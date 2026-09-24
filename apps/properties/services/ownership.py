"""The ownership ledger of units: sales, co-owners, departures.

Invariant kept here, under the lock of the unit: a unit always has an active
owner. When the last one leaves without an acquirer, the promoter takes it back.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.db.models import QuerySet

from apps.common.db import deleting, translate_integrity_errors
from apps.common.exceptions import BusinessRuleViolation, InvalidInput, NotFound, PermissionDenied
from apps.common.services.audit import AuditService
from apps.notifications.services import delete_notification_traces
from apps.properties import notices, timezones
from apps.properties.audit import OwnershipAudit
from apps.properties.models import (
    OwnershipEndReason,
    OwnershipStatus,
    Property,
    Unit,
    UnitOwnership,
)
from apps.properties.policies import OwnershipPolicy

FULL_SHARE = Decimal("100")


@dataclass(frozen=True)
class Acquirer:
    user: object
    share: Decimal | None = None


# --------------------------------------------------------------------------- primitives
# Shared with the unit and property services; callers hold the lock of the unit.


def open_promoter_default(
    unit: Unit, *, prop: Property, start_date: dt.date, actor
) -> UnitOwnership:
    """The promoter's representative holds the unit until it is sold."""
    return UnitOwnership.objects.create(
        unit=unit,
        owner=prop.promoter.representative_user,
        ownership_share=FULL_SHARE,
        start_date=start_date,
        is_promoter_default=True,
        created_by=actor,
    )


def close_ownership(ownership: UnitOwnership, *, end_date: dt.date, reason: str, actor) -> None:
    if end_date < ownership.start_date:
        raise InvalidInput(
            f"The effective date cannot precede the start of ownership #{ownership.pk} "
            f"({ownership.start_date}).",
            field="effective_date",
        )
    ownership.status = OwnershipStatus.TERMINATED
    ownership.end_date = end_date
    ownership.end_reason = reason
    ownership.ended_by = actor
    ownership.save(update_fields=["status", "end_date", "end_reason", "ended_by", "updated_at"])


def _validate_shares(shares: list[Decimal | None]) -> None:
    explicit = [share for share in shares if share is not None]
    if any(share <= 0 or share > FULL_SHARE for share in explicit):
        raise InvalidInput("Ownership shares must be between 0 and 100.", field="share")
    if sum(explicit, Decimal("0")) > FULL_SHARE:
        raise InvalidInput("Ownership shares cannot exceed 100% in total.", field="share")


def _require_personal_accounts(users, *, message: str, field: str) -> None:
    if any(not user.is_active or user.is_technical_account for user in users):
        raise InvalidInput(message, field=field)


