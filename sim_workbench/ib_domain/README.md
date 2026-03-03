# ib_domain — Investment Banking Domain

`ib_domain` is a simulation domain plugin for the Sim Workbench. It configures `sim_core` to simulate an **Investment Banker** pitching a financial idea to a **corporate client** (CFO, CEO, or Treasurer) and driving that client toward agreeing to engage on the proposed transaction.

---

## Overview

| Property | Value |
|----------|-------|
| **Slug** | `investment_banking` |
| **Label** | Investment Banking |
| **Persuader role** | Investment Banker |
| **Target role** | Client |
| **Success goal** | Client agrees to engage on the proposed financial transaction |
| **Turns per session** | 6 |
| **Success threshold** | 7.0 / 10 |

---

## Files

```
ib_domain/
├── __init__.py
├── apps.py       # IBDomainConfig — registers InvestmentBankingDomain on startup
└── config.py     # InvestmentBankingDomain class (the full domain implementation)
```

### `apps.py`

Registers the domain with `sim_core`'s `DOMAIN_REGISTRY` when Django starts:

```python
from sim_core.base_domain import DOMAIN_REGISTRY
from .config import InvestmentBankingDomain

class IBDomainConfig(AppConfig):
    name = 'ib_domain'

    def ready(self):
        DOMAIN_REGISTRY[InvestmentBankingDomain.slug] = InvestmentBankingDomain()
```

### `config.py`

Contains `InvestmentBankingDomain`, which subclasses `BaseDomainConfig` and implements all required prompt methods.

---

## Scenario Context Fields

These fields are presented to the user when creating a new Investment Banking scenario. Their values are passed to both agent system prompts during simulation.

| Field key | Label | Required | Example |
|-----------|-------|----------|---------|
| `client_industry` | Industry | Yes | `Robotics`, `SaaS`, `Manufacturing` |
| `financial_context` | Financial Context | Yes | `$50M Rev, High burn rate, Series D` |
| `market_conditions` | Market Conditions | No | `High interest rates, Bear market` |

---

## Persona Seed Fields

Minimal inputs provided by the user to trigger AI generation of a rich `PersonaProfile` (the client persona).

| Field key | Label | Example |
|-----------|-------|---------|
| `company_size` | Company Size | `200 employees, Series D` |
| `company_stage` | Stage | `Pre-IPO`, `Growth`, `Mature` |
| `personality_hint` | Personality Hint | `analytical`, `risk-averse`, `deal-hungry` |

---

## Generated Persona Fields

When `PersonaGenerationService` generates a client persona, the LLM produces a JSON profile with these fields:

| Field | Description |
|-------|-------------|
| `name` | Executive's full name |
| `title` | Job title (e.g. CFO, CEO, Treasurer) |
| `company` | Company name and one-sentence description |
| `personality_traits` | List of 3 traits |
| `risk_tolerance` | `low` / `medium` / `high` |
| `decision_style` | `analytical` / `intuitive` / `consensus-driven` / `data-driven` |
| `financial_pressures` | Current financial pressures |
| `key_concerns` | List of key concerns |
| `communication_style` | `Direct` / `Formal` / `Guarded` / `Collaborative` |
| `full_description` | 2–3 sentence narrative used in system prompts |

---

## Agent Prompts

### Persuader (Investment Banker)

The banker is prompted as a **VP-level investment banker at a top-tier bank**. Each session the prompt includes:
- Client's industry and market conditions from the scenario context.
- A summary of prior meetings (`persona_state.memory_summary`), if any.
- A list of unresolved client concerns to address this session (`persona_state.open_objections`).

The banker is instructed to be professional, persuasive, and concise (2–3 sentences per turn).

### Target (Client)

The client is prompted with:
- The full `full_description` from the generated persona profile.
- Industry, financial context, and market conditions from the scenario.
- Prior meeting recall and unresolved concerns from `persona_state`.
- A **stance label** derived from `PersonaState.stance_score`:

| Score range | Stance label |
|-------------|-------------|
| 0 – 1.9 | Strongly opposed — need significant convincing to even engage |
| 2.0 – 3.9 | Skeptical — reluctant, need more evidence before considering |
| 4.0 – 5.9 | Neutral — open to hearing more but not yet convinced |
| 6.0 – 7.9 | Cautiously interested — starting to see the value |
| 8.0 – 10 | Genuinely interested — leaning toward agreeing to proceed |

The client is instructed to react realistically and concisely (2–3 sentences per turn).

---

## Outcome Labels

After each session, `GoalEvaluationService` evaluates the conversation and assigns one of these outcome labels:

| Label | Meaning |
|-------|---------|
| `DEAL_AGREED` | Client has agreed to engage on the transaction |
| `PROGRESSING` | Positive momentum; follow-up expected |
| `STALLED` | Conversation stalled; no clear progress |
| `REJECTED` | Client declined or closed the door |

---

## Scenario Variants

`ScenarioGenerationService` can generate multiple scenario variants from a persuader goal. Each variant includes:

| Field | Description |
|-------|-------------|
| `title` | Short scenario title |
| `difficulty` | `easy` / `medium` / `hard` / `very_hard` |
| `client_industry` | Industry |
| `financial_context` | Company financial situation |
| `market_conditions` | Current market environment |
| `narrative` | 2–3 sentence setup explaining the challenge level |

---

## Multi-Session Tracking

`PersonaState` is updated after each session:

- **`stance_score`** is incremented or decremented by `stance_delta` from the evaluation result, bounded to [0, 10].
- **`memory_summary`** is replaced with a fresh 2–3 sentence summary of what happened this session.
- **`open_objections`** is replaced with any objections that remain unresolved.
- **`session_count`** increments by 1.
- If `score < 7.0` (the success threshold), `PersonaState.trigger_active` is set to `True` and `next_trigger_at` is scheduled 7 days out, causing the scheduler to auto-create a follow-up session.

---

## Registration

`ib_domain` is activated by adding it to `INSTALLED_APPS` in `settings.py` **after** `sim_core`:

```python
INSTALLED_APPS = [
    ...
    'sim_core.apps.SimCoreConfig',
    'ib_domain.apps.IBDomainConfig',   # ← this line
    ...
]
```

After adding the app for the first time, seed the `SimulationDomain` DB row:

```bash
python manage.py bootstrap_domains
```
