"""The rules every leasing service applies."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from apps.common.exceptions import InvalidInput, InvalidTransition
from apps.leasing.models import Lease, LeaseStatus

MEMBER_EXTRA_FIELDS = (
    "emergency_contact_name",
    "emergency_contact_phone",
    "emergency_contact_relation",
    "vehicles_info",
    "pets_info",
)


@dataclass
class MemberInput:
    user: object
    is_signatory: bool = False
    joined_at: dt.date | None = None
    extras: dict = field(default_factory=dict)

    def extra_fields(self) -> dict:
        """The contextual details of the member that the model knows."""
        return {
            name: value
            for name, value in self.extras.items()
            if name in MEMBER_EXTRA_FIELDS
        }


def check_member_dates(lease: Lease, joined_at: dt.date) -> None:
    if joined_at < lease.start_date:
        raise InvalidInput(
            "A member cannot join before the lease starts.", field="joined_at"
        )
    if lease.end_date and joined_at > lease.end_date:
        raise InvalidInput(
            "A member cannot join after the lease ends.", field="joined_at"
        )


def check_member_account(user) -> None:
    # Every occupant must own an active personal account (spec §1.6.2).
    if not user.is_active or user.is_technical_account:
        raise InvalidInput(
            "Lease members must have an active personal account.", field="user_id"
        )


def lock_active_lease(lease: Lease) -> Lease:
    """Lock the lease for a change; a closed lease is frozen."""
    lease = (
        Lease.objects.select_for_update(of=("self",))
        .select_related("unit__building__property")
        .get(pk=lease.pk)
    )
    if lease.status != LeaseStatus.ACTIVE:
        raise InvalidTransition("Only an active lease can be modified.")
    return lease
