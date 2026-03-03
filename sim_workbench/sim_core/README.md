# sim_core

`sim_core` is the **generic simulation engine** for the Sim Workbench. It provides the shared infrastructure — models, LLM engine, services, scheduler, and views — that all simulation domains build on. Adding a new domain requires only a single Python config file and a one-line registration call; `sim_core` never needs to change.

---

## Architecture Overview

```
sim_core/
├── base_domain.py          # Abstract base class every domain must subclass
├── engine.py               # DomainEngine — generic LLM conversation loop
├── models.py               # Core Django models (shared across all domains)
├── scheduler.py            # Background daemon for autonomous follow-up sessions
├── views.py                # Domain-agnostic Django views and REST API
├── urls.py                 # URL routing
├── admin.py                # Django admin registrations
├── apps.py                 # AppConfig — starts the scheduler on startup
├── management/
│   └── commands/
│       └── bootstrap_domains.py  # Management command to seed domain DB rows
└── services/
    ├── goal_evaluator.py       # GoalEvaluationService
    ├── persona_service.py      # PersonaGenerationService
    └── scenario_generator.py   # ScenarioGenerationService
```

---

## Core Concepts

### Domain Registry

`DOMAIN_REGISTRY` is a global `dict` (slug → config instance) populated at Django startup. Each domain app registers itself in its `AppConfig.ready()` method:

```python
from sim_core.base_domain import DOMAIN_REGISTRY
from .config import MyDomainConfig

DOMAIN_REGISTRY[MyDomainConfig.slug] = MyDomainConfig()
```

The registry is the single source of truth for which domains are available. Views, the engine, and services all resolve domain config exclusively through this registry.

### BaseDomainConfig

Every domain must subclass `BaseDomainConfig` (`base_domain.py`) and implement:

| Method | Purpose |
|--------|---------|
| `persuader_system_prompt(context, persona_profile, persona_state)` | System prompt for the persuader agent |
| `target_system_prompt(context, persona_profile, persona_state)` | System prompt for the target agent |
| `persona_generation_prompt(seed_inputs)` | LLM prompt to generate a rich `PersonaProfile` from seed inputs |
| `scenario_generation_prompt(persuader_goal, seed_inputs, count)` | LLM prompt to generate scenario variants |
| `goal_evaluation_prompt(conversation_log, context, persona_state)` | LLM prompt to evaluate a completed session |

Required class attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `slug` | `str` | URL-safe identifier (e.g. `'investment_banking'`) |
| `label` | `str` | Human-readable name (e.g. `'Investment Banking'`) |
| `description` | `str` | One-sentence description shown on the domain selection card |
| `persuader_role` | `str` | Name of the persuading agent (e.g. `'Investment Banker'`) |
| `target_role` | `str` | Name of the target agent (e.g. `'Client'`) |
| `goal_definition` | `str` | One-sentence success criterion |
| `context_fields` | `list[dict]` | Fields shown in the create-scenario form |
| `persona_seed_fields` | `list[dict]` | Minimal inputs for AI persona generation |
| `turns_per_session` | `int` | Conversation turns per simulation run (default: `6`) |
| `success_threshold` | `float` | Stance score (0–10) considered a success (default: `7.0`) |

---

## Data Models

All models live in `models.py` and use `app_label = 'sim_core'`.

### `SimulationDomain`

A thin DB record for each registered domain. The actual simulation logic lives in the domain's Python config class.

| Field | Type | Description |
|-------|------|-------------|
| `slug` | `CharField` | Matches a key in `DOMAIN_REGISTRY` |
| `label` | `CharField` | Human-readable domain name |
| `is_active` | `BooleanField` | Toggle to enable/disable a domain |
| `created_at` | `DateTimeField` | Auto-set on creation |

### `PersonaProfile`

A rich, LLM-generated (or manually authored) persona. One profile can be reused across multiple scenarios (e.g. the same physician across multiple drug campaigns).

