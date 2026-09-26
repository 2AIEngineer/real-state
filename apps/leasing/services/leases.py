"""Lease lifecycle: creation, edition, termination, cancellation, deletion."""

from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.db.models import Prefetch, QuerySet
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
from apps.leasing import errors, notices
from apps.leasing.audit import LeaseAudit
from apps.leasing.models import Lease, LeaseMember, LeaseStatus, LeaseTerminationReason
from apps.leasing.policies import LeasePolicy
from apps.leasing.services.members import LeaseMemberService
from apps.leasing.services.rules import (
    MemberInput,
    check_member_account,
    check_member_dates,
    lock_active_lease,
)
from apps.properties import timezones
from apps.properties.models import Property, Unit
from apps.properties.policies import HousekeepingPolicy

LEASE_CONSTRAINTS = {
    "lease_no_overlapping_active_per_unit": errors.lease_overlap,
    "lease_contract_reference_unique": errors.contract_reference_taken,
}


def _cancel_dependent_sublets(lease: Lease, effective_date: dt.date) -> None:
    """A tenant's short rentals cannot outlive the lease that allowed them.

    Called wherever a lease leaves the ACTIVE state. Local import: the
    short-rental module is built on top of leasing.
    """
    from apps.short_term_rental.services import ShortTermRentalService

    ShortTermRentalService.on_lease_closed(lease=lease, effective_date=effective_date)


