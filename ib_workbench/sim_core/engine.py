"""
DomainEngine — the generic simulation loop.

Replaces SimpleLLMEngine from ib_sim/simulation.py.
Reads all domain-specific behaviour (roles, prompt templates, turn count)
from the domain config object, so this file never needs to change when
a new domain is added.
"""
import os
import time
import json

try:
    import openai
    openai.api_key = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_AVAILABLE = bool(openai.api_key)
except ImportError:
    OPENAI_AVAILABLE = False


class DomainEngine:
    def __init__(self, scenario, domain_config):
        self.scenario = scenario
        self.config = domain_config
        self.context = scenario.get_context()
        self.persona_profile = {}
        self.persona_state = {}
        self.conversation_history = []

        if scenario.target_persona:
            self.persona_profile = scenario.target_persona.get_profile()
        if scenario.persona_state:
            self.persona_state = scenario.persona_state.as_dict()

    def _call_llm(self, messages, temperature=0.7, max_tokens=200):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message['content'].strip()
        except Exception as e:
            return f"[Error generating response: {e}]"

    def generate_system_prompt(self, role):
        if role == self.config.persuader_role:
            return self.config.persuader_system_prompt(
                self.context, self.persona_profile, self.persona_state
            )
        return self.config.target_system_prompt(
            self.context, self.persona_profile, self.persona_state
        )

    def generate_turn(self, speaker):
        system_prompt = self.generate_system_prompt(speaker)
        messages = [{"role": "system", "content": system_prompt}]
        for entry in self.conversation_history:
            msg_role = "assistant" if entry['agent'] == speaker else "user"
            messages.append({"role": msg_role, "content": entry['message']})
        return self._call_llm(messages)

    def run_step(self):
        if not self.conversation_history:
            speaker = self.config.persuader_role
        else:
            last = self.conversation_history[-1]['agent']
            speaker = (
                self.config.target_role
                if last == self.config.persuader_role
                else self.config.persuader_role
            )

        message = self.generate_turn(speaker)
        entry = {'agent': speaker, 'message': message}
        self.conversation_history.append(entry)

        current_log = self.scenario.get_conversation_log()
        current_log.append(entry)
        self.scenario.set_conversation_log(current_log)
        self.scenario.save()


def run_simulation(scenario_id):
    """
    Entry point called by views and the scheduler.
    Contract: takes a Scenario pk, runs the simulation, updates status.
    """
    from .models import Scenario
    from .services.goal_evaluator import GoalEvaluationService

    scenario = Scenario.objects.get(id=scenario_id)
    domain_config = scenario.domain.get_config()

    if not OPENAI_AVAILABLE:
        # Mock fallback when no API key is present
        persuader = domain_config.persuader_role
        target = domain_config.target_role
        mock_log = [
            {'agent': persuader, 'message': f"Hello! I'd like to discuss: {scenario.persuader_goal}"},
            {'agent': target,    'message': "That sounds interesting. Could you tell me more?"},
            {'agent': persuader, 'message': "Absolutely. The key benefit here is a meaningful improvement in outcomes."},
            {'agent': target,    'message': "I'd need to look at the details more carefully before deciding."},
        ]
        for entry in mock_log:
            time.sleep(1)
            log = scenario.get_conversation_log()
            log.append(entry)
            scenario.set_conversation_log(log)
            scenario.save()
        scenario.status = 'COMPLETED'
        scenario.save()
        return

    try:
        engine = DomainEngine(scenario, domain_config)
        for _ in range(domain_config.turns_per_session):
            time.sleep(1)
            engine.run_step()

        # Evaluate outcome and update PersonaState
        evaluator = GoalEvaluationService(domain_config)
        result = evaluator.evaluate(scenario)

        if scenario.persona_state:
            ps = scenario.persona_state
            new_score = ps.stance_score + result.stance_delta
            ps.stance_score = max(0.0, min(10.0, new_score))
            ps.memory_summary = result.memory_summary
            ps.set_open_objections(result.get_new_objections())
            ps.session_count += 1
            ps.last_outcome_label = result.outcome_label
            if result.score < domain_config.success_threshold:
                ps.schedule_next_trigger(days=7)
            else:
                ps.trigger_active = False
                ps.save()

        scenario.status = 'COMPLETED'
        scenario.save()

    except Exception as e:
        scenario.status = 'FAILED'
        scenario.set_conversation_log([{'agent': 'System', 'message': f'Error: {str(e)}'}])
        scenario.save()
        raise
