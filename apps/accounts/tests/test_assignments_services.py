import pytest

from apps.accounts.enums import PropertyRole, StructuralRole
from apps.accounts.models import UserBuilding, UserProperty, UserSyndicat
from apps.accounts.services.accounts import AccountService
from apps.accounts.services.assignments import (
    BuildingAssignmentService,
    PropertyAssignmentService,
    SyndicatAssignmentService,
    assign_according_to_role,
)
from apps.accounts.services.authorization import AccessService
from apps.accounts.services.directory import UserDirectory
from apps.common.exceptions import BusinessRuleViolation, InvalidInput, PermissionDenied
from apps.common.models import AuditLogEntry
from apps.properties.services import BuildingService, PropertyService, SyndicatService
from tests import factories as f

pytestmark = pytest.mark.django_db


def create(actor, role, *, syndicat, prop=None, building_ids=(), email="new@x.test"):
    """Create an account with `syndicat` / `prop` selected by the author."""
    return AccountService.create_account(
        actor=actor,
        email=email,
        first_name="N",
        last_name="N",
        role=role,
        syndicat_id=syndicat.pk,
        property_id=prop.pk if prop else None,
        building_ids=building_ids,
    )


class TestWhoWorksWhere:
    def test_syndic_of_a_syndicat_manages_all_its_properties(self, world):
        assert AccessService.is_syndic_of(world.syndic, world.syndicat)
        assert AccessService.manages_property(world.syndic, world.prop)
        assert AccessService.manages_property(
            world.syndic, f.make_property(syndicat=world.syndicat)
        )  # future ones too
        assert not AccessService.manages_property(world.syndic, f.make_property())

    def test_manager_manages_their_properties_only(self, world):
        assert AccessService.is_manager_of(world.manager, world.prop)
        assert AccessService.manages_property(world.manager, world.prop)
        assert not AccessService.manages_property(
            world.manager, f.make_property(syndicat=world.syndicat)
        )
        assert not AccessService.manages_syndicat(world.manager, world.syndicat)

    def test_security_works_in_their_building_only(self, world):
        assert AccessService.is_security_of(world.security, world.building)
        assert AccessService.is_staff_of_building(world.security, world.building)
        assert not AccessService.is_staff_of_building(world.security, world.other_building)
        assert AccessService.is_staff_of_property(
            world.security, world.prop
        )  # through their building
        assert not AccessService.manages_property(world.security, world.prop)

    def test_maintenance_works_in_the_property_without_managing_it(self, world):
        assert AccessService.is_maintenance_of(world.maintenance, world.prop)
        assert AccessService.is_staff_of_building(world.maintenance, world.other_building)
        assert not AccessService.manages_property(world.maintenance, world.prop)

    def test_management_does_not_work_on_site(self, world):
        """Running a property and being on the ground there are two different links."""
        for boss in (world.admin, world.syndic, world.manager):
            assert AccessService.manages_property(boss, world.prop)
            assert not AccessService.works_on_site_in_property(boss, world.prop)
            assert not AccessService.works_on_site_in_building(boss, world.building)
        for agent in (world.maintenance, world.security):
            assert AccessService.works_on_site_in_property(agent, world.prop)
            assert not AccessService.manages_property(agent, world.prop)

    def test_admin_manages_everything_without_assignment(self, world):
        assert AccessService.manages_property(world.admin, f.make_property())

    def test_a_role_question_is_false_for_another_role(self, world):
        assert not AccessService.is_manager_of(
            world.maintenance, world.prop
        )  # same table, other role
        assert not AccessService.is_cleaning_of(world.security, world.building)

    def test_deactivated_user_has_no_rights(self, world):
        world.manager.is_active = False
        assert not AccessService.manages_property(world.manager, world.prop)


