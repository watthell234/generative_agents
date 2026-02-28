"""
Management command: python manage.py bootstrap_domains

Seeds SimulationDomain rows from whatever is currently in DOMAIN_REGISTRY.
Run this after adding a new domain app to INSTALLED_APPS.
"""
from django.core.management.base import BaseCommand
from sim_core.models import SimulationDomain
from sim_core.base_domain import get_all_domains


class Command(BaseCommand):
    help = 'Seeds SimulationDomain DB rows from the Python DOMAIN_REGISTRY.'

    def handle(self, *args, **options):
        domains = get_all_domains()
        if not domains:
            self.stdout.write(self.style.WARNING(
                'No domains registered. Make sure domain apps are in INSTALLED_APPS '
                'and their AppConfig.ready() has been called.'
            ))
            return

        for domain in domains:
            obj, created = SimulationDomain.objects.get_or_create(
                slug=domain.slug,
                defaults={'label': domain.label, 'is_active': True},
            )
            if not created and obj.label != domain.label:
                obj.label = domain.label
                obj.save()

            verb = 'Created' if created else 'Already exists'
            self.stdout.write(self.style.SUCCESS(
                f'{verb}: {domain.label} (slug={domain.slug})'
            ))
