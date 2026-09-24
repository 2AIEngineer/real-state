"""How long delivery traces are kept."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.notifications.models import OutboxMessage, OutboxStatus


class OutboxRetention:
    @staticmethod
    def purge(*, now=None) -> int:
        """Delete the messages delivered or abandoned before the retention period."""
        days = settings.NOTIFICATIONS["OUTBOX_RETENTION_DAYS"]
        threshold = (now or timezone.now()) - timedelta(days=days)
        deleted, _ = OutboxMessage.objects.filter(
            status__in=(OutboxStatus.SENT, OutboxStatus.FAILED), created_at__lt=threshold
        ).delete()
        return deleted