class TestOwnersAndTenants:
    def test_owner_and_tenants_are_derived(self, world):
        assert AccessService.is_owner_of(
            world.owner, world.unit
        ) and not AccessService.is_tenant_of(world.owner, world.unit)
        assert AccessService.is_tenant_of(
            world.tenant, world.unit
        ) and not AccessService.is_owner_of(world.tenant, world.unit)
        assert not AccessService.is_owner_or_tenant_of(world.outsider, world.unit)

    def test_owners_and_tenants_keep_the_standard_role(self, world):
        assert world.owner.role == world.tenant.role == StructuralRole.STANDARD

    def test_building_security_is_linked_to_the_property(self, world):
        assert AccessService.is_staff_or_resident_of_property(world.security, world.prop)

    def test_a_standard_owner_reaches_their_property_without_working_there(self, world):
        """Owners and tenants sign up with the standard role: their unit is their only link."""
        for resident in (world.owner, world.tenant):
            assert AccessService.is_resident_of_property(resident, world.prop)
            assert AccessService.is_staff_or_resident_of_property(resident, world.prop)
            assert world.prop.pk in AccessService.accessible_property_ids(resident)
            assert not AccessService.is_staff_of_property(resident, world.prop)
            assert AccessService.staff_property_ids(resident) == set()
        assert AccessService.resident_property_ids(world.manager) == set()


class TestDirectory:
    def test_property_roles_mix_staff_roles_and_derived_ones(self, world):
        matched = UserDirectory.users_by_property_role(
            world.prop, [PropertyRole.TENANT, PropertyRole.SECURITY]
        )
        assert set(matched) == {world.tenant.pk, world.co_tenant.pk, world.security.pk}

    def test_technical_accounts_are_never_recipients(self, world):
        matched = UserDirectory.users_by_property_role(world.prop, [PropertyRole.OWNER])
        assert (
            world.prop.promoter.representative_user_id not in matched and world.owner.pk in matched
        )

    def test_management_resolution_follows_assignments(self, world):
        assert set(UserDirectory.management(world.prop)) == {world.manager, world.syndic}
        assert set(UserDirectory.management(f.make_property())) == set()


class TestSyndicAssignments:
    def test_lands_on_the_selected_syndicat(self, world):
        syndic = create(world.syndic, "syndic", syndicat=world.syndicat)
        assert list(
            UserSyndicat.objects.filter(user=syndic, is_active=True).values_list(
                "syndicat_id", flat=True
            )
        ) == [world.syndicat.pk]
        later = f.make_property(syndicat=world.syndicat)
        assert AccessService.manages_property(
            syndic, later
        )  # a syndicat covers its future properties

    def test_a_second_syndicat_comes_from_selecting_it(self, world):
        other = f.make_syndicat()
        syndic = create(world.admin, "syndic", syndicat=world.syndicat)
        assign_according_to_role(actor=world.admin, user=syndic, syndicat_id=other.pk)
        assert UserSyndicat.objects.filter(user=syndic, is_active=True).count() == 2

    def test_never_assigned_to_properties(self, world):
        syndic = create(world.admin, "syndic", syndicat=world.syndicat)
        with pytest.raises(InvalidInput):
            PropertyAssignmentService.assign(
                actor=world.admin, user=syndic, property_ids=(world.prop.pk,)
            )


