"""What the people an event is addressed to are told about it."""

from __future__ import annotations

from apps.events.models import Event
from apps.notifications.models import NotificationCategory, Severity
from apps.notifications.services import (
    NotificationIntent,
    NotificationService,
    SnapshotService,
)
from apps.properties import timezones


def _tell(
    event: Event,
    *,
    kind: str,
    title: str,
    body: str,
    actor,
    severity: str = Severity.INFO,
):
    """Tell everyone the event was frozen for, by BCC."""
    NotificationService.notify(
        NotificationIntent(
            event_type=f"event.{kind}",
            category=NotificationCategory.EVENT,
            title=f"[{event.property.name}] {title}",
            body=body,
            bcc=SnapshotService.recipients(event),
            target=event,
            severity=severity,
            exclude=[actor] if actor else [],
            data={"event_id": event.pk, "property_id": event.property_id},
            action_path=f"/events/{event.pk}",
        )
    )


def _when(event: Event) -> str:
    where = f" — {event.location}" if event.location else ""
    return f"{timezones.local(event.property, event.start_at):%d/%m/%Y à %H:%M}{where}"


def created(event: Event, *, actor) -> None:
    _tell(
        event,
        kind="created",
        actor=actor,
        title=f"Nouvel événement : {event.title}",
        body=f"Le {_when(event)}",
    )


def updated(event: Event, *, actor) -> None:
    _tell(
        event,
        kind="updated",
        actor=actor,
        severity=Severity.WARNING,
        title=f"Événement modifié : {event.title}",
        body=f"Nouvelle date : {_when(event)}",
    )


def cancelled(event: Event, *, actor, reason: str) -> None:
    _tell(
        event,
        kind="cancelled",
        actor=actor,
        severity=Severity.WARNING,
        title=f"Événement annulé : {event.title}",
        body=reason or "Cet événement n'aura pas lieu.",
    )


def archived(event: Event, *, actor) -> None:
    _tell(
        event,
        kind="archived",
        actor=actor,
        severity=Severity.WARNING,
        title=f"Événement supprimé : {event.title}",
        body="Cet événement a été retiré du calendrier.",
    )


def completed(event: Event) -> None:
    _tell(
        event,
        kind="completed",
        actor=None,
        title="Événement terminé",
        body=f"« {event.title} » est terminé. Merci à tous les participants.",
    )
