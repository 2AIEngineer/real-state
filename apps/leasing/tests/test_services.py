import datetime as dt

import pytest

from apps.common.exceptions import (
    BusinessRuleViolation,
    InvalidInput,
    InvalidTransition,
    PermissionDenied,
)
from apps.leasing.models import CheckPhase, ComponentCondition, LeaseStatus
from apps.leasing.services import (
    LeaseComponentStateService,
    LeaseMemberService,
    LeaseService,
    MemberInput,
)
from tests import factories as f

pytestmark = pytest.mark.django_db
TODAY = dt.date.today()


class TestLeaseCreation:
    def test_active_lease_requires_a_member(self, world):
        with pytest.raises(InvalidInput):
            LeaseService.create(
                actor=world.manager, unit=world.other_unit, start_date=TODAY, members=[]
            )

    def test_a_signatory_is_required(self, world):
        with pytest.raises(InvalidInput):
            LeaseService.create(
                actor=world.manager,
                unit=world.other_unit,
                start_date=TODAY,
                members=[MemberInput(f.make_user())],
            )

    def test_overlapping_active_leases_are_refused_by_the_database(self, world):
        with pytest.raises(BusinessRuleViolation) as exc:
            f.make_lease(
                world.unit, [f.make_user()], world.manager, start=TODAY + dt.timedelta(days=10)
            )
        assert exc.value.code == "lease_overlap"

    def test_consecutive_leases_are_allowed(self, world):
        first = f.make_lease(
            world.other_unit,
            [f.make_user()],
            world.manager,
            start=TODAY,
            end=TODAY + dt.timedelta(days=30),
        )
        second = f.make_lease(
            world.other_unit, [f.make_user()], world.manager, start=TODAY + dt.timedelta(days=31)
        )
        assert first.status == second.status == LeaseStatus.ACTIVE

    def test_technical_account_cannot_be_member(self, world):
        with pytest.raises(InvalidInput):
            f.make_lease(world.other_unit, [world.prop.promoter.representative_user], world.manager)

    def test_owner_cannot_create_lease(self, world):
        with pytest.raises(PermissionDenied):
            f.make_lease(world.other_unit, [f.make_user()], world.owner)


class TestLeaseMembers:
    def test_departure_keeps_the_row(self, world):
        member = world.lease.members.get(user=world.co_tenant)
        LeaseMemberService.record_departure(actor=world.manager, member=member, left_at=TODAY)
        member.refresh_from_db()
        assert member.left_at == TODAY
        assert world.lease.members.count() == 2

    def test_last_active_member_cannot_leave(self, world):
        LeaseMemberService.record_departure(
            actor=world.manager, member=world.lease.members.get(user=world.co_tenant), left_at=TODAY
        )
        with pytest.raises(BusinessRuleViolation) as exc:
            LeaseMemberService.record_departure(
                actor=world.manager,
                member=world.lease.members.get(user=world.tenant),
                left_at=TODAY,
            )
        assert exc.value.code == "last_active_member"

    def test_tenant_edits_own_extras_but_not_signatory_flag(self, world):
        member = world.lease.members.get(user=world.tenant)
        LeaseMemberService.update(
            actor=world.tenant, member=member, changes={"emergency_contact_name": "Mom"}
        )
        assert member.emergency_contact_name == "Mom"
        with pytest.raises(PermissionDenied):
            LeaseMemberService.update(
                actor=world.tenant, member=member, changes={"is_signatory": False}
            )

    def test_a_user_cannot_be_recorded_twice_on_a_lease(self, world):
        with pytest.raises(InvalidInput) as exc:
            LeaseMemberService.add(
                actor=world.manager, lease=world.lease, member=MemberInput(world.tenant)
            )
        assert exc.value.code == "already_member"

    def test_member_cannot_join_before_start(self, world):
        with pytest.raises(InvalidInput):
            LeaseMemberService.add(
                actor=world.manager,
                lease=world.lease,
                member=MemberInput(
                    f.make_user(), joined_at=world.lease.start_date - dt.timedelta(days=1)
                ),
            )


class TestLeaseTransitions:
    def test_termination_freezes_members(self, world):
        LeaseService.terminate(actor=world.manager, lease=world.lease, effective_date=TODAY)
        world.lease.refresh_from_db()
        assert world.lease.status == LeaseStatus.TERMINATED and world.lease.end_date == TODAY
        assert world.lease.members.filter(left_at__isnull=True).count() == 2

    def test_terminated_tenant_loses_derived_rights(self, world):
        from apps.accounts.services.authorization import AccessService

        LeaseService.terminate(actor=world.manager, lease=world.lease, effective_date=TODAY)
        assert not AccessService.is_tenant_of(world.tenant, world.unit)

    def test_started_lease_cannot_be_cancelled(self, world):
        with pytest.raises(InvalidTransition):
            LeaseService.cancel(actor=world.manager, lease=world.lease)

    def test_future_lease_can_be_cancelled(self, world):
        lease = f.make_lease(
            world.other_unit, [f.make_user()], world.manager, start=TODAY + dt.timedelta(days=5)
        )
        lease = LeaseService.cancel(actor=world.manager, lease=lease, reason="Tenant withdrew")
        assert lease.status == LeaseStatus.CANCELLED

    def test_closed_lease_is_immutable(self, world):
        LeaseService.terminate(actor=world.manager, lease=world.lease, effective_date=TODAY)
        with pytest.raises(InvalidTransition):
            LeaseService.update(actor=world.manager, lease=world.lease, changes={"notes": "x"})

    def test_expiry_job(self, world):
        lease = f.make_lease(
            world.other_unit,
            [f.make_user()],
            world.manager,
            start=TODAY - dt.timedelta(days=60),
            end=TODAY - dt.timedelta(days=1),
        )
        assert LeaseService.expire_due(today=TODAY) == 1
        lease.refresh_from_db()
        assert lease.status == LeaseStatus.TERMINATED and lease.termination_reason == "TERM_REACHED"


class TestInspections:
    def test_move_out_cannot_precede_move_in(self, world):
        LeaseComponentStateService.record(
            actor=world.manager,
            lease=world.lease,
            name="Oven",
            state=ComponentCondition.GOOD,
            on_check=CheckPhase.IN,
            on_check_date=TODAY,
        )
        with pytest.raises(InvalidInput):
            LeaseComponentStateService.record(
                actor=world.manager,
                lease=world.lease,
                name="oven",
                state=ComponentCondition.BAD,
                on_check=CheckPhase.OUT,
                on_check_date=TODAY - dt.timedelta(days=1),
            )

    def test_inspection_with_photos(self, world):
        component = LeaseComponentStateService.record(
            actor=world.manager,
            lease=world.lease,
            name="Door",
            state=ComponentCondition.GOOD,
            on_check=CheckPhase.IN,
            on_check_date=TODAY,
            files=[f.png(), f.pdf()],
        )
        from apps.common.files.rules import EntityType
        from apps.common.files.service import AttachmentService

        assert AttachmentService.count(EntityType.LEASE_COMPONENT_STATE, component.pk) == 2

    def test_move_in_refused_on_terminated_lease(self, world):
        LeaseService.terminate(actor=world.manager, lease=world.lease, effective_date=TODAY)
        with pytest.raises(InvalidTransition):
            LeaseComponentStateService.record(
                actor=world.manager,
                lease=world.lease,
                name="Sink",
                state=ComponentCondition.GOOD,
                on_check=CheckPhase.IN,
                on_check_date=TODAY,
            )