class TestManagerAssignments:
    def test_lands_on_the_selected_property_only(self, world):
        second = f.make_property(syndicat=world.syndicat)
        manager = create(world.syndic, "manager", syndicat=world.syndicat, prop=world.prop)
        assigned = set(
            UserProperty.objects.filter(user=manager, is_active=True).values_list(
                "property_id", flat=True
            )
        )
        assert assigned == {world.prop.pk}
        assert not AccessService.manages_property(
            manager, second
        )  # another property is a second grant
        assert not UserSyndicat.objects.filter(user=manager).exists()

    def test_a_property_of_another_syndicat_comes_from_selecting_that_syndicat(self, world):
        foreign = f.make_property()
        manager = create(world.admin, "manager", syndicat=world.syndicat, prop=world.prop)
        assign_according_to_role(
            actor=world.admin, user=manager, syndicat_id=foreign.syndicat_id, property_id=foreign.pk
        )
        assigned = set(
            UserProperty.objects.filter(user=manager, is_active=True).values_list(
                "property_id", flat=True
            )
        )
        assert assigned == {world.prop.pk, foreign.pk}

    def test_new_property_goes_to_the_managers_of_its_syndicat(self, world):
        elsewhere = f.make_user()
        f.assign_role(elsewhere, StructuralRole.MANAGER, f.make_property())
        prop = PropertyService.create(
            actor=world.admin,
            syndicat=world.syndicat,
            promoter=f.make_promoter(),
            data={"name": "Les Pins"},
        )
        assert AccessService.manages_property(world.manager, prop)
        assert not AccessService.manages_property(elsewhere, prop)
        assert AuditLogEntry.objects.filter(
            action="assignment.granted",
            metadata__reason="new_property_in_managed_syndicat",
            metadata__user_id=world.manager.pk,
        ).exists()

    def test_refused_without_a_selected_property(self, world):
        with pytest.raises(InvalidInput) as exc:
            create(world.admin, "manager", syndicat=world.syndicat, email="m@x.test")
        assert exc.value.code == "selection_required"
        assert not AccountService.search(
            actor=world.admin, query="m@x.test"
        ).exists()  # rolled back

    def test_never_assigned_to_syndicats_or_buildings(self, world):
        with pytest.raises(InvalidInput):
            SyndicatAssignmentService.assign(
                actor=world.admin, user=world.manager, syndicat_ids=(world.syndicat.pk,)
            )
        with pytest.raises(InvalidInput):
            BuildingAssignmentService.assign(
                actor=world.admin, user=world.manager, building_ids=(world.building.pk,)
            )


class TestFieldRoleDefaults:
    def test_maintenance_takes_the_selected_property(self, world):
        tech = create(world.manager, "maintenance", syndicat=world.syndicat, prop=world.prop)
        assert list(
            UserProperty.objects.filter(user=tech).values_list("property_id", flat=True)
        ) == [world.prop.pk]

    def test_maintenance_needs_an_open_property(self, world):
        with pytest.raises(InvalidInput) as exc:
            create(world.manager, "maintenance", syndicat=world.syndicat)
        assert exc.value.code == "selection_required"

    @pytest.mark.parametrize("role", ["security", "cleaning"])
    def test_building_roles_must_be_given_their_buildings(self, world, role):
        with pytest.raises(InvalidInput) as exc:
            create(world.manager, role, syndicat=world.syndicat, prop=world.prop)
        assert exc.value.code == "assignment_required"

    @pytest.mark.parametrize("role", ["security", "cleaning"])
    def test_buildings_must_belong_to_the_open_property(self, world, role):
        elsewhere = f.make_building(f.make_property())
        with pytest.raises(InvalidInput) as exc:
            create(
                world.manager,
                role,
                syndicat=world.syndicat,
                prop=world.prop,
                building_ids=(elsewhere.pk,),
            )
        assert exc.value.code == "building_outside_property"

    def test_the_selected_property_must_belong_to_the_selected_syndicat(self, world):
        with pytest.raises(InvalidInput) as exc:
            create(world.manager, "maintenance", syndicat=world.syndicat, prop=f.make_property())
        assert exc.value.code == "property_outside_syndicat"


class TestWhoCreatesWhichRole:
    @pytest.mark.parametrize("role", ["admin", "provider"])
    def test_admin_and_provider_are_created_by_admins_only(self, world, role):
        with pytest.raises(PermissionDenied):
            create(world.syndic, role, syndicat=world.syndicat)
        assert create(world.admin, role, syndicat=world.syndicat).role == role

    def test_syndic_creates_syndics_and_managers(self, world):
        assert (
            create(world.syndic, "syndic", syndicat=world.syndicat, email="s@x.test").role
            == "syndic"
        )
        assert (
            create(
                world.syndic, "manager", syndicat=world.syndicat, prop=world.prop, email="m@x.test"
            ).role
            == "manager"
        )

    @pytest.mark.parametrize("role", ["syndic", "manager"])
    def test_manager_cannot_create_syndics_or_managers(self, world, role):
        with pytest.raises(PermissionDenied):
            create(world.manager, role, syndicat=world.syndicat)