class LeaseService:
    # ---------------------------------------------------------------- queries
    @staticmethod
    def _base() -> QuerySet[Lease]:
        return Lease.objects.select_related(
            "unit__building__property"
        ).prefetch_related(
            Prefetch("members", queryset=LeaseMember.objects.select_related("user"))
        )

    @staticmethod
    def list_visible(
        *,
        actor,
        property_id: int,
        unit_id: int | None = None,
        status: str | None = None,
    ) -> QuerySet[Lease]:
        leases = (
            LeaseService._base().filter(LeasePolicy.visible_filter(actor)).distinct()
        )
        leases = leases.filter(unit__building__property_id=property_id)
        if unit_id:
            leases = leases.filter(unit_id=unit_id)
        if status:
            leases = leases.filter(status=status)
        return leases

    @staticmethod
    def get_visible(*, actor, prop: Property, lease_id: int) -> Lease:
        lease = (
            LeaseService._base()
            .filter(pk=lease_id, unit__building__property=prop)
            .first()
        )
        if lease is None or not LeasePolicy.can_view(actor, lease):
            raise NotFound("Lease not found.")
        return lease

    @staticmethod
    def active_lease_of_unit(unit: Unit) -> Lease | None:
        """The lease currently running on the unit, if there is one."""
        return (
            Lease.objects.filter(unit=unit, status=LeaseStatus.ACTIVE)
            .order_by("start_date")
            .first()
        )

    # ---------------------------------------------------------------- creation
    @staticmethod
    @transaction.atomic
    def create(
        *,
        actor,
        unit: Unit,
        start_date: dt.date,
        members: list[MemberInput],
        end_date: dt.date | None = None,
        contract_reference: str | None = None,
        notes: str = "",
    ) -> Lease:
        if not LeasePolicy.can_create(actor, unit):
            raise PermissionDenied("Only the property management can create leases.")
        LeaseService._check_new_lease(members, start_date=start_date, end_date=end_date)

        # Serialise lease creation per unit (the exclusion constraint is the
        # safety net; the lock gives a clean error instead of a race).
        Unit.objects.select_for_update(of=("self",)).filter(pk=unit.pk).first()
        with translate_integrity_errors(LEASE_CONSTRAINTS):
            lease = Lease.objects.create(
                unit=unit,
                start_date=start_date,
                end_date=end_date,
                contract_reference=contract_reference or None,
                notes=notes,
                created_by=actor,
            )
        for member in members:
            joined_at = member.joined_at or start_date
            check_member_dates(lease, joined_at)
            LeaseMember.objects.create(
                lease=lease,
                user=member.user,
                joined_at=joined_at,
                is_signatory=member.is_signatory,
                added_by=actor,
                **member.extra_fields(),
            )
        AuditService.record(
            actor=actor,
            action=LeaseAudit.CREATED,
            target=lease,
            property_id=lease.property_id,
            metadata={"members": [m.user.pk for m in members]},
        )
        notices.lease_created(lease, actor=actor)
        return lease

    @staticmethod
    def _check_new_lease(
        members: list[MemberInput], *, start_date: dt.date, end_date: dt.date | None
    ) -> None:
        if not members:
            raise InvalidInput(
                "An active lease needs at least one member.", field="members"
            )
        if not any(m.is_signatory for m in members):
            raise InvalidInput(
                "At least one member must be a signatory of the lease.", field="members"
            )
        user_ids = [m.user.pk for m in members]
        if len(set(user_ids)) != len(user_ids):
            raise InvalidInput("A user is listed twice.", field="members")
        if end_date and end_date < start_date:
            raise InvalidInput(
                "The lease cannot end before it starts.", field="end_date"
            )
        for member in members:
            check_member_account(member.user)

    @staticmethod
    @transaction.atomic
    def record_tenant(
        *,
        actor,
        unit: Unit,
        user,
        start_date: dt.date | None = None,
        end_date: dt.date | None = None,
        contract_reference: str | None = None,
        is_signatory: bool = False,
    ) -> LeaseMember:
        """Record `user` as a tenant of `unit`, whether the unit is already rented or not.

        Renting is always a lease: when one is already running on the unit the
        tenant joins it, and when there is none the lease opens with them as
        its signatory — a first tenant has nothing to join. Both paths go
        through the operations above, so the journal, the notifications and the
        rules of a lease are the same as if it had been recorded by hand.
        """
        lease = LeaseService.active_lease_of_unit(unit)
        if lease is not None:
            return LeaseMemberService.add(
                actor=actor,
                lease=lease,
                member=MemberInput(user=user, is_signatory=is_signatory),
            )
        lease = LeaseService.create(
            actor=actor,
            unit=unit,
            start_date=start_date or timezones.today(unit.building.property),
            end_date=end_date,
            contract_reference=contract_reference,
            members=[MemberInput(user=user, is_signatory=True)],
        )
        return lease.members.get(user=user)

    # ---------------------------------------------------------------- lifecycle
    @staticmethod
    @transaction.atomic
    def update(*, actor, lease: Lease, changes: dict) -> Lease:
        if not LeasePolicy.can_update(actor, lease):
            raise PermissionDenied("Only the property management can edit leases.")
        lease = lock_active_lease(lease)
        fields = []
        if "end_date" in changes:
            end_date = changes["end_date"]
            if end_date and end_date < lease.start_date:
                raise InvalidInput(
                    "The lease cannot end before it starts.", field="end_date"
                )
            if end_date and lease.members.filter(joined_at__gt=end_date).exists():
                raise InvalidInput(
                    "A member joins after this end date.", field="end_date"
                )
            lease.end_date = end_date
            fields.append("end_date")
        if "contract_reference" in changes:
            lease.contract_reference = changes["contract_reference"] or None
            fields.append("contract_reference")
        if "notes" in changes:
            lease.notes = changes["notes"]
            fields.append("notes")
        if fields:
            with translate_integrity_errors(LEASE_CONSTRAINTS):
                lease.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=LeaseAudit.UPDATED,
                target=lease,
                property_id=lease.property_id,
                metadata={"fields": fields},
            )
        return lease

    @staticmethod
    @transaction.atomic
    def terminate(
        *,
        actor,
        lease: Lease,
        effective_date: dt.date,
        reason: str = LeaseTerminationReason.OTHER,
    ) -> Lease:
        """Close the lease at its term or early. Members are frozen as-is:
        their rows keep the last known occupancy (rights end with the status)."""
        if actor and not LeasePolicy.can_terminate(actor, lease):
            raise PermissionDenied("Only the property management can terminate leases.")
        lease = lock_active_lease(lease)
        if effective_date < lease.start_date:
            raise InvalidInput(
                "A lease that never took effect must be cancelled, not terminated.",
                field="effective_date",
            )
        if lease.end_date and effective_date > lease.end_date:
            raise InvalidInput(
                "The termination date cannot be after the lease end date.",
                field="effective_date",
            )
        lease.status = LeaseStatus.TERMINATED
        lease.end_date = effective_date
        lease.terminated_on = effective_date
        lease.termination_reason = reason
        lease.closed_by = actor
        lease.save(
            update_fields=[
                "status",
                "end_date",
                "terminated_on",
                "termination_reason",
                "closed_by",
                "updated_at",
            ]
        )
        AuditService.record(
            actor=actor,
            action=LeaseAudit.TERMINATED,
            target=lease,
            property_id=lease.property_id,
            metadata={"effective_date": effective_date.isoformat(), "reason": reason},
        )
        _cancel_dependent_sublets(lease, effective_date)
        notices.lease_terminated(lease, effective_date=effective_date, actor=actor)
        return lease

    @staticmethod
    @transaction.atomic
    def cancel(*, actor, lease: Lease, reason: str = "") -> Lease:
        if not LeasePolicy.can_terminate(actor, lease):
            raise PermissionDenied("Only the property management can cancel leases.")
        lease = lock_active_lease(lease)
        if lease.start_date <= timezones.today(lease.unit.building.property):
            raise InvalidTransition(
                "A lease that has already taken effect must be terminated, not cancelled.",
                code="lease_already_started",
            )
        lease.status = LeaseStatus.CANCELLED
        lease.cancelled_at = timezone.now()
        lease.cancellation_reason = reason
        lease.closed_by = actor
        lease.save(
            update_fields=[
                "status",
                "cancelled_at",
                "cancellation_reason",
                "closed_by",
                "updated_at",
            ]
        )
        AuditService.record(
            actor=actor,
            action=LeaseAudit.CANCELLED,
            target=lease,
            property_id=lease.property_id,
        )
        _cancel_dependent_sublets(lease, lease.start_date)
        notices.lease_cancelled(lease, actor=actor)
        return lease

    @staticmethod
    def expire_due_in(*, actor, prop: Property) -> int:
        """Bulk action: terminate now every lease of the property past its end date."""
        HousekeepingPolicy.require(actor, prop)
        return LeaseService.expire_due(prop=prop)

    @staticmethod
    @transaction.atomic
    def end_if_unoccupied(*, actor, lease: Lease) -> Lease:
        """An active lease left without any occupant (their account was deleted)
        ends today, or is cancelled if it had not started yet."""
        if (
            lease.status != LeaseStatus.ACTIVE
            or lease.members.filter(left_at__isnull=True).exists()
        ):
            return lease
        today = timezones.today(lease.unit.building.property)
        if today < lease.start_date:
            return LeaseService.cancel(
                actor=actor, lease=lease, reason="No occupant left."
            )
        effective = min(today, lease.end_date) if lease.end_date else today
        return LeaseService.terminate(
            actor=actor, lease=lease, effective_date=effective
        )

    @staticmethod
    def expire_due(
        *, today: dt.date | None = None, prop: Property | None = None
    ) -> int:
        """Leases past their end date are terminated at term (all properties, or `prop`).

        "Past" is read in the time zone of each property (`today` forces one
        date for all, in tests). No time zone is more than a day ahead of UTC,
        so the leases ending before tomorrow in UTC are the only candidates.
        Run by `run_scheduled_jobs`, and on demand by `expire_due_in`.
        """
        horizon = today or timezone.now().date() + dt.timedelta(days=1)
        candidates = Lease.objects.filter(
            status=LeaseStatus.ACTIVE, end_date__lt=horizon
        ).select_related("unit__building__property")
        if prop is not None:
            candidates = candidates.filter(unit__building__property=prop)
        due = [
            lease
            for lease in candidates
            if lease.end_date < (today or timezones.today(lease.unit.building.property))
        ]
        count = 0
        for lease in due:
            LeaseService.terminate(
                actor=None,
                lease=lease,
                effective_date=lease.end_date,
                reason=LeaseTerminationReason.TERM_REACHED,
            )
            count += 1
        return count

    @staticmethod
    @transaction.atomic
    def delete(*, actor, lease: Lease) -> None:
        """Permanent removal of a lease and everything recorded under it:
        members, inspections, the short rentals declared under it, their files."""
        if not LeasePolicy.can_delete(actor, lease):
            raise PermissionDenied(
                "Only administrators and syndics can delete a lease."
            )
        AuditService.record(
            actor=actor,
            action=LeaseAudit.DELETED,
            target=lease,
            property_id=lease.property_id,
            metadata={
                "unit_id": lease.unit_id,
                "status": lease.status,
                "members": lease.members.count(),
            },
        )
        destroy(lease)
