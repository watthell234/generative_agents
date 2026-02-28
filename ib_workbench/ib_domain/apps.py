from django.apps import AppConfig


class IBDomainConfig(AppConfig):
    name = 'ib_domain'
    verbose_name = 'Investment Banking Domain'

    def ready(self):
        from .config import InvestmentBankingDomain
        from sim_core.base_domain import DOMAIN_REGISTRY
        DOMAIN_REGISTRY[InvestmentBankingDomain.slug] = InvestmentBankingDomain()