class TestFieldRoleAssignments:
    def test_security_buildings_must_share_one_property(self, world):
        other_prop_building = f.make_building(f.make_property())
        BuildingAssignmentService.assign(
            actor=world.admin, user=world.security, building_ids=(world.other_building.pk,)
        )
        with pytest.raises(BusinessRuleViolation) as exc:
            BuildingAssignmentService.assign(
                actor=world.admin, user=world.security, building_ids=(other_prop_building.pk,)
            )
        assert exc.value.code == "security_single_property"

    def test_security_coverage_is_never_materialised_above_buildings(self, world):
        assert not UserProperty.objects.filter(user=world.security).exists()
        assert not UserSyndicat.objects.filter(user=world.security).exists()

    def test_cleaning_buildings_are_free(self, world):
        cleaner = f.make_user()
        f.assign_role(cleaner, StructuralRole.CLEANING)
        far = f.make_building(f.make_property())
        BuildingAssignmentService.assign(
            actor=world.admin, user=cleaner, building_ids=(world.building.pk, far.pk)
        )
        assert UserBuilding.objects.filter(user=cleaner, is_active=True).count() == 2

    def test_maintenance_takes_properties_across_syndicats(self, world):
        far = f.make_property()
        PropertyAssignmentService.assign(
            actor=world.admin, user=world.maintenance, property_ids=(far.pk,)
        )
        assert AccessService.is_maintenance_of(world.maintenance, far)

    @pytest.mark.parametrize(
        "role", [StructuralRole.ADMIN, StructuralRole.STANDARD, StructuralRole.PROVIDER]
    )
    def test_roles_without_location_refuse_any_assignment(self, world, role):
        user = f.make_user()
        f.assign_role(user, role)
        with pytest.raises(BusinessRuleViolation) as exc:
            assign_according_to_role(
                actor=world.admin,
                user=user,
                syndicat_id=world.syndicat.pk,
                property_id=world.prop.pk,
            )
        assert exc.value.code == "role_takes_no_assignment"

    def test_duplicate_assignment(self, world):
        with pytest.raises(BusinessRuleViolation) as exc:
            BuildingAssignmentService.assign(
                actor=world.admin, user=world.security, building_ids=(world.building.pk,)
            )
        assert exc.value.code == "already_assigned"


