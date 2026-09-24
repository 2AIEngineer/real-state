import datetime as dt
import re
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.enums import Gender, StructuralRole
from apps.accounts.models import ProviderProfile, UserBuilding
from apps.accounts.services.accounts import AccountService
from apps.accounts.services.authorization import AccessService
from apps.accounts.services.passwords import PasswordService
from apps.accounts.services.registration import OwnedUnit, RentedUnit
from apps.common.exceptions import BusinessRuleViolation, InvalidInput, NotFound, PermissionDenied
from apps.common.models import AuditLogEntry
from apps.leasing.models import Lease, LeaseMember, LeaseStatus
from apps.leasing.services import LeaseService
from apps.notifications.models import InboxNotification, OutboxChannel, OutboxMessage
from apps.properties.models import OwnershipStatus, UnitOwnership
from tests import factories as f

pytestmark = pytest.mark.django_db
User = get_user_model()


def invitation_link(user) -> tuple[str, str]:
    message = OutboxMessage.objects.filter(
        channel=OutboxChannel.EMAIL, payload__to=[user.email]
    ).latest("id")
    match = re.search(r"uid=([\w-]+)&token=([\w-]+)", message.payload["text"])
    return match.group(1), match.group(2)


class TestAccountCreation:
    def test_manager_creates_account_and_invitation_is_queued(self, world):
        user = AccountService.create_account(
            actor=world.manager,
            syndicat_id=world.syndicat.pk,
            property_id=world.prop.pk,
            email=" New.Tenant@Example.test ",
            first_name="New",
            last_name="Tenant",
            tenancy=RentedUnit(unit_id=world.unit.pk),
        )
        assert user.email == "new.tenant@example.test" and not user.has_usable_password()
        uid, token = invitation_link(user)
        PasswordService.set_password_with_token(
            uid=uid, token=token, password="A-very-long-passw0rd"
        )
        user.refresh_from_db()
        assert user.check_password("A-very-long-passw0rd")

    def test_token_cannot_be_reused(self, world):
        user = AccountService.create_account(
            actor=world.manager,
            syndicat_id=world.syndicat.pk,
            property_id=world.prop.pk,
            email="x@example.test",
            first_name="X",
            last_name="Y",
            tenancy=RentedUnit(unit_id=world.unit.pk),
        )
        uid, token = invitation_link(user)
        PasswordService.set_password_with_token(
            uid=uid, token=token, password="A-very-long-passw0rd"
        )
        with pytest.raises(InvalidInput):
            PasswordService.set_password_with_token(
                uid=uid, token=token, password="Another-l0ng-password"
            )

    def test_email_is_unique_case_insensitively(self, world):
        with pytest.raises(InvalidInput):
            AccountService.create_account(
                actor=world.manager,
                syndicat_id=world.syndicat.pk,
                property_id=world.prop.pk,
                email="TENANT@example.test",
                first_name="A",
                last_name="B",
                tenancy=RentedUnit(unit_id=world.unit.pk),
            )

    def test_owners_and_tenants_cannot_create_accounts(self, world):
        with pytest.raises(PermissionDenied):
            AccountService.create_account(
                actor=world.tenant,
                syndicat_id=world.syndicat.pk,
                property_id=world.prop.pk,
                email="z@example.test",
                first_name="Z",
                last_name="Z",
                tenancy=RentedUnit(unit_id=world.unit.pk),
            )

    def test_weak_password_is_rejected(self, world):
        user = AccountService.create_account(
            actor=world.manager,
            syndicat_id=world.syndicat.pk,
            property_id=world.prop.pk,
            email="w@example.test",
            first_name="W",
            last_name="W",
            tenancy=RentedUnit(unit_id=world.unit.pk),
        )
        uid, token = invitation_link(user)
        with pytest.raises(InvalidInput):
            PasswordService.set_password_with_token(uid=uid, token=token, password="12345")

    def test_reset_request_is_silent_for_unknown_addresses(self, world):
        PasswordService.request_reset(email="nobody@example.test")
        assert not OutboxMessage.objects.filter(payload__to=["nobody@example.test"]).exists()


