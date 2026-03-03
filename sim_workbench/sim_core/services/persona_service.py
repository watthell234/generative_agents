"""
PersonaGenerationService — calls the domain's persona_generation_prompt,
parses the LLM response, and creates a PersonaProfile + initial PersonaState.
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
    """Remove ```json ... ``` wrappers if the LLM adds them."""
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        # parts[1] is the content between the fences
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


class PersonaGenerationService:
    """
    Domain-agnostic persona generator.
    Usage:
        service = PersonaGenerationService()
        persona = service.generate(domain_config, seed_inputs)
    """

    def generate(self, domain_config, seed_inputs, role='target'):
        """
        Generate a PersonaProfile using the domain's persona_generation_prompt.

        Args:
            domain_config: An instance of BaseDomainConfig.
            seed_inputs (dict): Minimal inputs from the user (persona_seed_fields).
            role (str): 'target' or 'persuader'.

        Returns:
            PersonaProfile: The newly created (and saved) persona.
        """
        from sim_core.models import PersonaProfile, PersonaState, SimulationDomain

        prompt = domain_config.persona_generation_prompt(seed_inputs)
        profile_dict = self._call_llm(prompt)

        domain_obj = SimulationDomain.objects.get(slug=domain_config.slug)
        persona = PersonaProfile(
            domain=domain_obj,
            name=profile_dict.get('name', 'Auto-Generated Persona'),
            role=role,
            seed_inputs_json=json.dumps(seed_inputs),
        )
        persona.set_profile(profile_dict)
        persona.save()

        if role == 'target':
            PersonaState.objects.create(
                persona=persona,
                stance_score=3.0,
            )

        return persona

    def _call_llm(self, prompt):
        if not OPENAI_AVAILABLE:
            return {
                "name": "Mock Persona",
                "full_description": "A mock persona (no OpenAI API key configured).",
            }
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=700,
            )
            raw = response.choices[0].message['content']
            return json.loads(_strip_code_fence(raw))
        except json.JSONDecodeError as e:
            return {"name": "Parse Error", "full_description": f"Could not parse LLM response: {e}"}
        except Exception as e:
            return {"name": "Error Persona", "full_description": f"Error during generation: {e}"}
