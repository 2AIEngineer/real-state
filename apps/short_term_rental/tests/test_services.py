import datetime as dt

import pytest

from apps.common.exceptions import (
    BusinessRuleViolation,
    InvalidInput,
    InvalidTransition,
    PermissionDenied,
)
from apps.leasing.services import LeaseService
from apps.notifications.models import InboxNotification
from apps.short_term_rental.models import InitiatorCapacity, ShortTermRentalStatus
from apps.short_term_rental.services import (
    ShortTermRentalMemberInput,
    ShortTermRentalMemberService,
    ShortTermRentalService,
)
from tests import factories as f

pytestmark = pytest.mark.django_db
TODAY = dt.date.today()
MEMBERS = [ShortTermRentalMemberInput("Ana", "Diaz"), ShortTermRentalMemberInput("Leo", "Diaz")]


def declare(world, actor, unit=None, start=1, nights=3, **kwargs):
    checkin = TODAY + dt.timedelta(days=start)
    return ShortTermRentalService.declare(
        actor=actor,
        unit=unit or world.unit,
        checkin_date=checkin,
        checkout_date=checkin + dt.timedelta(days=nights),
        members=kwargs.pop("members", MEMBERS),
        **kwargs,
    )


class TestDeclaration:
    def test_tenant_sublet_inside_lease(self, world):
        rental = declare(world, world.tenant)
        assert rental.initiator_capacity == InitiatorCapacity.TENANT and rental.lease == world.lease
        assert rental.primary_member.first_name == "Ana"
        # The owner must learn that the unit is sublet.
        assert InboxNotification.objects.filter(
            notification_type="short_term_rental.created", user=world.owner
        ).exists()

    def test_tenant_sublet_must_stay_within_lease_bounds(self, world):
        LeaseService.update(
            actor=world.manager,
            lease=world.lease,
            changes={"end_date": TODAY + dt.timedelta(days=10)},
        )
        with pytest.raises(BusinessRuleViolation) as exc:
            declare(world, world.tenant, start=8, nights=5)
        assert exc.value.code == "outside_lease"

    def test_owner_cannot_sublet_a_leased_unit(self, world):
        with pytest.raises(BusinessRuleViolation) as exc:
            declare(world, world.owner)
        assert exc.value.code == "unit_leased"

    def test_owner_can_sublet_a_free_unit(self, world):
        f.make_owner(world.other_unit, world.owner, world.admin)
        assert (
            declare(world, world.owner, unit=world.other_unit).initiator_capacity
            == InitiatorCapacity.OWNER
        )

    def test_overlapping_stays_are_refused_but_turnover_day_is_fine(self, world):
        declare(world, world.tenant, start=1, nights=3)
        with pytest.raises(BusinessRuleViolation):
            declare(world, world.co_tenant, start=2, nights=3)
        declare(world, world.co_tenant, start=4, nights=2)

    def test_strangers_cannot_declare(self, world):
        with pytest.raises(PermissionDenied):
            declare(world, world.outsider)

    def test_past_stays_only_for_management(self, world):
        with pytest.raises(InvalidInput):
            declare(world, world.tenant, start=-5)
        declare(world, world.manager, start=-5)


class TestLifecycle:
    def test_lease_end_cancels_future_sublets(self, world):
        rental = declare(world, world.tenant, start=10)
        LeaseService.terminate(actor=world.manager, lease=world.lease, effective_date=TODAY)
        rental.refresh_from_db()
        assert rental.status == ShortTermRentalStatus.CANCELLED

    def test_security_checks_guests_in_and_out(self, world):
        rental = declare(world, world.tenant)
        rental = ShortTermRentalService.check_in(actor=world.security, rental=rental)
        with pytest.raises(InvalidTransition):
            ShortTermRentalService.cancel(actor=world.tenant, rental=rental)
        assert (
            ShortTermRentalService.complete(actor=world.security, rental=rental).status
            == ShortTermRentalStatus.COMPLETED
        )

    def test_guest_rules(self, world):
        rental = declare(
            world, world.tenant, members=[ShortTermRentalMemberInput("Solo", "Member")]
        )
        with pytest.raises(BusinessRuleViolation):
            ShortTermRentalMemberService.remove(actor=world.tenant, member=rental.members.get())
        ShortTermRentalMemberService.set_id_card(
            actor=world.tenant, member=rental.members.get(), upload=f.png()
        )
