"""What the residents of a unit are told about its visitors."""

from __future__ import annotations

from apps.accounts.services.directory import UserDirectory
from apps.notifications.models import NotificationCategory, Severity
from apps.notifications.services import NotificationIntent, NotificationService
from apps.properties import timezones
from apps.visitors.models import Visitor, VisitStatus


def visitor_logged(visitor: Visitor, *, actor) -> None:
    """A visitor arrived, or was turned away: the unit's residents and the management know."""
    unit = visitor.unit
    name = f"{visitor.first_name} {visitor.last_name}"
    admitted = visitor.status == VisitStatus.ARRIVED
    if admitted:
        event, severity = "visitor.arrived", Severity.INFO
        title = f"Visiteur — lot {unit.number}"
        body = f"{name} est arrivé(e) à {timezones.local(visitor.property, visitor.arrived_at):%H:%M}."
    else:
        event, severity = "visitor.denied", Severity.WARNING
        title = f"Visite refusée — lot {unit.number}"
        body = f"L'accès a été refusé à {name} : {visitor.denial_reason}"
    NotificationService.notify(
        NotificationIntent(
            event_type=event,
            category=NotificationCategory.VISITOR,
            title=title,
            body=body,
            to=UserDirectory.unit_owners_and_tenants(unit),
            bcc=UserDirectory.management(unit.building.property),
            target=visitor,
            severity=severity,
            exclude=[actor],
            data={"visitor_id": visitor.pk, "unit_id": unit.pk},
            action_path=f"/visitors/{visitor.pk}",
        )
    )
