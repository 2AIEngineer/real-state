"""Removing notification traces: of a deleted record, or of a closed account.

A permanently deleted record must not leave an inbox entry pointing at
nothing, nor a frozen recipient list. Callers invoke this explicitly, next to
the attachment cleanup of the same record.
"""

from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.notifications.models import (
    ExpoPushToken,
    InboxNotification,
    NotificationPreference,
    RecipientSnapshot,
)


def delete_notification_traces(target: models.Model) -> dict[str, int]:
    """Drop inbox entries and frozen recipients attached to `target`."""
    content_type = ContentType.objects.get_for_model(target)
    reference = {"content_type": content_type, "object_id": target.pk}
    inbox, _ = InboxNotification.objects.filter(**reference).delete()
    snapshots, _ = RecipientSnapshot.objects.filter(**reference).delete()
    return {"inbox": inbox, "snapshots": snapshots}


def erase_notifications_of(user) -> None:
    """What the notification module holds about a person whose account is closed:
    their devices, their inbox and their preferences."""
    ExpoPushToken.objects.filter(user=user).delete()
    InboxNotification.objects.filter(user=user).delete()
    NotificationPreference.objects.filter(user=user).delete()
