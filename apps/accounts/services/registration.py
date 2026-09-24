"""What ties a new account to the residence.

An account is never registered floating in the air: the request that creates
it says what ties it to the residence, and the kind of tie is decided by the
role.

- a `standard` account is registered as the owner of at least one unit, as the
  tenant of one, or both (`ownerships`, `tenancy`): those are the only ways a
  standard account exists anywhere;
- every other role is registered with the place where that role is exercised,
  which the author selects (see `assignments`).

The ties are created in the transaction that creates the account, by the
services that own them (`OwnershipService`, `LeaseService`), so the account
never exists for a moment without its place.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from apps.accounts.enums import StructuralRole
from apps.common.exceptions import InvalidInput
from apps.leasing.services import LeaseService
from apps.properties.services import Acquirer, OwnershipService, UnitService


@dataclass(frozen=True)
class OwnedUnit:
    """A unit a new standard account owns, from the day it is registered."""

    unit_id: int
    share: Decimal | None = None


@dataclass(frozen=True)
class RentedUnit:
    """The unit a new standard account rents.

    The account joins the lease running on the unit; when the unit has none —
    the ordinary case for a first tenant — the lease opens with the dates given
    here (today by default) and the account as its signatory.
    """

    unit_id: int
    is_signatory: bool = False
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    contract_reference: str | None = None


def check_ties(role: str, *, ownerships, tenancy) -> None:
    """A standard account is registered with its units, the other roles without.

    A standard account holds no role anywhere: it exists in the residence only
    as an owner or as a tenant, so one of the two is required. Any other role
    is placed by its assignment, and naming units there would record two
    different things at once.
    """
    if role == StructuralRole.STANDARD:
        if not ownerships and tenancy is None:
            raise InvalidInput(
                "A standard account is registered as the owner of at least one unit, "
                "as the tenant of one, or both.",
                field="ownerships",
                code="ownership_or_tenancy_required",
            )
    elif ownerships or tenancy is not None:
        raise InvalidInput(
            f"A {role} account is registered with the place where its role is exercised, "
            "not with units.",
            field="ownerships",
            code="role_takes_no_unit",
        )


def register_ownerships(*, actor, user, ownerships) -> None:
    """Record the new account as an owner, unit by unit, from today.

    A unit still held by its promoter changes hands (a first sale); a unit that
    already has real owners gains a co-owner. Both operations belong to
    `OwnershipService`, which checks that the author manages the property and
    journals the change.
    """
    today = timezone.localdate()
    for owned in ownerships:
        unit = UnitService.get_visible(actor=actor, unit_id=owned.unit_id)
        if OwnershipService.active(unit).filter(is_promoter_default=True).exists():
            OwnershipService.transfer(
                actor=actor,
                unit=unit,
                acquirers=[Acquirer(user=user, share=owned.share)],
                effective_date=today,
            )
        else:
            OwnershipService.add_co_owner(
                actor=actor, unit=unit, user=user, share=owned.share, start_date=today
            )


def register_tenancy(*, actor, user, tenancy: RentedUnit) -> None:
    """Record the new account as the tenant of the unit it rents.

    Leases belong to `leasing`: this hands the unit and the account to
    `LeaseService.record_tenant`, which joins the lease running there or opens
    one when the unit has none.
    """
    LeaseService.record_tenant(
        actor=actor,
        unit=UnitService.get_visible(actor=actor, unit_id=tenancy.unit_id),
        user=user,
        start_date=tenancy.start_date,
        end_date=tenancy.end_date,
        contract_reference=tenancy.contract_reference,
        is_signatory=tenancy.is_signatory,
    )
