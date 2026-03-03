from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_scenario, name='create_scenario'),
    path('monitor/<int:scenario_id>/', views.monitor_scenario, name='monitor_scenario'),
    path('api/start/<int:scenario_id>/', views.api_start_simulation, name='api_start_simulation'),
    path('api/status/<int:scenario_id>/', views.api_get_scenario_status, name='api_get_scenario_status'),
]
