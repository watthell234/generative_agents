from django.contrib import admin
from .models import SimulationDomain, PersonaProfile, PersonaState, Scenario, SimulationResult


@admin.register(SimulationDomain)
class SimulationDomainAdmin(admin.ModelAdmin):
    list_display = ('label', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active',)


@admin.register(PersonaProfile)
class PersonaProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'role', 'created_at')
    list_filter = ('domain', 'role')
    search_fields = ('name',)


@admin.register(PersonaState)
class PersonaStateAdmin(admin.ModelAdmin):
    list_display = ('persona', 'stance_score', 'session_count', 'last_outcome_label',
                    'trigger_active', 'next_trigger_at', 'updated_at')
    list_filter = ('trigger_active', 'last_outcome_label')
    search_fields = ('persona__name',)


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'domain', 'title', 'status', 'session_number',
                    'is_autonomous', 'created_at')
    list_filter = ('domain', 'status', 'is_autonomous')
    search_fields = ('title', 'persuader_goal')


@admin.register(SimulationResult)
class SimulationResultAdmin(admin.ModelAdmin):
    list_display = ('scenario', 'score', 'outcome_label', 'stance_delta', 'created_at')
    list_filter = ('outcome_label',)
