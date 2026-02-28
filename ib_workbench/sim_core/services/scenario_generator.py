"""
ScenarioGenerationService — generates multiple realistic scenario variants
using the domain's scenario_generation_prompt.
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


class ScenarioGenerationService:
    """
    Domain-agnostic scenario variant generator.
    Usage:
        service = ScenarioGenerationService()
        variants = service.generate_variants(domain_config, persuader_goal, seed_inputs, count=3)
    Returns a list of dicts, each ready to pre-fill the create-scenario form.
    """

    def generate_variants(self, domain_config, persuader_goal, seed_inputs, count=3):
        prompt = domain_config.scenario_generation_prompt(persuader_goal, seed_inputs, count)
        return self._call_llm(prompt)

    def _call_llm(self, prompt):
        if not OPENAI_AVAILABLE:
            return [{"title": "Mock Scenario", "narrative": "No OpenAI key — mock scenario only."}]
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=1200,
            )
            raw = response.choices[0].message['content']
            result = json.loads(_strip_code_fence(raw))
            if isinstance(result, list):
                return result
            # Some models wrap the array in an object
            for v in result.values():
                if isinstance(v, list):
                    return v
            return [result]
        except json.JSONDecodeError as e:
            return [{"title": "Parse Error", "narrative": f"Could not parse LLM response: {e}"}]
        except Exception as e:
            return [{"title": "Error", "narrative": str(e)}]
