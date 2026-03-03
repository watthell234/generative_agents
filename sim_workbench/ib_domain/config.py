"""
Investment Banking domain configuration.

Ports the existing hardcoded IB prompts from ib_sim/simulation.py into
the generic BaseDomainConfig interface so sim_core can run IB simulations
without knowing anything about banking.
"""
import json
from sim_core.base_domain import BaseDomainConfig


class InvestmentBankingDomain(BaseDomainConfig):

    slug = 'investment_banking'
    label = 'Investment Banking'
    description = (
        'Simulate an investment banker pitching a financial idea to a corporate client '
        '(CFO, CEO, or Treasurer).'
    )

    persuader_role = 'Investment Banker'
    target_role = 'Client'
    goal_definition = 'Client agrees to engage on the proposed financial transaction.'

    turns_per_session = 6
    success_threshold = 7.0

    context_fields = [
        {
            'key': 'client_industry',
            'label': 'Industry',
            'type': 'text',
            'placeholder': 'e.g. Robotics, SaaS, Manufacturing',
            'required': True,
            'help_text': "The client's industry vertical.",
        },
        {
            'key': 'financial_context',
            'label': 'Financial Context',
            'type': 'text',
            'placeholder': 'e.g. $50M Rev, High burn rate, Series D',
            'required': True,
            'help_text': 'Key financial metrics and pressures.',
        },
        {
            'key': 'market_conditions',
            'label': 'Market Conditions',
            'type': 'text',
            'placeholder': 'e.g. High interest rates, Bear market',
            'required': False,
            'help_text': 'Current macro environment.',
        },
    ]

    persona_seed_fields = [
        {
            'key': 'company_size',
            'label': 'Company Size',
            'type': 'text',
            'placeholder': 'e.g. 200 employees, Series D',
            'required': False,
            'help_text': '',
        },
        {
            'key': 'company_stage',
            'label': 'Stage',
            'type': 'text',
            'placeholder': 'e.g. Pre-IPO, Growth, Mature',
            'required': False,
            'help_text': '',
        },
        {
            'key': 'personality_hint',
            'label': 'Personality Hint',
            'type': 'text',
            'placeholder': 'e.g. analytical, risk-averse, deal-hungry',
            'required': False,
            'help_text': 'Optional cue to shape the persona.',
        },
    ]

    # ------------------------------------------------------------------
    # Prompt methods
    # ------------------------------------------------------------------

    def persuader_system_prompt(self, context, persona_profile, persona_state):
        memory_txt = ''
        if persona_state.get('memory_summary'):
            memory_txt = f" Prior meeting summary: {persona_state['memory_summary']}."
        objections_txt = ''
        if persona_state.get('open_objections'):
            objections_txt = (
                f" Unresolved concerns to address this session: "
                f"{'; '.join(persona_state['open_objections'])}."
            )
        return (
            "You are a seasoned Investment Banker (VP level) at a top-tier bank."
            " Your goal is to pitch a financial idea to the client and move toward agreement."
            f" Client Industry: {context.get('client_industry', 'General')}."
            f" Market Conditions: {context.get('market_conditions', 'Neutral')}."
            f"{memory_txt}{objections_txt}"
            " Be professional, persuasive, and concise (2-3 sentences per turn)."
        )

    def target_system_prompt(self, context, persona_profile, persona_state):
        stance_score = persona_state.get('stance_score', 3.0)
        stance_desc = self._stance_label(stance_score)
        memory_txt = ''
        if persona_state.get('memory_summary'):
            memory_txt = f" From prior meetings you recall: {persona_state['memory_summary']}."
        objections_txt = ''
        if persona_state.get('open_objections'):
            objections_txt = (
                f" Your unresolved concerns: "
                f"{'; '.join(persona_state['open_objections'])}."
            )
        persona_desc = persona_profile.get('full_description', 'a corporate executive')
        return (
            f"You are the Client: {persona_desc}."
            f" Your company is in the {context.get('client_industry', 'General')} industry."
            f" Financial Context: {context.get('financial_context', 'Stable')}."
            f" Market Conditions: {context.get('market_conditions', 'Neutral')}."
            f"{memory_txt}{objections_txt}"
            f" Your current stance toward this deal: {stance_desc}."
            " React realistically to the banker's pitch. Be concise (2-3 sentences per turn)."
        )

    def _stance_label(self, score):
        if score < 2.0:
            return "strongly opposed — need significant convincing to even engage"
        if score < 4.0:
            return "skeptical — reluctant, need more evidence before considering this"
        if score < 6.0:
            return "neutral — open to hearing more but not yet convinced"
        if score < 8.0:
            return "cautiously interested — starting to see the value here"
        return "genuinely interested — leaning toward agreeing to proceed"

    def persona_generation_prompt(self, seed_inputs):
        return f"""Generate a realistic CFO/CEO persona for an investment banking simulation.

Seed inputs:
- Company size: {seed_inputs.get('company_size', 'Mid-size')}
- Company stage: {seed_inputs.get('company_stage', 'Growth')}
- Industry: {seed_inputs.get('client_industry', 'Technology')}
- Personality hint: {seed_inputs.get('personality_hint', 'analytical')}

Return ONLY valid JSON (no markdown fences, no preamble):
{{
  "name": "Full name",
  "title": "Job title (e.g. CFO, CEO, Treasurer)",
  "company": "Company name and one-sentence description",
  "personality_traits": ["trait1", "trait2", "trait3"],
  "risk_tolerance": "low|medium|high",
  "decision_style": "analytical|intuitive|consensus-driven|data-driven",
  "financial_pressures": "Brief description of current financial pressures",
  "key_concerns": ["concern1", "concern2"],
  "communication_style": "Direct|Formal|Guarded|Collaborative",
  "full_description": "2-3 sentence narrative describing this executive for use in simulation prompts"
}}"""

    def scenario_generation_prompt(self, persuader_goal, seed_inputs, count=3):
        return f"""Generate {count} realistic investment banking scenario variants for this pitch goal:
Goal: {persuader_goal}
Context hints: {json.dumps(seed_inputs)}

Return ONLY a valid JSON array of {count} objects (no markdown, no preamble), each with:
{{
  "title": "Short scenario title",
  "difficulty": "easy|medium|hard|very_hard",
  "client_industry": "Industry",
  "financial_context": "Company financial situation",
  "market_conditions": "Current market environment",
  "narrative": "2-3 sentence setup explaining why this is a challenging or accessible target"
}}"""

    def goal_evaluation_prompt(self, conversation_log, context, persona_state):
        log_text = '\n'.join([f"{e['agent']}: {e['message']}" for e in conversation_log])
        return f"""Evaluate this investment banking pitch conversation.

Goal: {self.goal_definition}
Client Industry: {context.get('client_industry', 'unknown')}
Current stance score before this session: {persona_state.get('stance_score', 3.0)}/10

Conversation:
{log_text}

Return ONLY valid JSON (no markdown, no preamble):
{{
  "score": <0-10 float, where 10 = deal firmly agreed>,
  "outcome_label": "DEAL_AGREED|PROGRESSING|STALLED|REJECTED",
  "rationale": "Brief explanation of the score",
  "stance_delta": <float, positive = moved toward deal, negative = moved away>,
  "new_objections": ["any unresolved objection that remains after this session"],
  "memory_summary": "2-3 sentences capturing what happened for the next meeting",
  "next_step": "What the banker should do before the next contact"
}}"""
