"""Short-term rentals (short rentals with external members).

Who may declare a rental on a unit, and within which bounds:
- MANAGEMENT (admin/syndic/manager of the unit): any period free of other rentals.
- TENANT (active lease member): the rental must fit inside the lease they belong
  to, and start on/after they joined it.
- OWNER: only while no active lease covers the period (tenants hold the
  occupancy right during a lease).

    SCHEDULED ──check_in──▶ CHECKED_IN ──complete──▶ COMPLETED
    SCHEDULED ──cancel──▶ CANCELLED
"""

from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.common.db import translate_integrity_errors
from apps.common.deletion import destroy
from apps.common.exceptions import (
    InvalidInput,
    InvalidTransition,
    NotFound,
    PermissionDenied,
)
from apps.common.services.audit import AuditService
from apps.leasing.models import Lease
from apps.properties import timezones
from apps.properties.enums import Feature
from apps.properties.models import Property, Unit
from apps.properties.services import FeatureGate
from apps.short_term_rental import errors, notices
from apps.short_term_rental.audit import ShortTermRentalAudit
from apps.short_term_rental.models import (
    InitiatorCapacity,
    ShortTermRental,
    ShortTermRentalStatus,
)
from apps.short_term_rental.policies import ShortTermRentalPolicy
from apps.short_term_rental.services.members import ShortTermRentalMemberInput
from apps.short_term_rental.services.rules import (
    DeclarationRight,
    check_period,
    lock_rental,
    resolve_right,
)

RENTAL_CONSTRAINTS = {"short_term_rental_no_overlap_per_unit": errors.rental_overlap}