| Field | Type | Description |
|-------|------|-------------|
| `domain` | FK → `SimulationDomain` | Which domain owns this persona |
| `name` | `CharField` | Full name |
| `role` | `CharField` | `'persuader'` or `'target'` |
| `seed_inputs_json` | `TextField` | JSON dict of the minimal inputs used to generate this persona |
| `profile_data_json` | `TextField` | JSON dict of the full LLM-generated profile |
| `created_at` | `DateTimeField` | Auto-set on creation |

### `PersonaState`

Mutable state for a target persona that persists across simulation sessions. Tracks the evolving relationship.

| Field | Type | Description |
|-------|------|-------------|
| `persona` | FK → `PersonaProfile` | The persona this state belongs to |
| `stance_score` | `FloatField` | 0–10; how close the target is to the desired action |
| `memory_summary` | `TextField` | Rolling narrative memory maintained across sessions |
| `open_objections_json` | `TextField` | JSON list of unresolved objections |
| `session_count` | `IntegerField` | Number of completed sessions with this persona |
| `last_outcome_label` | `CharField` | Outcome label from the last evaluation |
| `trigger_active` | `BooleanField` | Whether an autonomous follow-up is scheduled |
| `next_trigger_at` | `DateTimeField` | When the scheduled follow-up should fire |
| `updated_at` | `DateTimeField` | Auto-updated on save |

### `Scenario`

A single simulation session. Domain-agnostic — all domain-specific context is stored in `context_json`.

| Field | Type | Description |
|-------|------|-------------|
| `domain` | FK → `SimulationDomain` | The domain this scenario belongs to |
| `target_persona` | FK → `PersonaProfile` | The target persona (optional) |
| `persona_state` | FK → `PersonaState` | Current state snapshot (optional) |
| `title` | `CharField` | Auto-generated display title |
| `persuader_goal` | `TextField` | What the persuader is trying to achieve |
| `context_json` | `TextField` | JSON dict of all domain-specific context field values |
| `status` | `CharField` | `CREATED` → `RUNNING` → `COMPLETED` / `FAILED` |
| `conversation_log` | `TextField` | JSON list of `{agent, message}` dicts |
| `session_number` | `IntegerField` | Which session this is (1, 2, 3 … for multi-session personas) |
| `is_autonomous` | `BooleanField` | `True` when auto-created by the scheduler |
| `created_at` / `updated_at` | `DateTimeField` | Timestamps |

### `SimulationResult`

Goal-evaluation output produced by `GoalEvaluationService` after each session.

| Field | Type | Description |
|-------|------|-------------|
| `scenario` | OneToOne → `Scenario` | The scenario this result belongs to |
| `score` | `FloatField` | 0–10 score toward the domain's goal |
| `outcome_label` | `CharField` | Domain-specific outcome (e.g. `DEAL_AGREED`, `TRIAL_AGREED`) |
| `rationale` | `TextField` | LLM explanation of the score |
| `stance_delta` | `FloatField` | Change applied to `PersonaState.stance_score` |
| `memory_summary` | `TextField` | Rolling memory for the next session |
| `new_objections_json` | `TextField` | JSON list of unresolved objections |
| `next_step` | `TextField` | Recommended action for the persuader before next contact |
| `created_at` | `DateTimeField` | Auto-set on creation |

---

## Services

### `GoalEvaluationService` (`services/goal_evaluator.py`)

Evaluates a completed simulation session by calling the domain's `goal_evaluation_prompt`, parsing the LLM JSON response, saving a `SimulationResult`, and returning it so `run_simulation()` can update `PersonaState`.

**Mock fallback** (when no `OPENAI_API_KEY` is set): returns a fixed `FOLLOW_UP_AGREED` result with a `+0.5` stance delta.

### `PersonaGenerationService` (`services/persona_service.py`)

Generates a `PersonaProfile` from minimal seed inputs by calling the domain's `persona_generation_prompt`. Also creates an initial `PersonaState` with `stance_score=3.0` for target personas.

**Mock fallback**: returns a generic `"Mock Persona"` profile.

### `ScenarioGenerationService` (`services/scenario_generator.py`)

