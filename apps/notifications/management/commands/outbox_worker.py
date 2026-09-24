"""Relay process of the transactional outbox (e-mail + Expo push).

Run one or more instances (rows are claimed with SKIP LOCKED):

    python manage.py outbox_worker            # loop forever
    python manage.py outbox_worker --once     # single batch (cron / tests)
"""

import logging
import signal
import time

from django.core.management.base import BaseCommand

from apps.notifications.services import OutboxRelay

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Deliver pending notification messages from the outbox."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process one batch then exit.")
        parser.add_argument(
            "--interval",
            type=float,
            default=2.0,
            help="Idle sleep between polls (seconds).",
        )
        parser.add_argument("--batch-size", type=int, default=None)

    def handle(self, *args, once: bool, interval: float, batch_size: int | None, **options):
        stopping = False
        consecutive_failures = 0

        def _stop(*_):
            nonlocal stopping
            stopping = True

        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)
        while not stopping:
            try:
                handled = OutboxRelay.run_once(batch_size)
            except Exception:
                consecutive_failures += 1
                logger.exception(
                    "outbox_worker: run_once failed (%d consecutive)",
                    consecutive_failures,
                )
                if once:
                    raise  # laisse un run cron/test échouer visiblement
                time.sleep(min(interval * (2**consecutive_failures), 60))
                continue

            consecutive_failures = 0
            if handled:
                self.stdout.write(f"Delivered/attempted {handled} message(s).")
            if once:
                break
            if not handled:
                time.sleep(interval)
