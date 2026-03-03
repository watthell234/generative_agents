# pharma_domain — Pharma Consulting Domain

`pharma_domain` is a simulation domain plugin for the Sim Workbench. It configures `sim_core` to simulate a **Medical Science Liaison (MSL)** building a **physician's** propensity to prescribe a specific drug for appropriate patients in their practice.

---

## Overview

| Property | Value |
|----------|-------|
| **Slug** | `pharma` |
| **Label** | Pharma Consulting |
| **Persuader role** | Medical Science Liaison |
| **Target role** | Physician |
| **Success goal** | Physician develops propensity to prescribe the drug for appropriate patients |
| **Turns per session** | 6 |
| **Success threshold** | 7.0 / 10 |

---

## Files

```
pharma_domain/
├── __init__.py
├── apps.py       # PharmaDomainConfig — registers PharmaDomain on startup
└── config.py     # PharmaDomain class (the full domain implementation)
```

### `apps.py`

Registers the domain with `sim_core`'s `DOMAIN_REGISTRY` when Django starts:

```python
from sim_core.base_domain import DOMAIN_REGISTRY
from .config import PharmaDomain

class PharmaDomainConfig(AppConfig):
    name = 'pharma_domain'

    def ready(self):
        DOMAIN_REGISTRY[PharmaDomain.slug] = PharmaDomain()
```

### `config.py`

Contains `PharmaDomain`, which subclasses `BaseDomainConfig` and implements all required prompt methods.

---

## Scenario Context Fields

These fields are presented to the user when creating a new Pharma Consulting scenario. Their values are passed to both agent system prompts during simulation.

| Field key | Label | Required | Example |
|-----------|-------|----------|---------|
| `drug_name` | Drug / Product Name | Yes | `Cardivex 10mg` |
| `therapeutic_area` | Therapeutic Area | Yes | `Type 2 Diabetes`, `Heart Failure`, `Oncology` |
| `key_clinical_claim` | Key Clinical Claim | Yes | `23% reduction in HbA1c vs. SoC in the EMPA-HEART trial (n=3,200)` |
| `specialty` | Physician Specialty | Yes | `Cardiologist`, `GP`, `Endocrinologist` |
| `formulary_status` | Formulary Status | No | `Tier 2, requires prior auth` |
| `competitor_landscape` | Competitor Landscape | No | `Metformin dominant, GLP-1 agonists growing fast` |
| `patient_demographics` | Target Patient Demographics | No | `55-75yo, comorbid hypertension, insulin-resistant` |

---

## Persona Seed Fields

Minimal inputs provided by the user to trigger AI generation of a rich `PersonaProfile` (the physician persona).

| Field key | Label | Required | Example |
|-----------|-------|----------|---------|
| `specialty` | Specialty | Yes | `Cardiologist`, `GP`, `Oncologist` |
| `years_experience` | Years in Practice | No | `15` |
| `practice_type` | Practice Type | No | `Academic medical centre`, `Private group`, `Community clinic` |
| `personality_hint` | Personality Hint | No | `evidence-driven`, `time-poor`, `KOL`, `early adopter` |

---

## Generated Persona Fields

When `PersonaGenerationService` generates a physician persona, the LLM produces a JSON profile with these fields:

| Field | Description |
|-------|-------------|
| `name` | Physician's full name (e.g. `Dr. Jane Smith`) |
| `title` | Title and specialty |
| `practice_description` | One-sentence description of their practice |
| `personality_traits` | List of 3 traits |
| `prescribing_habits` | e.g. `Conservative`, `Evidence-driven`, `Protocol-driven` |
| `evidence_threshold` | What level of evidence is required to change prescribing behaviour |
| `influence_factors` | e.g. `peer opinion`, `patient outcomes`, `formulary status`, `cost` |
| `current_drug_preferences` | What they currently prescribe in this therapeutic area and why |
| `time_constraints` | Availability for rep visits (e.g. `5 min max, lunch-and-learns only`) |
| `receptiveness_to_reps` | `low` / `medium` / `high` |
| `key_concerns` | List of clinical, safety/AE, and cost/access concerns |
| `full_description` | 2–3 sentence narrative used in system prompts |