Generates multiple realistic scenario variants by calling the domain's `scenario_generation_prompt`. Returns a list of dicts ready to pre-fill the create-scenario form.

**Mock fallback**: returns a single `"Mock Scenario"` variant.

---

## Simulation Engine (`engine.py`)

### `DomainEngine`

The core conversation loop. On each `run_step()` call it:
1. Determines the next speaker (alternates persuader/target, persuader goes first).
2. Builds the full message history for the LLM call.
3. Calls the domain's appropriate system prompt generator.
4. Appends the reply to the scenario's `conversation_log` and saves.

### `run_simulation(scenario_id)`

Entry point called by views and the scheduler:
1. Loads the `Scenario` and resolves its domain config.
2. Runs `DomainEngine` for `domain_config.turns_per_session` turns.
3. Calls `GoalEvaluationService` to evaluate and save a `SimulationResult`.
4. Updates `PersonaState` (stance score, memory, objections, session count).
5. Schedules an autonomous follow-up if the score is below `success_threshold`.
6. Sets `scenario.status` to `COMPLETED` (or `FAILED` on error).

**Mock fallback** (no `OPENAI_API_KEY`): runs a fixed 4-turn mock conversation and sets status to `COMPLETED`.

---

## Scheduler (`scheduler.py`)

A background daemon thread (started by `SimCoreConfig.ready()`) that polls every 15 minutes for `PersonaState` records with `trigger_active=True` and `next_trigger_at <= now`. When found, it:

1. Creates a new follow-up `Scenario` based on the last completed session.
2. Marks the trigger as consumed (prevents double-fire).
3. Launches `run_simulation()` in a daemon thread.

---

## Views & URL Reference

All views are domain-agnostic. Domain-specific rendering is driven by the config's `context_fields` and `persona_seed_fields`.

| URL Pattern | View | Description |
|-------------|------|-------------|
| `/sim/` | `select_domain` | Domain selection landing page |
| `/sim/<domain_slug>/create/` | `create_scenario` | Create a new scenario |
| `/sim/monitor/<scenario_id>/` | `monitor_scenario` | Real-time monitoring page |
| `/sim/api/start/<scenario_id>/` | `api_start_simulation` | `POST` — start the simulation thread |
| `/sim/api/status/<scenario_id>/` | `api_get_status` | `GET` — poll conversation log and result |
| `/sim/api/<domain_slug>/generate-persona/` | `api_generate_persona` | `POST` — generate a `PersonaProfile` from seed inputs |
| `/sim/api/<domain_slug>/generate-scenarios/` | `api_generate_scenarios` | `POST` — generate scenario variants |

---

## Management Command

```bash
python manage.py bootstrap_domains
```

Seeds `SimulationDomain` rows from whatever is currently in `DOMAIN_REGISTRY`. Run this once after adding a new domain app to `INSTALLED_APPS` (or after the first `migrate`).

---

## Adding a New Domain

1. Create a new Django app (e.g. `legal_domain/`).
2. In `legal_domain/config.py`, subclass `BaseDomainConfig` and implement all five prompt methods plus the required class attributes.
3. In `legal_domain/apps.py`, register the domain in `ready()`:
   ```python
   from sim_core.base_domain import DOMAIN_REGISTRY
   from .config import LegalDomain

   class LegalDomainConfig(AppConfig):
       name = 'legal_domain'

       def ready(self):
           DOMAIN_REGISTRY[LegalDomain.slug] = LegalDomain()
   ```
4. Add `'legal_domain.apps.LegalDomainConfig'` to `INSTALLED_APPS` in `settings.py`.
5. Run `python manage.py bootstrap_domains` to create the `SimulationDomain` DB row.

No changes to `sim_core` are required.

---

## LLM Configuration

`sim_core` uses the OpenAI ChatCompletion API (`gpt-3.5-turbo` by default). Set the API key via environment variable:

```bash
export OPENAI_API_KEY="sk-..."
```

When the key is absent or the `openai` package is not installed, all services fall back to mock implementations so the application remains fully functional for demonstration purposes.
