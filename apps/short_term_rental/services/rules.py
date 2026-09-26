"""The rules that bound a short rental: under which right it is declared, and its dates."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from django.db.models import Q

from apps.accounts.services.authorization import AccessService
from apps.common.exceptions import (
    BusinessRuleViolation,
    InvalidInput,
    InvalidTransition,
    NotFound,
    PermissionDenied,
)
from apps.leasing.models import Lease, LeaseMember, LeaseStatus
from apps.properties.models import Unit
from apps.short_term_rental.models import (
    BLOCKING_SHORT_TERM_RENTAL_STATUSES,
    InitiatorCapacity,
    ShortTermRental,
)
from apps.short_term_rental.policies import ShortTermRentalPolicy


@dataclass(frozen=True)
class DeclarationRight:
    capacity: str
    lease: Lease | None = None
    member: LeaseMember | None = None


def resolve_right(actor, unit: Unit) -> DeclarationRight:
    """The capacity a rental is declared under, which sets its date rules."""
    if AccessService.manages_property(actor, unit.building.property):
        return DeclarationRight(InitiatorCapacity.MANAGEMENT)
    member = AccessService.active_lease_membership(actor, unit)
    if member:
        return DeclarationRight(
            InitiatorCapacity.TENANT, lease=member.lease, member=member
        )
    if AccessService.is_owner_of(actor, unit):
        return DeclarationRight(InitiatorCapacity.OWNER)
    raise PermissionDenied(
        "Only the unit's tenants, owners or management can declare a short rental."
    )


def check_period(
    right: DeclarationRight,
    unit: Unit,
    checkin: dt.date,
    checkout: dt.date,
    *,
    today: dt.date,
) -> None:
    if checkout <= checkin:
        raise InvalidInput("Check-out must be after check-in.", field="checkout_date")
    if right.capacity != InitiatorCapacity.MANAGEMENT and checkin < today:
        raise InvalidInput(
            "A rental cannot be declared in the past.", field="checkin_date"
        )
    if right.capacity == InitiatorCapacity.TENANT:
        lease = right.lease
        start_bound = max(lease.start_date, right.member.joined_at)
        if checkin < start_bound or (
            lease.end_date is not None and checkout > lease.end_date
        ):
            end = (
                lease.end_date.strftime("%d/%m/%Y") if lease.end_date else "open-ended"
            )
            raise BusinessRuleViolation(
                f"A sublet must rental within your lease ({start_bound:%d/%m/%Y} → {end}).",
                code="outside_lease",
            )
    elif right.capacity == InitiatorCapacity.OWNER:
        leased = Lease.objects.filter(
            unit=unit, status=LeaseStatus.ACTIVE, start_date__lt=checkout
        ).filter(Q(end_date__isnull=True) | Q(end_date__gte=checkin))
        if leased.exists():
            raise BusinessRuleViolation(
                "The unit is under an active lease for this period: only its tenants may sublet it.",
                code="unit_leased",
            )


def lock_rental(rental: ShortTermRental) -> ShortTermRental:
    """Lock the rental for a change, with what its rules need."""
    return (
        ShortTermRental.objects.select_for_update(of=("self",))
        .select_related("unit__building__property", "initiated_by", "lease")
        .get(pk=rental.pk)
    )


def require_editable(actor, rental: ShortTermRental) -> None:
    """Members can be changed by whoever may update the rental, until it is over."""
    if not ShortTermRentalPolicy.can_update(actor, rental):
        raise NotFound("Short rental not found.")
    if rental.status not in BLOCKING_SHORT_TERM_RENTAL_STATUSES:
        raise InvalidTransition(
            "Members can only be changed on upcoming or ongoing rentals."
        )