class TestStandardAccountIsRegisteredWithItsUnits:
    """A standard account holds no role anywhere: it is registered as an owner,
    as a tenant, or both, in the request that creates it."""

    def _register(self, world, **kwargs):
        return AccountService.create_account(
            actor=world.manager,
            syndicat_id=world.syndicat.pk,
            property_id=world.prop.pk,
            first_name="N",
            last_name="N",
            **kwargs,
        )

    def test_neither_owner_nor_tenant_is_refused(self, world):
        with pytest.raises(InvalidInput) as exc:
            self._register(world, email="nowhere@example.test")
        assert exc.value.code == "ownership_or_tenancy_required"

    def test_owner_of_a_unit_still_held_by_the_promoter_buys_it(self, world):
        user = self._register(
            world, email="buyer@example.test", ownerships=[OwnedUnit(unit_id=world.other_unit.pk)]
        )
        active = UnitOwnership.objects.filter(unit=world.other_unit, status=OwnershipStatus.ACTIVE)
        assert [o.owner_id for o in active] == [user.pk]
        assert active.get().ownership_share == Decimal("100.00")
        assert AccessService.is_owner_of(user, world.other_unit)
        # The promoter's holding is closed, not erased.
        assert UnitOwnership.objects.filter(
            unit=world.other_unit, is_promoter_default=True, status=OwnershipStatus.TERMINATED
        ).exists()

    def test_owner_of_a_unit_that_already_has_one_becomes_a_co_owner(self, world):
        unit = f.make_unit(world.building, world.admin, number="A909")
        f.make_owner(unit, world.owner, world.admin, share=Decimal("60"))
        user = self._register(
            world,
            email="coowner@example.test",
            ownerships=[OwnedUnit(unit_id=unit.pk, share=Decimal("40"))],
        )
        owners = UnitOwnership.objects.filter(unit=unit, status=OwnershipStatus.ACTIVE)
        assert {o.owner_id for o in owners} == {world.owner.pk, user.pk}
        assert owners.get(owner=user).ownership_share == Decimal("40.00")

    def test_a_unit_already_rented_is_joined_not_re_leased(self, world):
        user = self._register(
            world, email="newtenant@example.test", tenancy=RentedUnit(unit_id=world.unit.pk)
        )
        assert LeaseMember.objects.filter(
            lease=world.lease, user=user, left_at__isnull=True
        ).exists()
        assert AccessService.is_tenant_of(user, world.unit)

    def test_an_account_can_own_and_rent_at_once(self, world):
        user = self._register(
            world,
            email="both@example.test",
            ownerships=[OwnedUnit(unit_id=world.other_unit.pk)],
            tenancy=RentedUnit(unit_id=world.unit.pk),
        )
        assert AccessService.is_owner_of(user, world.other_unit) and AccessService.is_tenant_of(
            user, world.unit
        )

    def test_renting_a_unit_with_no_lease_yet_opens_the_lease(self, world):
        """The first tenant of a unit has no lease to join: it is opened for them."""
        user = self._register(
            world,
            email="firsttenant@example.test",
            tenancy=RentedUnit(unit_id=world.other_unit.pk, contract_reference="BAIL-2026-42"),
        )
        lease = Lease.objects.get(unit=world.other_unit, status=LeaseStatus.ACTIVE)
        member = lease.members.get(user=user)
        assert member.is_signatory and lease.contract_reference == "BAIL-2026-42"
        assert lease.start_date == dt.date.today() and AccessService.is_tenant_of(
            user, world.other_unit
        )

    def test_the_lease_dates_given_are_the_ones_recorded(self, world):
        start, end = (
            dt.date.today() - dt.timedelta(days=10),
            dt.date.today() + dt.timedelta(days=355),
        )
        self._register(
            world,
            email="dated@example.test",
            tenancy=RentedUnit(unit_id=world.other_unit.pk, start_date=start, end_date=end),
        )
        lease = Lease.objects.get(unit=world.other_unit, status=LeaseStatus.ACTIVE)
        assert (lease.start_date, lease.end_date) == (start, end)

    def test_a_unit_the_author_does_not_manage_is_not_found(self, world):
        elsewhere = f.make_unit(f.make_building(f.make_property()), world.admin)
        with pytest.raises(NotFound):
            self._register(
                world, email="far@example.test", ownerships=[OwnedUnit(unit_id=elsewhere.pk)]
            )

    def test_a_staff_account_is_placed_by_its_assignment_not_by_units(self, world):
        with pytest.raises(InvalidInput) as exc:
            self._register(
                world,
                email="staff@example.test",
                role=StructuralRole.MAINTENANCE,
                ownerships=[OwnedUnit(unit_id=world.other_unit.pk)],
            )
        assert exc.value.code == "role_takes_no_unit"


class TestAnAccountIsBornWithItsRole:
    """Creating an account is not changing its role: it starts with the role it
    is given, so nothing that belongs to a role *change* happens."""

    def test_the_role_is_set_at_creation_without_a_role_change(self, world):
        guard = AccountService.create_account(
            actor=world.manager,
            syndicat_id=world.syndicat.pk,
            property_id=world.prop.pk,
            email="born@example.test",
            first_name="B",
            last_name="B",
            role=StructuralRole.SECURITY,
            building_ids=(world.building.pk,),
        )
        assert guard.role == StructuralRole.SECURITY
        assert UserBuilding.objects.filter(user=guard, is_active=True).exists()
        assert not AuditLogEntry.objects.filter(action="role.changed", object_id=guard.pk).exists()
        assert not InboxNotification.objects.filter(
            user=guard, notification_type="account.role_changed"
        ).exists()
        created = AuditLogEntry.objects.get(action="account.created", object_id=guard.pk)
        assert created.metadata["role"] == StructuralRole.SECURITY

    def test_a_provider_account_is_born_with_its_profile(self, world):
        provider = AccountService.create_account(
            actor=world.admin,
            syndicat_id=world.syndicat.pk,
            property_id=world.prop.pk,
            email="provider@example.test",
            first_name="P",
            last_name="P",
            role=StructuralRole.PROVIDER,
        )
        assert ProviderProfile.objects.filter(user=provider).exists()

    def test_a_role_the_author_does_not_hand_out_is_refused(self, world):
        with pytest.raises(PermissionDenied):
            AccountService.create_account(
                actor=world.manager,
                syndicat_id=world.syndicat.pk,
                property_id=world.prop.pk,
                email="boss@example.test",
                first_name="A",
                last_name="A",
                role=StructuralRole.SYNDIC,
            )
        assert not User.objects.filter(email="boss@example.test").exists()


