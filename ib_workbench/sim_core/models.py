import json
import datetime
from django.db import models
from django.utils import timezone


class SimulationDomain(models.Model):
    """
    Thin DB record for each registered domain.
    The actual simulation logic lives in the domain's Python config class.
    slug maps to DOMAIN_REGISTRY in base_domain.py.
    """
    slug = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_config(self):
        from .base_domain import get_domain
        return get_domain(self.slug)

    def __str__(self):
        return self.label

    class Meta:
        app_label = 'sim_core'


class PersonaProfile(models.Model):
    """
    A rich, LLM-generated (or manually authored) persona.
    One profile can be reused across multiple scenarios
    (e.g. the same doctor across multiple drug campaigns).
    """
    ROLE_CHOICES = [('persuader', 'Persuader'), ('target', 'Target')]

    domain = models.ForeignKey(
        SimulationDomain, on_delete=models.CASCADE, related_name='personas'
    )
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='target')
    # Minimal inputs the user provided to trigger generation
    seed_inputs_json = models.TextField(default='{}')
    # Full LLM-generated profile (domain-specific fields)
    profile_data_json = models.TextField(default='{}')
    created_at = models.DateTimeField(auto_now_add=True)

    def get_profile(self):
        try:
            return json.loads(self.profile_data_json)
        except json.JSONDecodeError:
            return {}

    def set_profile(self, d):
        self.profile_data_json = json.dumps(d)

    def get_seed_inputs(self):
        try:
            return json.loads(self.seed_inputs_json)
        except json.JSONDecodeError:
            return {}

    def __str__(self):
        return f"{self.name} ({self.domain.label} / {self.role})"

    class Meta:
        app_label = 'sim_core'


class PersonaState(models.Model):
    """
    Mutable state for a target persona that persists across simulation sessions.
    Tracks the evolving relationship: stance score, memory, objections, and
    when to autonomously re-engage.
    """
    persona = models.ForeignKey(
        PersonaProfile, on_delete=models.CASCADE, related_name='states'
    )
    # 0-10: how close the target is to the desired action
    stance_score = models.FloatField(default=3.0)
    # Running narrative memory maintained by the goal evaluator
    memory_summary = models.TextField(default='')
    # Unresolved objections as a JSON list of strings
    open_objections_json = models.TextField(default='[]')
    # How many simulation sessions have been run with this persona
    session_count = models.IntegerField(default=0)
    # Label from the last evaluation (e.g. DEAL_AGREED, REJECTED)
    last_outcome_label = models.CharField(max_length=50, default='')
    # Autonomous re-engagement trigger
    trigger_active = models.BooleanField(default=False)
    next_trigger_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_open_objections(self):
        try:
            return json.loads(self.open_objections_json)
        except json.JSONDecodeError:
            return []

    def set_open_objections(self, lst):
        self.open_objections_json = json.dumps(lst)

    def as_dict(self):
        return {
            'stance_score': self.stance_score,
            'memory_summary': self.memory_summary,
            'open_objections': self.get_open_objections(),
            'session_count': self.session_count,
            'last_outcome_label': self.last_outcome_label,
        }

    def schedule_next_trigger(self, days=7):
        self.trigger_active = True
        self.next_trigger_at = timezone.now() + datetime.timedelta(days=days)
        self.save()

    def __str__(self):
        return f"State of {self.persona.name} (score={self.stance_score:.1f})"

    class Meta:
        app_label = 'sim_core'


class Scenario(models.Model):
    """
    A single simulation session. Domain-agnostic: all domain-specific
    context is stored in context_json so the same table works for any domain.
    """
    STATUS_CHOICES = [
        ('CREATED', 'Created'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    domain = models.ForeignKey(
        SimulationDomain, on_delete=models.CASCADE, related_name='scenarios'
    )
    target_persona = models.ForeignKey(
        PersonaProfile, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='scenarios_as_target'
    )
    persona_state = models.ForeignKey(
        PersonaState, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='scenarios'
    )

    title = models.CharField(max_length=255, default='')
    # What the persuader is trying to achieve (e.g. banker's pitch idea, drug name)
    persuader_goal = models.TextField(default='')
    # All domain context field values as a JSON dict
    context_json = models.TextField(default='{}')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CREATED')
    conversation_log = models.TextField(default='[]')

    # For multi-session tracking (session 1, 2, 3 … with same persona)
    session_number = models.IntegerField(default=1)
    # True when this session was auto-created by the scheduler
    is_autonomous = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_context(self):
        try:
            return json.loads(self.context_json)
        except json.JSONDecodeError:
            return {}

    def set_context(self, d):
        self.context_json = json.dumps(d)

    def get_conversation_log(self):
        try:
            return json.loads(self.conversation_log)
        except json.JSONDecodeError:
            return []

    def set_conversation_log(self, lst):
        self.conversation_log = json.dumps(lst)

    def __str__(self):
        return f"Scenario #{self.id} ({self.domain.label}) — {self.title[:50]}"

    class Meta:
        app_label = 'sim_core'


class SimulationResult(models.Model):
    """
    Goal-evaluation output produced by GoalEvaluationService after each session.
    Drives PersonaState updates and next-step recommendations.
    """
    scenario = models.OneToOneField(
        Scenario, on_delete=models.CASCADE, related_name='result'
    )
    # 0-10 score toward the domain's goal
    score = models.FloatField(default=0.0)
    # Domain-specific outcome label (e.g. DEAL_AGREED, TRIAL_AGREED)
    outcome_label = models.CharField(max_length=50, default='')
    rationale = models.TextField(default='')
    # Change applied to PersonaState.stance_score
    stance_delta = models.FloatField(default=0.0)
    # Rolling memory summary for the next session
    memory_summary = models.TextField(default='')
    # Objections that remain unresolved after this session
    new_objections_json = models.TextField(default='[]')
    # Recommended action for the persuader before next contact
    next_step = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def get_new_objections(self):
        try:
            return json.loads(self.new_objections_json)
        except json.JSONDecodeError:
            return []

    def set_new_objections(self, lst):
        self.new_objections_json = json.dumps(lst)

    def __str__(self):
        return f"Result for Scenario #{self.scenario_id}: {self.outcome_label} ({self.score:.1f}/10)"

    class Meta:
        app_label = 'sim_core'
