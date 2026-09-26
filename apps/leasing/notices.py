"""What people are told about leases."""

from __future__ import annotations

import datetime as dt

from apps.accounts.services.directory import UserDirectory
from apps.leasing.models import Lease
from apps.notifications.models import NotificationCategory
from apps.notifications.services import NotificationIntent, NotificationService


def _lease_event(lease: Lease, *, event: str, title: str, body: str, actor) -> None:
    """Tell the occupants, the owners of the unit and the property management."""
    unit = lease.unit
    occupants = [
        member.user for member in lease.active_members().select_related("user")
    ]
    NotificationService.notify(
        NotificationIntent(
            event_type=event,
            category=NotificationCategory.LEASING,
            title=title,
            body=body,
            to=occupants + list(UserDirectory.unit_owners(unit)),
            bcc=UserDirectory.management(unit.building.property),
            target=lease,
            exclude=[actor] if actor else [],
            include_platform_admins=False,
            data={"lease_id": lease.pk, "unit_id": unit.pk},
            action_path=f"/leases/{lease.pk}",
        )
    )


def lease_created(lease: Lease, *, actor) -> None:
    number = lease.unit.number
    _lease_event(
        lease,
        event="lease.created",
        actor=actor,
        title=f"Nouveau bail — lot {number}",
        body=(
            f"Un bail a été enregistré pour le lot {number} "
            f"à compter du {lease.start_date:%d/%m/%Y}."
        ),
    )


def lease_terminated(lease: Lease, *, effective_date: dt.date, actor) -> None:
    number = lease.unit.number
    _lease_event(
        lease,
        event="lease.terminated",
        actor=actor,
        title=f"Fin de bail — lot {number}",
        body=f"Le bail du lot {number} prend fin le {effective_date:%d/%m/%Y}.",
    )


def lease_cancelled(lease: Lease, *, actor) -> None:
    number = lease.unit.number
    _lease_event(
        lease,
        event="lease.cancelled",
        actor=actor,
        title=f"Bail annulé — lot {number}",
        body=(
            f"Le bail prévu à compter du {lease.start_date:%d/%m/%Y} "
            f"pour le lot {number} a été annulé."
        ),
    )


def member_added(lease: Lease, *, user) -> None:
    number = lease.unit.number
    NotificationService.notify(
        NotificationIntent(
            event_type="lease.member_added",
            category=NotificationCategory.LEASING,
            title=f"Ajout au bail — lot {number}",
            body=f"Vous avez été ajouté(e) comme occupant du lot {number}.",
            to=[user],
            target=lease,
            include_platform_admins=False,
        )
    )
