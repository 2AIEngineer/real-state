"""Deleting a record for good, with everything that belongs to it.

Deleting is a deliberate, destructive action; archiving is the alternative
that keeps things. So a deletion is never refused because other records point
at the row: they are deleted with it (foreign keys cascade). The only
references that stay protected are those to user accounts, which are never
deleted but closed (see `AccountStatusService.close`).

Files and notifications point at a record by type and id, without a foreign
key, so the database cannot cascade to them. `destroy` collects every row the
deletion reaches, cascades included, and removes their files and their
notification traces in the same transaction.
"""

from __future__ import annotations

from collections import defaultdict

from django.db import router, transaction
from django.db.models import Model
from django.db.models.deletion import Collector

from apps.common.attachments.rules import entity_types_owned_by
from apps.common.attachments.service import AttachmentService


def _rows_reached(obj: Model) -> dict[type[Model], set[int]]:
    """Every row the deletion of `obj` removes, by model, cascades included."""
    collector = Collector(using=router.db_for_write(type(obj)), origin=obj)
    collector.collect([obj])
    reached: dict[type[Model], set[int]] = defaultdict(set)
    for model, instances in collector.data.items():
        reached[model].update(instance.pk for instance in instances)
    for queryset in collector.fast_deletes:
        reached[queryset.model].update(queryset.values_list("pk", flat=True))
    return reached


@transaction.atomic
def destroy(obj: Model) -> None:
    """Delete `obj`, what cascades from it, and the files and notifications of all of it."""
    # Local import: notifications sit above the shared kernel.
    from apps.notifications.services import delete_notification_traces_of

    for model, pks in _rows_reached(obj).items():
        for entity_type in entity_types_owned_by(model._meta.label):
            AttachmentService.delete_for_entities(entity_type, pks)
        delete_notification_traces_of(model, pks)
    obj.delete()
