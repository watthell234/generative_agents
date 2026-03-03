"""
BaseDomainConfig — the contract every simulation domain must fulfil.

To add a new domain:
  1. Create a new Django app (e.g. legal_domain/)
  2. Subclass BaseDomainConfig in config.py
  3. In apps.py ready(), call:
       from sim_core.base_domain import DOMAIN_REGISTRY
       from .config import MyDomain
       DOMAIN_REGISTRY[MyDomain.slug] = MyDomain()
  4. Add the app to INSTALLED_APPS in settings.py
"""

# Global registry: slug -> BaseDomainConfig instance
# Populated by each domain app's AppConfig.ready()
DOMAIN_REGISTRY = {}


def get_domain(slug):
    """Return the registered domain config for `slug`, or raise KeyError."""
    if slug not in DOMAIN_REGISTRY:
        available = list(DOMAIN_REGISTRY.keys())
        raise KeyError(
            f"Domain '{slug}' not registered. Available: {available}"
        )
    return DOMAIN_REGISTRY[slug]


def get_all_domains():
    """Return all registered domain config instances, sorted by label."""
    return sorted(DOMAIN_REGISTRY.values(), key=lambda d: d.label)


class BaseDomainConfig:
    """
    Abstract base class every simulation domain must implement.
    Subclasses define class-level attributes and override the prompt methods.
    """

    # --- Identity (subclasses MUST override) ---
    slug = ''            # URL-safe key, e.g. 'investment_banking'
    label = ''           # Human label, e.g. 'Investment Banking'
    description = ''     # One-sentence description for the domain card

    # --- Agent roles (subclasses MUST override) ---
    persuader_role = ''  # e.g. 'Investment Banker'
    target_role = ''     # e.g. 'CFO / CEO'

    # --- Goal (subclasses MUST override) ---
    goal_definition = '' # One-sentence success criterion

    # --- Form fields (subclasses MUST override) ---
    # List of dicts: {key, label, type ('text'|'textarea'), placeholder, required, help_text}
    context_fields = []      # Context fields shown in the create-scenario form
    persona_seed_fields = [] # Minimal inputs to trigger AI persona generation

    # --- Tunable defaults (subclasses MAY override) ---
    turns_per_session = 6    # Number of conversation turns per simulation run
    success_threshold = 7.0  # Stance score (0-10) considered a success

    # ------------------------------------------------------------------
    # Prompt methods — subclasses MUST implement all of these
    # ------------------------------------------------------------------

    def persuader_system_prompt(self, context, persona_profile, persona_state):
        """
        Build the system prompt for the persuader agent.

        Args:
            context (dict): Values from context_fields for this scenario.
            persona_profile (dict): LLM-generated profile from PersonaProfile.get_profile().
            persona_state (dict): Current state from PersonaState.as_dict()
                                  (stance_score, memory_summary, open_objections, …).
        Returns:
            str: System prompt for the persuader.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement persuader_system_prompt()")

    def target_system_prompt(self, context, persona_profile, persona_state):
        """
        Build the system prompt for the target agent.

        Args:
            context (dict): Values from context_fields.
            persona_profile (dict): LLM-generated profile.
            persona_state (dict): Current persona state.
        Returns:
            str: System prompt for the target.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement target_system_prompt()")

    def persona_generation_prompt(self, seed_inputs):
        """
        Return the full LLM prompt to generate a rich PersonaProfile from minimal seed_inputs.
        The prompt must instruct the LLM to return ONLY valid JSON.

        Args:
            seed_inputs (dict): Values from persona_seed_fields.
        Returns:
            str: LLM prompt.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement persona_generation_prompt()")

    def scenario_generation_prompt(self, persuader_goal, seed_inputs, count=3):
        """
        Return the LLM prompt to generate `count` scenario variants as a JSON array.
        Each variant dict should map to the keys in context_fields.

        Args:
            persuader_goal (str): What the persuader is trying to achieve.
            seed_inputs (dict): Hints for scenario generation.
            count (int): Number of variants to generate.
        Returns:
            str: LLM prompt.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement scenario_generation_prompt()")

    def goal_evaluation_prompt(self, conversation_log, context, persona_state):
        """
        Return the LLM prompt to evaluate a completed simulation session.
        Must instruct the LLM to return ONLY valid JSON with these keys:
            score (float 0-10), outcome_label (str), rationale (str),
            stance_delta (float), new_objections (list[str]),
            memory_summary (str), next_step (str)

        Args:
            conversation_log (list): List of {'agent': str, 'message': str} dicts.
            context (dict): Scenario context.
            persona_state (dict): Current persona state before this session.
        Returns:
            str: LLM prompt.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement goal_evaluation_prompt()")
