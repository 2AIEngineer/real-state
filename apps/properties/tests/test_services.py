import datetime as dt
from decimal import Decimal

import pytest

from apps.common.exceptions import (
    BusinessRuleViolation,
    FeatureDisabled,
    InvalidInput,
    PermissionDenied,
)
from apps.library.models import Folder
from apps.notifications.models import InboxNotification
from apps.properties.enums import Feature
from apps.properties.models import OwnershipEndReason, OwnershipStatus, UnitOwnership
from apps.properties.services import (
    Acquirer,
    BuildingService,
    FeatureGate,
    OwnershipService,
    PropertyService,
    UnitService,
)
from tests import factories as f

pytestmark = pytest.mark.django_db

TODAY = dt.date.today()


def active_owner_ids(unit):
    return set(
        UnitOwnership.objects.filter(unit=unit, status=OwnershipStatus.ACTIVE).values_list(
            "owner_id", flat=True
        )
    )


class TestUnitCreation:
    def test_new_unit_is_owned_by_the_promoter(self, world):
        unit = UnitService.create(
            actor=world.manager, building=world.building, data={"number": "A999"}
        )
        ownership = UnitOwnership.objects.get(unit=unit)
        assert ownership.owner == world.prop.promoter.representative_user
        assert ownership.is_promoter_default and ownership.status == OwnershipStatus.ACTIVE

    def test_duplicate_number_in_building(self, world):
        with pytest.raises(InvalidInput):
            UnitService.create(
                actor=world.manager, building=world.building, data={"number": "A101"}
            )

    def test_owners_and_tenants_cannot_create_units(self, world):
        with pytest.raises(PermissionDenied):
            UnitService.create(actor=world.owner, building=world.building, data={"number": "X1"})


class TestOwnershipLedger:
    def test_sale_closes_previous_owners_and_keeps_history(self, world):
        buyer = f.make_user()
        OwnershipService.transfer(
            actor=world.manager, unit=world.unit, acquirers=[Acquirer(buyer)], effective_date=TODAY
        )
        assert active_owner_ids(world.unit) == {buyer.pk}
        history = UnitOwnership.objects.filter(unit=world.unit).order_by("id")
        assert [o.status for o in history] == [
            OwnershipStatus.TERMINATED,
            OwnershipStatus.TERMINATED,
            OwnershipStatus.ACTIVE,
        ]
        assert history[1].end_reason == OwnershipEndReason.SALE

    def test_joint_purchase_with_shares(self, world):
        a, b = f.make_user(), f.make_user()
        OwnershipService.transfer(
            actor=world.manager,
            unit=world.unit,
            effective_date=TODAY,
            acquirers=[Acquirer(a, Decimal("50")), Acquirer(b, Decimal("50"))],
        )
        assert active_owner_ids(world.unit) == {a.pk, b.pk}

    def test_shares_cannot_exceed_100(self, world):
        with pytest.raises(InvalidInput):
            OwnershipService.transfer(
                actor=world.manager,
                unit=world.unit,
                effective_date=TODAY,
                acquirers=[
                    Acquirer(f.make_user(), Decimal("60")),
                    Acquirer(f.make_user(), Decimal("60")),
                ],
            )

    def test_last_owner_leaving_reverts_unit_to_promoter(self, world):
        ownership = UnitOwnership.objects.get(
            unit=world.unit, owner=world.owner, status=OwnershipStatus.ACTIVE
        )
        OwnershipService.end(actor=world.manager, ownership=ownership, end_date=TODAY)
        assert active_owner_ids(world.unit) == {world.prop.promoter.representative_user_id}

    def test_co_owner_leaving_does_not_revert(self, world):
        partner = f.make_user()
        OwnershipService.add_co_owner(
            actor=world.manager, unit=world.unit, user=partner, share=None, start_date=TODAY
        )
        ownership = UnitOwnership.objects.get(
            unit=world.unit, owner=world.owner, status=OwnershipStatus.ACTIVE
        )
        OwnershipService.end(actor=world.manager, ownership=ownership, end_date=TODAY)
        assert active_owner_ids(world.unit) == {partner.pk}

    def test_co_owner_requires_a_sale_first_when_promoter_holds_the_unit(self, world):
        with pytest.raises(BusinessRuleViolation):
            OwnershipService.add_co_owner(
                actor=world.manager,
                unit=world.other_unit,
                user=f.make_user(),
                share=None,
                start_date=TODAY,
            )

    def test_promoter_default_cannot_be_ended_without_sale(self, world):
        ownership = UnitOwnership.objects.get(unit=world.other_unit, status=OwnershipStatus.ACTIVE)
        with pytest.raises(BusinessRuleViolation):
            OwnershipService.end(actor=world.manager, ownership=ownership, end_date=TODAY)

    def test_end_date_cannot_precede_start(self, world):
        with pytest.raises(InvalidInput):
            OwnershipService.transfer(
                actor=world.manager,
                unit=world.unit,
                acquirers=[Acquirer(f.make_user())],
                effective_date=TODAY - dt.timedelta(days=3650),
            )

    def test_promoter_change_moves_unsold_units_only(self, world):
        new_promoter = f.make_promoter()
        PropertyService.change_promoter(
            actor=world.admin, prop=world.prop, promoter=new_promoter, effective_date=TODAY
        )
        assert active_owner_ids(world.other_unit) == {new_promoter.representative_user_id}
        assert active_owner_ids(world.unit) == {world.owner.pk}


class TestPropertyLifecycle:
    def test_creation_notifies_admins_and_seeds_library(self, world):
        other_admin = f.make_admin()
        prop = PropertyService.create(
            actor=world.admin,
            syndicat=world.syndicat,
            promoter=f.make_promoter(),
            data={"name": "Les Pins"},
        )
        assert InboxNotification.objects.filter(
            user=other_admin, notification_type="property.created"
        ).exists()
        assert not InboxNotification.objects.filter(
            user=world.admin, notification_type="property.created"
        ).exists()
        assert Folder.objects.filter(property=prop, is_system=True).count() >= 5

    def test_syndic_can_create_in_own_syndicat_but_not_set_plan(self, world):
        PropertyService.create(
            actor=world.syndic,
            syndicat=world.syndicat,
            promoter=f.make_promoter(),
            data={"name": "P2"},
        )
        with pytest.raises(PermissionDenied):
            PropertyService.create(
                actor=world.syndic,
                syndicat=world.syndicat,
                promoter=f.make_promoter(),
                data={"name": "P3"},
                features={Feature.STORE: False},
            )

    def test_feature_gate(self, world):
        PropertyService.set_features(
            actor=world.admin, prop=world.prop, features={Feature.STORE: False}
        )
        with pytest.raises(FeatureDisabled):
            FeatureGate.require(world.prop, Feature.STORE)
        FeatureGate.require(world.prop, Feature.EVENTS)


class TestListsAreOrdered:
    """Pages of a list must be stable: aggregate queries lose `Meta.ordering`."""

    def test_buildings_come_back_ordered_by_name(self, world):
        f.make_building(world.prop, name="A first")
        names = [
            b.name for b in BuildingService.list_for_property(actor=world.manager, prop=world.prop)
        ]
        assert names == sorted(names)