class TestWhoManagesAssignments:
    def test_manager_creates_field_staff_in_their_property(self, world):
        guard = AccountService.create_account(
            actor=world.manager,
            email="guard@x.test",
            first_name="G",
            last_name="G",
            role="security",
            syndicat_id=world.syndicat.pk,
            property_id=world.prop.pk,
            building_ids=(world.other_building.pk,),
        )
        assert guard.role == StructuralRole.SECURITY
        assert UserBuilding.objects.filter(user=guard, building=world.other_building).exists()

    def test_manager_cannot_change_the_role_of_an_unrelated_account(self, world):
        from apps.common.exceptions import NotFound

        with pytest.raises(NotFound):
            AccountService.change_role(
                actor=world.manager,
                user=world.outsider,
                role="security",
                syndicat_id=world.syndicat.pk,
                property_id=world.prop.pk,
                building_ids=(world.building.pk,),
            )

    def test_manager_cannot_touch_a_syndic_assignment(self, world):
        with pytest.raises(PermissionDenied):
            SyndicatAssignmentService.revoke(
                actor=world.manager, assignment_id=UserSyndicat.objects.get(user=world.syndic).pk
            )

    def test_syndic_manages_managers_within_coverage(self, world):
        row = UserProperty.objects.get(user=world.manager)
        PropertyAssignmentService.revoke(actor=world.syndic, assignment_id=row.pk)
        row.refresh_from_db()
        assert not row.is_active and row.revoked_by == world.syndic and row.revoked_at

    def test_field_staff_cannot_assign_anyone_outside_their_coverage(self, world):
        with pytest.raises(PermissionDenied):
            PropertyAssignmentService.assign(
                actor=world.manager, user=world.maintenance, property_ids=(f.make_property().pk,)
            )

    def test_nobody_manages_their_own_assignments(self, world):
        with pytest.raises(PermissionDenied):
            SyndicatAssignmentService.assign(
                actor=world.syndic, user=world.syndic, syndicat_ids=(f.make_syndicat().pk,)
            )

    def test_revocation_is_audited(self, world):
        BuildingAssignmentService.revoke(
            actor=world.manager, assignment_id=UserBuilding.objects.get(user=world.security).pk
        )
        entry = AuditLogEntry.objects.get(action="assignment.revoked")
        assert entry.actor == world.manager and entry.metadata["reason"] == "revoked"


class TestRoleChange:
    def test_refused_while_assignments_are_active(self, world):
        with pytest.raises(BusinessRuleViolation) as exc:
            AccountService.change_role(
                actor=world.admin, user=world.manager, role="syndic", syndicat_id=world.syndicat.pk
            )
        assert (
            exc.value.code == "active_assignments"
            and exc.value.details["assignments"] == "property"
        )

    def test_allowed_once_assignments_are_revoked(self, world):
        PropertyAssignmentService.revoke(
            actor=world.admin, assignment_id=UserProperty.objects.get(user=world.manager).pk
        )
        user = AccountService.change_role(
            actor=world.admin, user=world.manager, role="syndic", syndicat_id=world.syndicat.pk
        )
        assert user.role == StructuralRole.SYNDIC
        assert AuditLogEntry.objects.filter(action="role.changed", metadata__to="syndic").exists()

    def test_last_admin_keeps_the_role(self, world):
        with pytest.raises(BusinessRuleViolation) as exc:
            AccountService.change_role(
                actor=world.admin, user=world.admin, role="standard", syndicat_id=world.syndicat.pk
            )
        assert exc.value.code == "last_admin"

    def test_provider_role_creates_profile(self, world):
        provider = AccountService.change_role(
            actor=world.admin, user=f.make_user(), role="provider", syndicat_id=world.syndicat.pk
        )
        assert provider.provider_profile

    def test_non_admin_cannot_promote_to_admin(self, world):
        with pytest.raises(PermissionDenied):
            AccountService.change_role(
                actor=world.syndic, user=world.outsider, role="admin", syndicat_id=world.syndicat.pk
            )


class TestSyndicVersusManagerAuthority:
    def test_manager_cannot_modify_the_property_or_syndicat(self, world):
        with pytest.raises(PermissionDenied):
            PropertyService.update(
                actor=world.manager, prop=world.prop, changes={"name": "Renamed"}
            )
        with pytest.raises(PermissionDenied):
            SyndicatService.update(
                actor=world.manager, syndicat=world.syndicat, changes={"name": "Renamed"}
            )

    def test_manager_runs_the_property_content(self, world):
        assert BuildingService.create(actor=world.manager, prop=world.prop, data={"name": "Bloc C"})

    def test_syndic_modifies_the_property(self, world):
        assert (
            PropertyService.update(
                actor=world.syndic, prop=world.prop, changes={"name": "Renamed"}
            ).name
            == "Renamed"
        )

    def test_manager_cannot_create_properties(self, world):
        with pytest.raises(PermissionDenied):
            PropertyService.create(
                actor=world.manager,
                syndicat=world.syndicat,
                promoter=f.make_promoter(),
                data={"name": "New"},
            )