---

## Agent Prompts

### Persuader (Medical Science Liaison)

The MSL is prompted as a **scientifically credible liaison promoting a specific drug**. Each session the prompt includes:
- Drug name, therapeutic area, key clinical claim, formulary status, and competitor context from the scenario.
- A summary of prior interactions (`persona_state.memory_summary`), if any.
- Physician concerns to address this visit (`persona_state.open_objections`).

The MSL is instructed to be evidence-based, respectful of the physician's time, and clinically credible — making no unsupported claims (2–3 sentences per turn).

### Target (Physician)

The physician is prompted with:
- The `full_description` from the generated persona profile.
- `prescribing_habits`, `evidence_threshold`, `time_constraints`, and `current_drug_preferences` from the profile.
- Patient demographics from the scenario context.
- Prior interaction recall and unresolved concerns from `persona_state`.
- A **prescribing propensity label** derived from `PersonaState.stance_score`:

| Score range | Prescribing propensity label |
|-------------|------------------------------|
| 0 – 1.4 | Zero interest — effective alternatives already in use |
| 1.5 – 2.9 | Skeptical — heard similar claims before, need strong differentiation |
| 3.0 – 4.9 | Mildly curious — need more evidence before changing prescribing habits |
| 5.0 – 6.9 | Cautiously interested — considering trialing with select patients |
| 7.0 – 8.4 | Interested — planning to trial with appropriate patients soon |
| 8.5 – 10 | Convinced — intend to prescribe for appropriate patients |

The physician is instructed to respond as a busy, skeptical but fair clinician (2–3 sentences per turn).

---

## Outcome Labels

After each session, `GoalEvaluationService` evaluates the conversation and assigns one of these outcome labels:

| Label | Meaning |
|-------|---------|
| `PRESCRIBING_COMMITTED` | Physician committed to prescribing for appropriate patients |
| `TRIAL_AGREED` | Physician agreed to trial the drug with select patients |
| `FOLLOW_UP_AGREED` | Physician open to further discussion; follow-up requested |
| `INTERESTED_NO_ACTION` | Interest expressed but no concrete next step agreed |
| `REJECTED` | Physician declined or closed the conversation |

---

## Scenario Variants

`ScenarioGenerationService` can generate multiple scenario variants from a drug goal. Each variant includes:

| Field | Description |
|-------|-------------|
| `title` | Short scenario title |
| `difficulty` | `easy` / `medium` / `hard` / `very_hard` |
| `specialty` | Physician specialty for this scenario |
| `patient_demographics` | Typical patient profile |
| `formulary_status` | Formulary access description |
| `competitor_landscape` | Key competitors in this scenario |
| `key_clinical_claim` | Headline clinical evidence the MSL should lead with |
| `narrative` | 2–3 sentence setup: physician's starting situation and challenge level |

---

## Multi-Session Tracking

`PersonaState` is updated after each session:

- **`stance_score`** is incremented or decremented by `stance_delta` from the evaluation result, bounded to [0, 10].
- **`memory_summary`** captures what the physician would recall: key data points mentioned and any commitments made.
- **`open_objections`** is replaced with any objections that remain unresolved after this visit.
- **`session_count`** increments by 1.
- If `score < 7.0` (the success threshold), `PersonaState.trigger_active` is set to `True` and `next_trigger_at` is scheduled 7 days out, causing the scheduler to auto-create a follow-up visit.

---

## Registration

`pharma_domain` is activated by adding it to `INSTALLED_APPS` in `settings.py` **after** `sim_core`:

```python
INSTALLED_APPS = [
    ...
    'sim_core.apps.SimCoreConfig',
    'pharma_domain.apps.PharmaDomainConfig',   # ← this line
    ...
]
```

After adding the app for the first time, seed the `SimulationDomain` DB row:

```bash
python manage.py bootstrap_domains
```
