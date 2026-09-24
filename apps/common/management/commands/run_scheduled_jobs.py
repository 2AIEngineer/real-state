"""Time-driven transitions. Schedule it (cron, k8s CronJob…) e.g. every 15 min.

Each job is an idempotent service call: running it twice changes nothing.
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.services.tokens import TokenService
from apps.events.services import EventService
from apps.leasing.services import LeaseService
from apps.notifications.services import OutboxRetention
from apps.surveys.services import SurveyService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Time-driven transitions and housekeeping (idempotent)."

    def handle(self, *args, **options):
        jobs = {
            "leases terminated at term": LeaseService.expire_due,
            "events completed": EventService.complete_past,
            "surveys closed": SurveyService.close_expired,
            "outbox messages purged": OutboxRetention.purge,
            "expired session tokens flushed": TokenService.flush_expired,
        }
        failures = []
        for label, job in jobs.items():
            try:
                result = job()
            except Exception:
                logger.exception("scheduled job failed: %s", label)
                failures.append(label)
                continue
            self.stdout.write(f"{label}: {result}")
            logger.info("scheduled job succeeded: %s -> %s", label, result)

        if failures:
            raise CommandError(f"failed jobs: {', '.join(failures)}")
