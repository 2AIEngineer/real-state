"""What people are told about short-term rentals."""

from __future__ import annotations

from apps.accounts.services.directory import UserDirectory
from apps.notifications.models import NotificationCategory, Severity
from apps.notifications.services import NotificationIntent, NotificationService
from apps.short_term_rental.models import InitiatorCapacity, ShortTermRental


def _tell(
    rental: ShortTermRental,
    *,
    kind: str,
    title: str,
    body: str,
    actor,
    to=(),
    include_management: bool = True,
    severity: str = Severity.INFO,
) -> None:
    NotificationService.notify(
        NotificationIntent(
            event_type=f"short_term_rental.{kind}",
            category=NotificationCategory.SHORT_TERM_RENTAL,
            title=title,
            body=body,
            to=list(to),
            bcc=(
                UserDirectory.management(rental.unit.building.property)
                if include_management
                else []
            ),
            target=rental,
            severity=severity,
            exclude=[actor] if actor else [],
            data={"short_term_rental_id": rental.pk, "unit_id": rental.unit_id},
            action_path=f"/short-term-rentals/{rental.pk}",
        )
    )


def _parties(rental: ShortTermRental) -> list:
    """Initiator plus the unit's owners and active tenants."""
    return [rental.initiated_by, *UserDirectory.unit_owners_and_tenants(rental.unit)]


def _period(rental: ShortTermRental) -> str:
    return f"du {rental.checkin_date:%d/%m/%Y} au {rental.checkout_date:%d/%m/%Y}"


def declared(rental: ShortTermRental, *, actor, occupants: int) -> None:
    unit = rental.unit
    if rental.initiator_capacity == InitiatorCapacity.MANAGEMENT:
        _tell(
            rental,
            kind="created",
            actor=actor,
            to=UserDirectory.unit_owners_and_tenants(unit),
            include_management=False,
            title=f"Location courte durée — lot {unit.number}",
            body=f"Une location courte durée a été enregistrée sur votre lot {_period(rental)}.",
        )
        return
    # Owners must know when their unit is sublet by a tenant.
    tenant_declared = rental.initiator_capacity == InitiatorCapacity.TENANT
    _tell(
        rental,
        kind="created",
        actor=actor,
        to=UserDirectory.unit_owners(unit) if tenant_declared else [],
        title=f"Nouvelle location courte durée — lot {unit.number}",
        body=(
            f"{actor.get_full_name()} a déclaré une location courte durée "
            f"{_period(rental)} ({occupants} occupant(s))."
        ),
    )


def rescheduled(rental: ShortTermRental, *, actor) -> None:
    _tell(
        rental,
        kind="updated",
        actor=actor,
        to=_parties(rental),
        title=f"Location courte durée modifiée — lot {rental.unit.number}",
        body=(
            f"Nouvelles dates : du {rental.checkin_date:%d/%m/%Y} "
            f"au {rental.checkout_date:%d/%m/%Y}."
        ),
    )


def completed(rental: ShortTermRental, *, actor) -> None:
    _tell(
        rental,
        kind="completed",
        actor=actor,
        to=_parties(rental),
        severity=Severity.SUCCESS,
        title=f"Location courte durée terminée — lot {rental.unit.number}",
        body="Les occupants ont quitté le logement.",
    )


def cancelled(rental: ShortTermRental, *, actor, reason: str) -> None:
    _tell(
        rental,
        kind="cancelled",
        actor=actor,
        to=_parties(rental),
        severity=Severity.WARNING,
        title=f"Location courte durée annulée — lot {rental.unit.number}",
        body=reason or f"La location courte durée {_period(rental)} est annulée.",
    )
