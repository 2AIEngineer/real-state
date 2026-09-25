"""Fill a development database with a complete, realistic residence portfolio.

    python manage.py seed_demo            # on an empty database
    python manage.py seed_demo --reset    # wipe the database first
    python manage.py seed_demo --seed 7   # another random draw

Every account can log in with the demo password printed at the end.
Notifications are written to the in-app inbox, but no e-mail or push is queued.
"""

import time

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test.utils import override_settings

from apps.demo.seed import PASSWORD, run
from apps.properties.models import Syndicat
from apps.service_requests.models import ServiceRequest


class Command(BaseCommand):
    help = "Generate complete demo data (2 syndicats, 4 properties, 8 buildings, 400 units…)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Wipe the database first.")
        parser.add_argument(
            "--seed", type=int, default=2026, help="Random seed (same seed, same data)."
        )

    def handle(self, *args, reset: bool, seed: int, **options):
        if settings.IS_PRODUCTION:
            raise CommandError("Demo data is never generated in production.")
        if reset:
            call_command("flush", interactive=False, verbosity=0)
        elif Syndicat.objects.exists():
            raise CommandError("The database already holds data: run with --reset to start over.")
        started = time.monotonic()
        quiet = {**settings.NOTIFICATIONS, "EMAIL_ENABLED": False, "PUSH_ENABLED": False}
        with override_settings(NOTIFICATIONS=quiet), transaction.atomic():
            demo = run(seed=seed, log=self.stdout.write)
        self._summary(demo, time.monotonic() - started)

    def _summary(self, demo, seconds: float) -> None:
        self.stdout.write(self.style.SUCCESS(f"\nDonnées de démo créées en {seconds:.0f} s."))
        self.stdout.write(f"Mot de passe de tous les comptes : {PASSWORD}\n")
        first = demo.residences[0]
        rows = [
            ("Administrateur", demo.admin),
            ("Syndic", demo.syndics[0]),
            ("Gérant", first.manager),
            ("Maintenance", first.maintenance[0]),
            ("Sécurité", next(iter(first.security.values()))),
            ("Ménage", next(iter(first.cleaning.values()))),
            ("Prestataire", demo.providers[0]),
            ("Propriétaire", _busiest(first.owners)),
            ("Locataire", _busiest(first.tenants)),
        ]
        for label, user in rows:
            self.stdout.write(f"  {label:<15} {user.email}")
        self.stdout.write(
            f"\nPropriété de départ : {first.prop.name} (syndicat {first.syndicat.name})"
        )


def _busiest(people: list):
    """The resident with the most service requests: the richest account to explore."""
    counts = {person.pk: 0 for person in people}
    for requester_id in ServiceRequest.objects.filter(requester__in=people).values_list(
        "requester_id", flat=True
    ):
        counts[requester_id] += 1
    best = max(counts, key=counts.get)
    return next(person for person in people if person.pk == best)
