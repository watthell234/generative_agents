from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Scenario
import threading
from .simulation import run_simulation  # We will implement this next

def create_scenario(request):
    if request.method == 'POST':
        banker_idea = request.POST.get('banker_idea')
        client_persona = request.POST.get('client_persona')
        client_industry = request.POST.get('client_industry', 'General')
        financial_context = request.POST.get('financial_context', 'Stable')
        market_conditions = request.POST.get('market_conditions', 'Neutral')
        
        scenario = Scenario.objects.create(
            banker_idea=banker_idea,
            client_persona=client_persona,
            client_industry=client_industry,
            financial_context=financial_context,
            market_conditions=market_conditions,
            status='CREATED'
        )
        return redirect('monitor_scenario', scenario_id=scenario.id)
    
    return render(request, 'ib_sim/create_scenario.html')

def monitor_scenario(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    return render(request, 'ib_sim/monitor_scenario.html', {'scenario': scenario})

def api_start_simulation(request, scenario_id):
    if request.method == 'POST':
        scenario = get_object_or_404(Scenario, id=scenario_id)
        if scenario.status in ['CREATED', 'COMPLETED', 'FAILED']:
            scenario.status = 'RUNNING'
            scenario.save()
            
            # Start simulation in a background thread
            thread = threading.Thread(target=run_simulation, args=(scenario.id,))
            thread.start()
            
            return JsonResponse({'status': 'started'})
    return JsonResponse({'status': 'error'}, status=400)

def api_get_scenario_status(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    return JsonResponse({
        'status': scenario.status,
        'logs': scenario.get_conversation_log()
    })