class OwnershipService:
    @staticmethod
    def history(*, actor, unit: Unit) -> QuerySet[UnitOwnership]:
        if not OwnershipPolicy.can_view_history(actor, unit):
            raise PermissionDenied()
        return UnitOwnership.objects.filter(unit=unit).select_related("owner")

    @staticmethod
    def active(unit: Unit) -> QuerySet[UnitOwnership]:
        return UnitOwnership.objects.filter(unit=unit, status=OwnershipStatus.ACTIVE)

    @staticmethod
    def get(*, ownership_id: int) -> UnitOwnership:
        ownership = (
            UnitOwnership.objects.select_related("unit__building__property", "owner")
            .filter(pk=ownership_id)
            .first()
        )
        if ownership is None:
            raise NotFound("Ownership not found.")
        return ownership

    # -- internals -----------------------------------------------------------------
    @staticmethod
    def _lock_unit(unit: Unit) -> Unit:
        return (
            Unit.objects.select_for_update(of=("self",))
            .select_related("building__property__promoter__representative_user")
            .get(pk=unit.pk)
        )

    @staticmethod
    def _ensure_not_orphan(unit: Unit, *, start_date: dt.date, actor) -> UnitOwnership | None:
        """Reversion to the promoter when the last active owner is gone."""
        if OwnershipService.active(unit).exists():
            return None
        return open_promoter_default(
            unit, prop=unit.building.property, start_date=start_date, actor=actor
        )

    # -- operations ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def transfer(
        *,
        actor,
        unit: Unit,
        acquirers: list[Acquirer],
        effective_date: dt.date,
        reference: str = "",
    ) -> list[UnitOwnership]:
        """Sale: every active ownership ends and the acquirers become owners."""
        if not OwnershipPolicy.can_change(actor, unit):
            raise PermissionDenied("Only the property management can change ownerships.")
        if not acquirers:
            raise InvalidInput("At least one acquirer is required.", field="acquirers")
        user_ids = [a.user.pk for a in acquirers]
        if len(set(user_ids)) != len(user_ids):
            raise InvalidInput("An acquirer is listed twice.", field="acquirers")
        _require_personal_accounts(
            [a.user for a in acquirers],
            message="Acquirers must be active personal accounts.",
            field="acquirers",
        )
        _validate_shares([a.share for a in acquirers])

        unit = OwnershipService._lock_unit(unit)
        previous = list(OwnershipService.active(unit).select_related("owner"))
        for ownership in previous:
            close_ownership(
                ownership, end_date=effective_date, reason=OwnershipEndReason.SALE, actor=actor
            )
        sole_acquirer = len(acquirers) == 1
        created = [
            UnitOwnership.objects.create(
                unit=unit,
                owner=a.user,
                ownership_share=a.share
                if a.share is not None
                else (FULL_SHARE if sole_acquirer else None),
                start_date=effective_date,
                acquisition_reference=reference,
                created_by=actor,
            )
            for a in acquirers
        ]
        AuditService.record(
            actor=actor,
            action=OwnershipAudit.TRANSFERRED,
            target=unit,
            property_id=unit.building.property_id,
            metadata={
                "from": [o.owner_id for o in previous],
                "to": user_ids,
                "effective_date": effective_date.isoformat(),
            },
        )
        notices.unit_transferred(
            unit,
            owners=[o.owner for o in previous] + [a.user for a in acquirers],
            effective_date=effective_date,
        )
        return created

    @staticmethod
    @transaction.atomic
    def add_co_owner(
        *, actor, unit: Unit, user, share: Decimal | None, start_date: dt.date
    ) -> UnitOwnership:
        """Joint ownership next to existing (non-promoter) owners."""
        if not OwnershipPolicy.can_change(actor, unit):
            raise PermissionDenied("Only the property management can change ownerships.")
        _require_personal_accounts(
            [user], message="Owners must be active personal accounts.", field="user_id"
        )
        unit = OwnershipService._lock_unit(unit)
        active = list(OwnershipService.active(unit))
        if any(o.is_promoter_default for o in active):
            raise BusinessRuleViolation(
                "The unit is still held by the promoter: record a sale (transfer) instead.",
                code="promoter_held",
            )
        _validate_shares([o.ownership_share for o in active] + [share])
        with translate_integrity_errors(
            {"unique_active_ownership_per_user_unit": "This user already owns this unit."}
        ):
            ownership = UnitOwnership.objects.create(
                unit=unit,
                owner=user,
                ownership_share=share,
                start_date=start_date,
                created_by=actor,
            )
        AuditService.record(
            actor=actor,
            action=OwnershipAudit.CO_OWNER_ADDED,
            target=ownership,
            property_id=unit.building.property_id,
        )
        notices.co_owner_added(unit, ownership)
        return ownership

    @staticmethod
    @transaction.atomic
    def end(
        *,
        actor,
        ownership: UnitOwnership,
        end_date: dt.date,
        reason: str = OwnershipEndReason.DEPARTURE,
    ) -> UnitOwnership:
        """End one ownership without a registered acquirer.

        If it was the last active one, the unit reverts to the promoter.
        """
        if not OwnershipPolicy.can_change(actor, ownership.unit):
            raise PermissionDenied("Only the property management can change ownerships.")
        unit = OwnershipService._lock_unit(ownership.unit)
        ownership = UnitOwnership.objects.select_for_update(of=("self",)).get(pk=ownership.pk)
        if ownership.status != OwnershipStatus.ACTIVE:
            raise BusinessRuleViolation("This ownership is already terminated.")
        if ownership.is_promoter_default:
            raise BusinessRuleViolation(
                "The promoter's default ownership ends only through a sale.",
                code="promoter_default",
            )
        close_ownership(ownership, end_date=end_date, reason=reason, actor=actor)
        reverted = OwnershipService._ensure_not_orphan(unit, start_date=end_date, actor=actor)
        AuditService.record(
            actor=actor,
            action=OwnershipAudit.ENDED,
            target=ownership,
            property_id=unit.building.property_id,
            metadata={"reason": reason, "reverted_to_promoter": reverted is not None},
        )
        notices.ownership_ended(unit, ownership, end_date=end_date)
        return ownership

    @staticmethod
    @transaction.atomic
    def delete(*, actor, ownership: UnitOwnership) -> None:
        """Erase a ledger line recorded by mistake.

        Ending an ownership is the normal path (`end`), which keeps the
        history; this one is for a line that should never have existed. The
        unit invariant still holds: if the last active line goes, the unit
        reverts to the promoter.
        """
        if not OwnershipPolicy.can_delete(actor, ownership):
            raise PermissionDenied("Only administrators and syndics can erase an ownership record.")
        unit = OwnershipService._lock_unit(ownership.unit)
        AuditService.record(
            actor=actor,
            action=OwnershipAudit.DELETED,
            target=ownership,
            property_id=unit.building.property_id,
            metadata={
                "unit_id": unit.pk,
                "owner_id": ownership.owner_id,
                "status": ownership.status,
            },
        )
        with deleting("ownership record"):
            delete_notification_traces(ownership)
            ownership.delete()
            OwnershipService._ensure_not_orphan(
                unit, start_date=timezones.today(unit.building.property), actor=actor
            )
