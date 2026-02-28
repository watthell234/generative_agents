"""
GoalEvaluationService — evaluates a completed simulation session.

Calls the domain's goal_evaluation_prompt, parses the LLM response,
creates a SimulationResult, and returns it so run_simulation() can
update PersonaState accordingly.
"""
import os
import json

try:
    import openai
    openai.api_key = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_AVAILABLE = bool(openai.api_key)
except ImportError:
    OPENAI_AVAILABLE = False


def _strip_code_fence(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


class GoalEvaluationService:
    def __init__(self, domain_config):
        self.config = domain_config

    def evaluate(self, scenario):
        """
        Evaluate `scenario` and return a saved SimulationResult instance.
        """
        from sim_core.models import SimulationResult

        conversation_log = scenario.get_conversation_log()
        context = scenario.get_context()
        persona_state = scenario.persona_state.as_dict() if scenario.persona_state else {}

        prompt = self.config.goal_evaluation_prompt(conversation_log, context, persona_state)
        eval_dict = self._call_llm(prompt)

        result = SimulationResult(scenario=scenario)
        result.score = float(eval_dict.get('score', 0.0))
        result.outcome_label = eval_dict.get('outcome_label', '')
        result.rationale = eval_dict.get('rationale', '')
        result.stance_delta = float(eval_dict.get('stance_delta', 0.0))
        result.memory_summary = eval_dict.get('memory_summary', '')
        result.set_new_objections(eval_dict.get('new_objections', []))
        result.next_step = eval_dict.get('next_step', '')
        result.save()
        return result

    def _call_llm(self, prompt):
        if not OPENAI_AVAILABLE:
            return {
                "score": 5.0,
                "outcome_label": "FOLLOW_UP_AGREED",
                "rationale": "Mock evaluation (no OpenAI key).",
                "stance_delta": 0.5,
                "memory_summary": "Initial meeting completed. Interest was shown.",
                "new_objections": [],
                "next_step": "Schedule a follow-up meeting.",
            }
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            raw = response.choices[0].message['content']
            return json.loads(_strip_code_fence(raw))
        except json.JSONDecodeError as e:
            return {
                "score": 0.0, "outcome_label": "PARSE_ERROR", "rationale": str(e),
                "stance_delta": 0.0, "memory_summary": "", "new_objections": [],
                "next_step": "",
            }
        except Exception as e:
            return {
                "score": 0.0, "outcome_label": "ERROR", "rationale": str(e),
                "stance_delta": 0.0, "memory_summary": "", "new_objections": [],
                "next_step": "",
            }