class ShortTermRentalService:
    @staticmethod
    def list_visible(
        *, actor, property_id: int, unit_id: int | None = None, status: str | None = None
    ) -> QuerySet[ShortTermRental]:
        qs = ShortTermRental.objects.filter(
            ShortTermRentalPolicy.visible_filter(actor)
        ).select_related("unit__building", "initiated_by", "primary_member")
        qs = qs.filter(unit__building__property_id=property_id)
        if unit_id:
            qs = qs.filter(unit_id=unit_id)
        if status:
            qs = qs.filter(status=status)
        return qs.distinct()

    @staticmethod
    def get_visible(*, actor, prop: Property, short_term_rental_id: int) -> ShortTermRental:
        rental = (
            ShortTermRental.objects.select_related(
                "unit__building__property", "initiated_by", "lease"
            )
            .filter(pk=short_term_rental_id, unit__building__property=prop)
            .first()
        )
        if rental is None or not ShortTermRentalPolicy.can_view(actor, rental):
            raise NotFound("Short rental not found.")
        return rental

    # --------------------------------------------------------------- mutations
    @staticmethod
    @transaction.atomic
    def declare(
        *,
        actor,
        unit: Unit,
        checkin_date: dt.date,
        checkout_date: dt.date,
        members: list[ShortTermRentalMemberInput],
        primary_index: int = 0,
        notes: str = "",
    ) -> ShortTermRental:
        FeatureGate.require(unit.building.property, Feature.SHORT_TERM_RENTAL)
        if not ShortTermRentalPolicy.can_declare(actor, unit):
            raise PermissionDenied(
                "Only the unit's tenants, owners or management can declare a short rental."
            )
        right = resolve_right(actor, unit)
        if not members:
            raise InvalidInput("At least one member is required.", field="members")
        if not 0 <= primary_index < len(members):
            raise InvalidInput("The primary member index is out of range.", field="primary_index")
        check_period(
            right, unit, checkin_date, checkout_date, today=timezones.today(unit.building.property)
        )
        with translate_integrity_errors(RENTAL_CONSTRAINTS):
            rental = ShortTermRental.objects.create(
                unit=unit,
                initiated_by=actor,
                initiator_capacity=right.capacity,
                lease=right.lease,
                checkin_date=checkin_date,
                checkout_date=checkout_date,
                notes=notes,
            )
        created = [member.create_for(rental) for member in members]
        rental.primary_member = created[primary_index]
        rental.save(update_fields=["primary_member", "updated_at"])
        AuditService.record(
            actor=actor,
            action=ShortTermRentalAudit.DECLARED,
            target=rental,
            property_id=rental.property_id,
        )

        notices.declared(rental, actor=actor, occupants=len(created))
        return rental

    @staticmethod
    @transaction.atomic
    def reschedule(
        *, actor, rental: ShortTermRental, checkin_date: dt.date, checkout_date: dt.date
    ) -> ShortTermRental:
        rental = lock_rental(rental)
        if not ShortTermRentalPolicy.can_update(actor, rental):
            raise NotFound("Short rental not found.")
        if rental.status != ShortTermRentalStatus.SCHEDULED:
            raise InvalidTransition("Only scheduled rentals can be rescheduled.")
        # The bounding rules are those of the capacity the rental was declared under;
        # management moving someone else's rental is bound by management rules.
        if rental.initiated_by_id == actor.pk:
            right = resolve_right(rental.initiated_by, rental.unit)
        else:
            right = DeclarationRight(InitiatorCapacity.MANAGEMENT)
        check_period(
            right,
            rental.unit,
            checkin_date,
            checkout_date,
            today=timezones.today(rental.unit.building.property),
        )
        rental.checkin_date, rental.checkout_date = checkin_date, checkout_date
        with translate_integrity_errors(RENTAL_CONSTRAINTS):
            rental.save(update_fields=["checkin_date", "checkout_date", "updated_at"])
        AuditService.record(
            actor=actor,
            action=ShortTermRentalAudit.RESCHEDULED,
            target=rental,
            property_id=rental.property_id,
        )
        notices.rescheduled(rental, actor=actor)
        return rental

    @staticmethod
    @transaction.atomic
    def check_in(*, actor, rental: ShortTermRental) -> ShortTermRental:
        rental = lock_rental(rental)
        if not ShortTermRentalPolicy.can_check_in(actor, rental):
            raise PermissionDenied("Only management or on-site security can record arrivals.")
        if rental.status != ShortTermRentalStatus.SCHEDULED:
            raise InvalidTransition("Only scheduled rentals can be checked in.")
        rental.status = ShortTermRentalStatus.CHECKED_IN
        rental.checked_in_at = timezone.now()
        rental.save(update_fields=["status", "checked_in_at", "updated_at"])
        AuditService.record(
            actor=actor,
            action=ShortTermRentalAudit.CHECKED_IN,
            target=rental,
            property_id=rental.property_id,
        )
        return rental

    @staticmethod
    @transaction.atomic
    def complete(*, actor, rental: ShortTermRental) -> ShortTermRental:
        rental = lock_rental(rental)
        if not ShortTermRentalPolicy.can_complete(actor, rental):
            raise PermissionDenied()
        if rental.status != ShortTermRentalStatus.CHECKED_IN:
            raise InvalidTransition("Only rentals in progress can be completed.")
        rental.status = ShortTermRentalStatus.COMPLETED
        rental.completed_at = timezone.now()
        rental.save(update_fields=["status", "completed_at", "updated_at"])
        AuditService.record(
            actor=actor,
            action=ShortTermRentalAudit.COMPLETED,
            target=rental,
            property_id=rental.property_id,
        )
        notices.completed(rental, actor=actor)
        return rental

    @staticmethod
    @transaction.atomic
    def cancel(*, actor, rental: ShortTermRental, reason: str = "") -> ShortTermRental:
        rental = lock_rental(rental)
        if actor and not ShortTermRentalPolicy.can_update(actor, rental):
            raise NotFound("Short rental not found.")
        if rental.status != ShortTermRentalStatus.SCHEDULED:
            raise InvalidTransition("Only scheduled rentals can be cancelled.")
        rental.status = ShortTermRentalStatus.CANCELLED
        rental.cancelled_at = timezone.now()
        rental.cancelled_by = actor
        rental.cancellation_reason = reason
        rental.save(
            update_fields=[
                "status",
                "cancelled_at",
                "cancelled_by",
                "cancellation_reason",
                "updated_at",
            ]
        )
        AuditService.record(
            actor=actor,
            action=ShortTermRentalAudit.CANCELLED,
            target=rental,
            property_id=rental.property_id,
            metadata={"reason": reason},
        )
        notices.cancelled(rental, actor=actor, reason=reason)
        return rental

    @staticmethod
    def on_lease_closed(*, lease: Lease, effective_date: dt.date) -> int:
        """A tenant's sublets cannot outlive the lease that allowed them."""
        affected = ShortTermRental.objects.filter(
            lease=lease, status=ShortTermRentalStatus.SCHEDULED, checkout_date__gt=effective_date
        )
        count = 0
        for rental in affected:
            ShortTermRentalService.cancel(
                actor=None,
                rental=rental,
                reason="Le bail rattaché à cette location courte durée a pris fin.",
            )
            count += 1
        return count

    @staticmethod
    @transaction.atomic
    def delete(*, actor, rental: ShortTermRental) -> None:
        """Permanent removal of a rental and of its members' documents."""
        if not ShortTermRentalPolicy.can_delete(actor, rental):
            raise PermissionDenied("Only the property management can delete a short rental.")
        AuditService.record(
            actor=actor,
            action=ShortTermRentalAudit.DELETED,
            target=rental,
            property_id=rental.property_id,
            metadata={"status": rental.status},
        )
        destroy(rental)
