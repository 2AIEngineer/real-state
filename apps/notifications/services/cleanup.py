"""Removing the notification traces of deleted records.

A permanently deleted record must not leave an inbox entry pointing at
nothing, nor a frozen recipient list. Callers invoke this explicitly, next to
the attachment cleanup of the same record.
"""

from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.notifications.models import (
    InboxNotification,
    RecipientSnapshot,
)


def delete_notification_traces(target: models.Model) -> dict[str, int]:
    """Drop inbox entries and frozen recipients attached to `target`."""
    return delete_notification_traces_of(type(target), [target.pk])


def delete_notification_traces_of(model: type[models.Model], pks) -> dict[str, int]:
    """Same, for several rows of one model (a deletion and its cascades)."""
    content_type = ContentType.objects.get_for_model(model)
    reference = {"content_type": content_type, "object_id__in": list(pks)}
    inbox, _ = InboxNotification.objects.filter(**reference).delete()
    snapshots, _ = RecipientSnapshot.objects.filter(**reference).delete()
    return {"inbox": inbox, "snapshots": snapshots}