class TestFieldStaffIsRegisteredWithItsBuildings:
    def test_security_without_buildings_is_refused(self, world):
        with pytest.raises(InvalidInput) as exc:
            AccountService.create_account(
                actor=world.manager,
                syndicat_id=world.syndicat.pk,
                property_id=world.prop.pk,
                email="guard@example.test",
                first_name="G",
                last_name="G",
                role=StructuralRole.SECURITY,
            )
        assert exc.value.code == "assignment_required"
        assert not User.objects.filter(email="guard@example.test").exists()

    def test_cleaning_is_assigned_to_the_buildings_given(self, world):
        user = AccountService.create_account(
            actor=world.manager,
            syndicat_id=world.syndicat.pk,
            property_id=world.prop.pk,
            email="clean@example.test",
            first_name="C",
            last_name="C",
            role=StructuralRole.CLEANING,
            building_ids=(world.building.pk, world.other_building.pk),
        )
        assert set(
            UserBuilding.objects.filter(user=user, is_active=True).values_list(
                "building_id", flat=True
            )
        ) == {world.building.pk, world.other_building.pk}


class TestGender:
    def test_gender_is_undisclosed_unless_given(self, world):
        user = AccountService.create_account(
            actor=world.manager,
            syndicat_id=world.syndicat.pk,
            property_id=world.prop.pk,
            email="g1@example.test",
            first_name="G",
            last_name="One",
            tenancy=RentedUnit(unit_id=world.unit.pk),
        )
        assert user.gender == Gender.UNDISCLOSED
        user = AccountService.create_account(
            actor=world.manager,
            syndicat_id=world.syndicat.pk,
            property_id=world.prop.pk,
            email="g2@example.test",
            first_name="G",
            last_name="Two",
            gender=Gender.FEMALE,
            tenancy=RentedUnit(unit_id=world.unit.pk),
        )
        assert user.gender == Gender.FEMALE

    def test_users_edit_their_own_gender(self, world):
        user = AccountService.update_profile(
            actor=world.tenant, user=world.tenant, changes={"gender": Gender.MALE}
        )
        assert user.gender == Gender.MALE


class TestCriticalChanges:
    def test_email_change_warns_both_addresses(self, world):
        AccountService.change_email(
            actor=world.tenant,
            user=world.tenant,
            new_email="moved@example.test",
            current_password="Str0ng-Passw0rd!",
        )
        recipients = [
            m.payload["to"] for m in OutboxMessage.objects.filter(channel=OutboxChannel.EMAIL)
        ]
        assert ["moved@example.test"] in recipients and ["tenant@example.test"] in recipients

    def test_self_email_change_requires_password(self, world):
        with pytest.raises(PermissionDenied):
            AccountService.change_email(
                actor=world.tenant,
                user=world.tenant,
                new_email="x@example.test",
                current_password="wrong",
            )

    def test_cannot_deactivate_an_active_lease_member(self, world):
        with pytest.raises(BusinessRuleViolation) as exc:
            AccountService.deactivate(actor=world.admin, user=world.tenant)
        assert exc.value.code == "active_lease_member"

    def test_deactivation_revokes_roles_and_blocks_access(self, world):
        from apps.accounts.services.authorization import AccessService

        AccountService.deactivate(actor=world.admin, user=world.manager)
        world.manager.refresh_from_db()
        assert not world.manager.is_active and world.manager.deactivated_at
        assert not AccessService.manages_property(world.manager, world.prop)

    def test_only_admins_deactivate(self, world):
        with pytest.raises(PermissionDenied):
            AccountService.deactivate(actor=world.manager, user=world.outsider)

    def test_closure_erases_personal_data_but_keeps_history(self, world):
        LeaseService.terminate(
            actor=world.manager, lease=world.lease, effective_date=dt.date.today()
        )
        AccountService.close(actor=world.admin, user=world.co_tenant)
        world.co_tenant.refresh_from_db()
        assert world.co_tenant.email.endswith("@erased.invalid") and not world.co_tenant.is_active
        assert world.lease.members.filter(user=world.co_tenant).exists()


class TestVisibility:
    def test_manager_sees_the_people_of_their_property_only(self, world):
        visible = set(AccountService.search(actor=world.manager).values_list("pk", flat=True))
        assert {world.tenant.pk, world.owner.pk, world.security.pk} <= visible
        assert world.outsider.pk not in visible

    def test_exact_email_lookup_finds_platform_accounts(self, world):
        found = AccountService.search(actor=world.manager, query="outsider@example.test")
        assert list(found) == [world.outsider]


def test_technical_accounts_cannot_log_in(world):
    rep = world.prop.promoter.representative_user
    assert rep.is_technical_account and not rep.has_usable_password()
