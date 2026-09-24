"""Community events: addressed to target roles, notified on creation, change and removal."""

from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.common.db import deleting
from apps.common.exceptions import InvalidInput, InvalidTransition, NotFound, PermissionDenied
from apps.common.files.rules import EntityType
from apps.common.files.service import AttachmentService
from apps.common.services.audit import AuditService
from apps.events import notices
from apps.events.audit import EventAudit
from apps.events.models import Event, EventStatus
from apps.events.policies import EventPolicy
from apps.notifications.services import SnapshotService, delete_notification_traces
from apps.properties.enums import Feature
from apps.properties.models import Building, Property
from apps.properties.services import FeatureGate

EDITABLE_FIELDS = ("title", "description", "location", "start_at", "end_at")
# Changes worth telling attendees about (typos in the description are not).
SIGNIFICANT_FIELDS = frozenset({"title", "location", "start_at", "end_at"})


def _validate_schedule(start_at: dt.datetime, end_at: dt.datetime) -> None:
    if end_at <= start_at:
        raise InvalidInput("An event must end after it starts.", field="end_at")


class EventService:
    @staticmethod
    def list_visible(
        *,
        actor,
        prop: Property,
        status: str | None = None,
        starts_after: dt.datetime | None = None,
        starts_before: dt.datetime | None = None,
    ) -> QuerySet[Event]:
        if not EventPolicy.can_list(actor, prop):
            raise PermissionDenied("You have no link with this property.")
        FeatureGate.require(prop, Feature.EVENTS)
        qs = (
            Event.objects.not_archived()
            .filter(property=prop)
            .filter(EventPolicy.visible_filter(actor))
            .select_related("building", "created_by")
        )
        if status:
            qs = qs.filter(status=status)
        if starts_after:
            qs = qs.filter(start_at__gte=starts_after)
        if starts_before:
            qs = qs.filter(start_at__lt=starts_before)
        return qs

    @staticmethod
    def get_visible(*, actor, prop: Property, event_id: int) -> Event:
        event = (
            Event.objects.not_archived()
            .filter(pk=event_id, property=prop)
            .filter(EventPolicy.visible_filter(actor))
            .select_related("property", "building", "created_by")
            .first()
        )
        if event is None:
            raise NotFound("Event not found.")
        return event

    @staticmethod
    def get_manageable(*, actor, prop: Property, event_id: int) -> Event:
        """Lookup for management actions, archived records included.

        A archived event is out of everyone's feed but must stay reachable
        for the people who may erase it for good.
        """
        event = Event.objects.select_related("property").filter(pk=event_id, property=prop).first()
        if event is None or not EventPolicy.can_update(actor, event):
            raise NotFound("Event not found.")
        return event

    @staticmethod
    @transaction.atomic
    def create(
        *,
        actor,
        prop: Property,
        title: str,
        start_at: dt.datetime,
        end_at: dt.datetime,
        target_roles: list[str],
        description: str = "",
        location: str = "",
        building: Building | None = None,
        files=(),
    ) -> Event:
        if not EventPolicy.can_create(actor, prop):
            raise PermissionDenied("Only the property management can create events.")
        FeatureGate.require(prop, Feature.EVENTS)
        roles = SnapshotService.validate_target_roles(target_roles)
        _validate_schedule(start_at, end_at)
        if end_at <= timezone.now():
            raise InvalidInput("An event cannot be scheduled entirely in the past.", field="end_at")
        if building is not None and building.property_id != prop.pk:
            raise InvalidInput("The building belongs to another property.", field="building_id")
        event = Event.objects.create(
            property=prop,
            building=building,
            title=title.strip(),
            description=description,
            location=location,
            start_at=start_at,
            end_at=end_at,
            target_roles=roles,
            created_by=actor,
        )
        AttachmentService.attach(
            entity_type=EntityType.EVENT, entity_id=event.pk, files=list(files), uploaded_by=actor
        )
        SnapshotService.freeze(target=event, prop=prop, target_roles=roles, building=building)
        AuditService.record(
            actor=actor, action=EventAudit.CREATED, target=event, property_id=prop.pk
        )
        notices.created(event, actor=actor)
        return event

    @staticmethod
    def _lock_scheduled(event: Event) -> Event:
        event = (
            Event.objects.select_for_update(of=("self",))
            .select_related("property")
            .get(pk=event.pk)
        )
        if event.archived_at is not None:
            raise NotFound("Event not found.")
        if event.status != EventStatus.SCHEDULED:
            raise InvalidTransition("Only scheduled events can be changed.")
        return event

    @staticmethod
    @transaction.atomic
    def update(*, actor, event: Event, changes: dict) -> Event:
        if not EventPolicy.can_update(actor, event):
            raise PermissionDenied("Only the property management can edit events.")
        if "target_roles" in changes or "building" in changes:
            raise InvalidInput(
                "The target roles of a published event cannot change.", field="target_roles"
            )
        event = EventService._lock_scheduled(event)
        fields = [
            name
            for name in EDITABLE_FIELDS
            if name in changes and getattr(event, name) != changes[name]
        ]
        for name in fields:
            setattr(event, name, changes[name])
        _validate_schedule(event.start_at, event.end_at)
        if not fields:
            return event
        event.save(update_fields=[*fields, "updated_at"])
        AuditService.record(
            actor=actor,
            action=EventAudit.UPDATED,
            target=event,
            property_id=event.property_id,
            metadata={"fields": fields},
        )
        if SIGNIFICANT_FIELDS & set(fields):
            notices.updated(event, actor=actor)
        return event

    @staticmethod
    @transaction.atomic
    def cancel(*, actor, event: Event, reason: str = "") -> Event:
        if not EventPolicy.can_cancel(actor, event):
            raise PermissionDenied("Only the property management can cancel events.")
        event = EventService._lock_scheduled(event)
        event.status = EventStatus.CANCELLED
        event.cancelled_at = timezone.now()
        event.cancellation_reason = reason
        event.save(update_fields=["status", "cancelled_at", "cancellation_reason", "updated_at"])
        AuditService.record(
            actor=actor, action=EventAudit.CANCELLED, target=event, property_id=event.property_id
        )
        notices.cancelled(event, actor=actor, reason=reason)
        return event

    @staticmethod
    @transaction.atomic
    def delete(*, actor, event) -> None:
        """Permanent removal, files and delivered notifications included."""
        if not EventPolicy.can_delete(actor, event):
            raise PermissionDenied(
                "Only administrators and syndics can permanently delete this record."
            )
        AuditService.record(
            actor=actor,
            action=EventAudit.DELETED,
            target=event,
            property_id=event.property_id,
            metadata={"title": event.title},
        )
        with deleting("event"):
            AttachmentService.delete_for_entity(EntityType.EVENT, event.pk)
            delete_notification_traces(event)
            event.delete()

    @staticmethod
    @transaction.atomic
    def archive(*, actor, event: Event) -> None:
        if not EventPolicy.can_archive(actor, event):
            raise PermissionDenied("Only the property management can archive events.")
        event = (
            Event.objects.select_for_update(of=("self",))
            .select_related("property")
            .get(pk=event.pk)
        )
        was_upcoming = event.status == EventStatus.SCHEDULED and event.end_at > timezone.now()
        event.archived_at = timezone.now()
        event.archived_by = actor
        event.save(update_fields=["archived_at", "archived_by", "updated_at"])
        AuditService.record(
            actor=actor, action=EventAudit.ARCHIVED, target=event, property_id=event.property_id
        )
        if was_upcoming:
            notices.archived(event, actor=actor)

    @staticmethod
    @transaction.atomic
    def add_files(*, actor, event: Event, files) -> list:
        if not EventPolicy.can_update(actor, event):
            raise PermissionDenied("Only the property management can edit events.")
        return AttachmentService.attach(
            entity_type=EntityType.EVENT, entity_id=event.pk, files=list(files), uploaded_by=actor
        )

    @staticmethod
    @transaction.atomic
    def remove_file(*, actor, event: Event, attachment_id: int) -> None:
        if not EventPolicy.can_update(actor, event):
            raise PermissionDenied("Only the property management can edit events.")
        AttachmentService.delete(
            attachment=AttachmentService.get(
                entity_type=EntityType.EVENT, entity_id=event.pk, attachment_id=attachment_id
            )
        )

    @staticmethod
    def complete_past(*, now: dt.datetime | None = None) -> int:
        """Scheduled job: events whose end has passed become COMPLETED.

        The people the event was addressed to are told it is over, each event
        in its own transaction so one failure does not block the others.
        """
        now = now or timezone.now()
        due = Event.objects.filter(
            status=EventStatus.SCHEDULED, end_at__lt=now, archived_at__isnull=True
        )
        completed = 0
        for event_id in due.values_list("id", flat=True):
            with transaction.atomic():
                event = (
                    Event.objects.select_for_update(of=("self",), skip_locked=True)
                    .select_related("property")
                    .filter(pk=event_id, status=EventStatus.SCHEDULED)
                    .first()
                )
                if event is None:
                    continue  # completed meanwhile, or being handled by another run
                event.status = EventStatus.COMPLETED
                event.completed_at = now
                event.save(update_fields=["status", "completed_at", "updated_at"])
                notices.completed(event)
                completed += 1
        return completed
