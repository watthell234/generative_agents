from django.apps import AppConfig


class SimCoreConfig(AppConfig):
    name = 'sim_core'
    verbose_name = 'Simulation Core'

    def ready(self):
        from .scheduler import start_scheduler
        start_scheduler()
