from django.urls import path
from . import views

urlpatterns = [
    # Domain selection landing page
    path('', views.select_domain, name='select_domain'),

    # Scenario lifecycle
    path('<slug:domain_slug>/create/', views.create_scenario, name='create_scenario'),
    path('monitor/<int:scenario_id>/', views.monitor_scenario, name='monitor_scenario'),

    # Simulation control & polling
    path('api/start/<int:scenario_id>/', views.api_start_simulation, name='api_start_simulation'),
    path('api/status/<int:scenario_id>/', views.api_get_status, name='api_get_status'),

    # AI generation endpoints (domain-scoped)
    path('api/<slug:domain_slug>/generate-persona/', views.api_generate_persona, name='api_generate_persona'),
    path('api/<slug:domain_slug>/generate-scenarios/', views.api_generate_scenarios, name='api_generate_scenarios'),
]
