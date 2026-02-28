from django.apps import AppConfig


class PharmaDomainConfig(AppConfig):
    name = 'pharma_domain'
    verbose_name = 'Pharma Consulting Domain'

    def ready(self):
        from .config import PharmaDomain
        from sim_core.base_domain import DOMAIN_REGISTRY
        DOMAIN_REGISTRY[PharmaDomain.slug] = PharmaDomain()
