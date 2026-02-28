"""
Pharma Consulting domain configuration.

Simulates a Medical Science Liaison (MSL) or pharma rep building a physician's
propensity to prescribe a specific drug for appropriate patients.
"""
import json
from sim_core.base_domain import BaseDomainConfig


class PharmaDomain(BaseDomainConfig):

    slug = 'pharma'
    label = 'Pharma Consulting'
    description = (
        "Simulate a Medical Science Liaison building a physician's propensity "
        "to prescribe a drug for appropriate patients."
    )

    persuader_role = 'Medical Science Liaison'
    target_role = 'Physician'
    goal_definition = (
        'Physician develops propensity to prescribe the drug '
        'for appropriate patients in their practice.'
    )

    turns_per_session = 6
    success_threshold = 7.0

    context_fields = [
        {
            'key': 'drug_name',
            'label': 'Drug / Product Name',
            'type': 'text',
            'placeholder': 'e.g. Cardivex 10mg',
            'required': True,
            'help_text': 'The drug or product being promoted.',
        },
        {
            'key': 'therapeutic_area',
            'label': 'Therapeutic Area',
            'type': 'text',
            'placeholder': 'e.g. Type 2 Diabetes, Heart Failure, Oncology',
            'required': True,
            'help_text': '',
        },
        {
            'key': 'key_clinical_claim',
            'label': 'Key Clinical Claim',
            'type': 'textarea',
            'placeholder': 'e.g. 23% reduction in HbA1c vs. SoC in the EMPA-HEART trial (n=3,200)',
            'required': True,
            'help_text': 'The primary evidence point the MSL will lead with.',
        },
        {
            'key': 'specialty',
            'label': 'Physician Specialty',
            'type': 'text',
            'placeholder': 'e.g. Cardiologist, GP, Endocrinologist',
            'required': True,
            'help_text': "The target physician's specialty.",
        },
        {
            'key': 'formulary_status',
            'label': 'Formulary Status',
            'type': 'text',
            'placeholder': 'e.g. Tier 2, requires prior auth, not on formulary',
            'required': False,
            'help_text': 'Insurance/formulary access for this drug.',
        },
        {
            'key': 'competitor_landscape',
            'label': 'Competitor Landscape',
            'type': 'text',
            'placeholder': 'e.g. Metformin dominant, GLP-1 agonists growing fast',
            'required': False,
            'help_text': 'Key competing drugs and their current position.',
        },
        {
            'key': 'patient_demographics',
            'label': 'Target Patient Demographics',
            'type': 'text',
            'placeholder': 'e.g. 55-75yo, comorbid hypertension, insulin-resistant',
            'required': False,
            'help_text': 'Profile of patients this drug is indicated for.',
        },
    ]

    persona_seed_fields = [
        {
            'key': 'specialty',
            'label': 'Specialty',
            'type': 'text',
            'placeholder': 'e.g. Cardiologist, GP, Oncologist',
            'required': True,
            'help_text': '',
        },
        {
            'key': 'years_experience',
            'label': 'Years in Practice',
            'type': 'text',
            'placeholder': 'e.g. 15',
            'required': False,
            'help_text': '',
        },
        {
            'key': 'practice_type',
            'label': 'Practice Type',
            'type': 'text',
            'placeholder': 'e.g. Academic medical centre, Private group, Community clinic',
            'required': False,
            'help_text': '',
        },
        {
            'key': 'personality_hint',
            'label': 'Personality Hint',
            'type': 'text',
            'placeholder': 'e.g. evidence-driven, time-poor, KOL, early adopter',
            'required': False,
            'help_text': 'Optional cue to shape the physician persona.',
        },
    ]

    # ------------------------------------------------------------------
    # Prompt methods
    # ------------------------------------------------------------------

    def persuader_system_prompt(self, context, persona_profile, persona_state):
        memory_txt = ''
        if persona_state.get('memory_summary'):
            memory_txt = f" Prior interaction summary: {persona_state['memory_summary']}."
        objections_txt = ''
        if persona_state.get('open_objections'):
            objections_txt = (
                f" Physician concerns to address this visit: "
                f"{'; '.join(persona_state['open_objections'])}."
            )
        return (
            f"You are a Medical Science Liaison (MSL) promoting {context.get('drug_name', 'the drug')}."
            f" Therapeutic area: {context.get('therapeutic_area', 'unspecified')}."
            f" Key clinical claim: {context.get('key_clinical_claim', 'unspecified')}."
            f" Formulary status: {context.get('formulary_status', 'unknown')}."
            f" Competitor context: {context.get('competitor_landscape', 'not specified')}."
            f"{memory_txt}{objections_txt}"
            " Be evidence-based, respectful of the physician's time, and clinically credible."
            " Do not make unsupported claims. Keep responses to 2-3 sentences."
        )

    def target_system_prompt(self, context, persona_profile, persona_state):
        stance_score = persona_state.get('stance_score', 3.0)
        stance_desc = self._stance_label(stance_score)
        memory_txt = ''
        if persona_state.get('memory_summary'):
            memory_txt = f" You recall from a prior interaction: {persona_state['memory_summary']}."
        objections_txt = ''
        if persona_state.get('open_objections'):
            objections_txt = (
                f" Your unresolved concerns: "
                f"{'; '.join(persona_state['open_objections'])}."
            )
        persona_desc = persona_profile.get(
            'full_description',
            f"a {context.get('specialty', 'physician')}"
        )
        prescribing_habits = persona_profile.get('prescribing_habits', 'evidence-driven')
        evidence_threshold = persona_profile.get('evidence_threshold', 'requires Phase III RCT data')
        time_constraints = persona_profile.get('time_constraints', 'limited time for rep visits')
        current_prefs = persona_profile.get('current_drug_preferences', 'standard of care')
        return (
            f"You are a {context.get('specialty', 'physician')}. {persona_desc}"
            f" Your prescribing style: {prescribing_habits}."
            f" Evidence threshold: {evidence_threshold}."
            f" Current drug preferences in this area: {current_prefs}."
            f" Time available for this rep: {time_constraints}."
            f" Patient demographics you treat: {context.get('patient_demographics', 'mixed')}."
            f"{memory_txt}{objections_txt}"
            f" Your current prescribing propensity for {context.get('drug_name', 'this drug')}: {stance_desc}."
            " Respond as a busy physician. Be skeptical but fair. 2-3 sentences per turn."
        )

    def _stance_label(self, score):
        if score < 1.5:
            return "zero interest — you have effective alternatives and are loyal to them"
        if score < 3.0:
            return "skeptical — heard similar claims before, need strong differentiation"
        if score < 5.0:
            return "mildly curious — need more evidence before changing prescribing habits"
        if score < 7.0:
            return "cautiously interested — considering trialing with select patients"
        if score < 8.5:
            return "interested — planning to trial with appropriate patients soon"
        return "convinced — intend to prescribe for appropriate patients in your practice"

    def persona_generation_prompt(self, seed_inputs):
        return f"""Generate a realistic physician persona for a pharma sales simulation.

Seed inputs:
- Specialty: {seed_inputs.get('specialty', 'General Practitioner')}
- Years in practice: {seed_inputs.get('years_experience', '10-15')}
- Practice type: {seed_inputs.get('practice_type', 'Private group practice')}
- Personality hint: {seed_inputs.get('personality_hint', 'evidence-driven')}

Return ONLY valid JSON (no markdown fences, no preamble):
{{
  "name": "Dr. First Last",
  "title": "Title and specialty",
  "practice_description": "One-sentence practice description",
  "personality_traits": ["trait1", "trait2", "trait3"],
  "prescribing_habits": "Conservative|Aggressive|Evidence-driven|Protocol-driven|etc.",
  "evidence_threshold": "What level of evidence is required to change prescribing behaviour",
  "influence_factors": ["peer opinion", "patient outcomes", "formulary status", "cost"],
  "current_drug_preferences": "What they currently prescribe in this therapeutic area and why",
  "time_constraints": "Availability for rep visits (e.g. '5 min max, lunch-and-learns only')",
  "receptiveness_to_reps": "low|medium|high",
  "key_concerns": ["clinical concern", "safety/AE concern", "cost/access concern"],
  "full_description": "2-3 sentence narrative describing this physician for use in simulation prompts"
}}"""

    def scenario_generation_prompt(self, persuader_goal, seed_inputs, count=3):
        return f"""Generate {count} realistic pharma MSL–physician scenario variants.

Drug goal: {persuader_goal}
Context hints: {json.dumps(seed_inputs)}

Return ONLY a valid JSON array of {count} objects (no markdown, no preamble), each with:
{{
  "title": "Short scenario title",
  "difficulty": "easy|medium|hard|very_hard",
  "specialty": "Physician specialty",
  "patient_demographics": "Typical patient profile for this scenario",
  "formulary_status": "Formulary access description",
  "competitor_landscape": "Key competitors in this scenario",
  "key_clinical_claim": "Headline clinical evidence the MSL should use",
  "narrative": "2-3 sentence setup: physician's starting situation and why this is challenging or accessible"
}}"""

    def goal_evaluation_prompt(self, conversation_log, context, persona_state):
        log_text = '\n'.join([f"{e['agent']}: {e['message']}" for e in conversation_log])
        return f"""Evaluate this pharma MSL–physician interaction.

Goal: {self.goal_definition}
Drug: {context.get('drug_name', 'unknown')}
Therapeutic area: {context.get('therapeutic_area', 'unknown')}
Current prescribing propensity before this session: {persona_state.get('stance_score', 3.0)}/10
Unresolved concerns going in: {persona_state.get('open_objections', [])}

Conversation:
{log_text}

Return ONLY valid JSON (no markdown, no preamble):
{{
  "score": <0-10 float, where 10 = fully committed to prescribing>,
  "outcome_label": "PRESCRIBING_COMMITTED|TRIAL_AGREED|FOLLOW_UP_AGREED|INTERESTED_NO_ACTION|REJECTED",
  "rationale": "Clinical/behavioural explanation of the score",
  "stance_delta": <float change in prescribing propensity, positive = toward prescribing>,
  "new_objections": ["any unresolved objection remaining after this session"],
  "memory_summary": "What the physician would recall: key data points mentioned, any commitments made",
  "next_step": "What the MSL should do before the next visit (e.g. bring formulary data, arrange peer discussion)"
}}"""
