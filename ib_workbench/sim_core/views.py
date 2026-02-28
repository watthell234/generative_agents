import json
import threading

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import SimulationDomain, PersonaProfile, PersonaState, Scenario
from .base_domain import get_all_domains, get_domain
from .engine import run_simulation
from .services.persona_service import PersonaGenerationService
from .services.scenario_generator import ScenarioGenerationService


def select_domain(request):
    """Landing page — show all registered domains as selectable cards."""
    domains = get_all_domains()
    return render(request, 'sim_core/select_domain.html', {'domains': domains})


def create_scenario(request, domain_slug):
    """
    Create a new simulation scenario for the given domain.
    Context fields and persona seed fields are driven entirely by the domain config,
    so this view and template work for any domain without modification.
    """
    domain_config = get_domain(domain_slug)
    domain_obj = get_object_or_404(SimulationDomain, slug=domain_slug)
    personas = PersonaProfile.objects.filter(
        domain=domain_obj, role='target'
    ).order_by('-created_at')

    if request.method == 'POST':
        persuader_goal = request.POST.get('persuader_goal', '').strip()

        # Collect all domain-specific context field values
        context = {}
        for field in domain_config.context_fields:
            context[field['key']] = request.POST.get(field['key'], '')

        # Attach an existing persona if selected
        persona_id = request.POST.get('persona_id')
        target_persona = None
        persona_state = None
        if persona_id:
            try:
                target_persona = PersonaProfile.objects.get(id=int(persona_id), domain=domain_obj)
                persona_state = target_persona.states.order_by('-updated_at').first()
            except (PersonaProfile.DoesNotExist, ValueError):
                pass

        scenario = Scenario(
            domain=domain_obj,
            target_persona=target_persona,
            persona_state=persona_state,
            title=f"{domain_config.label}: {persuader_goal[:60]}",
            persuader_goal=persuader_goal,
            status='CREATED',
        )
        scenario.set_context(context)
        scenario.save()

        return redirect('monitor_scenario', scenario_id=scenario.id)

    return render(request, 'sim_core/create_scenario.html', {
        'domain': domain_config,
        'domain_obj': domain_obj,
        'personas': personas,
    })


def monitor_scenario(request, scenario_id):
    """Real-time monitoring page for an in-progress or completed scenario."""
    scenario = get_object_or_404(Scenario, id=scenario_id)
    domain_config = scenario.domain.get_config()
    result = getattr(scenario, 'result', None)
    return render(request, 'sim_core/monitor_scenario.html', {
        'scenario': scenario,
        'domain': domain_config,
        'context_items': list(scenario.get_context().items()),
        'result': result,
    })


# ------------------------------------------------------------------
# API endpoints
# ------------------------------------------------------------------

@require_POST
def api_start_simulation(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    if scenario.status in ('CREATED', 'COMPLETED', 'FAILED'):
        scenario.status = 'RUNNING'
        scenario.save()
        t = threading.Thread(target=run_simulation, args=(scenario.id,), daemon=True)
        t.start()
        return JsonResponse({'status': 'started'})
    return JsonResponse({'status': 'error', 'detail': 'Simulation already running'}, status=400)


def api_get_status(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    result_data = None
    if hasattr(scenario, 'result'):
        r = scenario.result
        result_data = {
            'score': r.score,
            'outcome_label': r.outcome_label,
            'rationale': r.rationale,
            'next_step': r.next_step,
        }
    return JsonResponse({
        'status': scenario.status,
        'logs': scenario.get_conversation_log(),
        'result': result_data,
    })


@require_POST
def api_generate_persona(request, domain_slug):
    """
    POST body: JSON dict of persona_seed_field values.
    Returns: {persona_id, name, profile}
    """
    domain_config = get_domain(domain_slug)
    try:
        seed_inputs = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    service = PersonaGenerationService()
    persona = service.generate(domain_config, seed_inputs)
    return JsonResponse({
        'persona_id': persona.id,
        'name': persona.name,
        'profile': persona.get_profile(),
    })


@require_POST
def api_generate_scenarios(request, domain_slug):
    """
    POST body: {persuader_goal, seed_inputs, count}
    Returns: {variants: [...]}
    """
    domain_config = get_domain(domain_slug)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    persuader_goal = data.get('persuader_goal', '')
    seed_inputs = data.get('seed_inputs', {})
    count = int(data.get('count', 3))

    service = ScenarioGenerationService()
    variants = service.generate_variants(domain_config, persuader_goal, seed_inputs, count)
    return JsonResponse({'variants': variants})
