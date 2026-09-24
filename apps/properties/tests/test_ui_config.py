"""The UI configuration path: which syndicats, then which properties, an
account may open (`SyndicatService.list_reachable` / `.get_reachable`,
`PropertyService.list_reachable_in`)."""

import pytest

from apps.accounts.enums import StructuralRole
from apps.common.exceptions import NotFound
from apps.properties.services import PropertyService, SyndicatService
from tests import factories as f

pytestmark = pytest.mark.django_db


def syndicat_ids(actor):
    return [s.pk for s in SyndicatService.list_reachable(actor=actor)]


def property_ids(actor, syndicat):
    return [p.pk for p in PropertyService.list_reachable_in(actor=actor, syndicat=syndicat)]


class TestSyndicatStep:
    def test_admin_reaches_every_syndicat(self, world):
        other = f.make_syndicat()
        assert set(syndicat_ids(world.admin)) == {world.syndicat.pk, other.pk}

    def test_syndic_reaches_their_syndicat_even_without_a_property_yet(self, world):
        bare = f.make_syndicat()
        syndic = f.make_user(email="bare-syndic@example.test")
        f.assign_role(syndic, StructuralRole.SYNDIC, bare)

        assert syndicat_ids(syndic) == [bare.pk]

    def test_manager_reaches_the_syndicat_of_their_property(self, world):
        assert syndicat_ids(world.manager) == [world.syndicat.pk]

    def test_owner_and_tenant_reach_the_syndicat_of_their_unit(self, world):
        assert syndicat_ids(world.owner) == [world.syndicat.pk]
        assert syndicat_ids(world.tenant) == [world.syndicat.pk]

    def test_provider_reaches_no_syndicat(self, world):
        provider = f.make_user(email="provider@example.test", role=StructuralRole.PROVIDER)
        assert syndicat_ids(provider) == []

    def test_outsider_reaches_nothing(self, world):
        assert syndicat_ids(world.outsider) == []

    def test_the_property_count_only_counts_reachable_active_properties(self, world):
        f.make_property(syndicat=world.syndicat)  # a second one, unmanaged by world.manager
        (listed,) = SyndicatService.list_reachable(actor=world.manager)
        assert listed.accessible_properties_count == 1

    def test_get_reachable_refuses_an_out_of_reach_syndicat(self, world):
        with pytest.raises(NotFound):
            SyndicatService.get_reachable(actor=world.outsider, syndicat_id=world.syndicat.pk)


class TestPropertyStep:
    def test_manager_reaches_their_property_only(self, world):
        other = f.make_property(syndicat=world.syndicat)
        assert property_ids(world.manager, world.syndicat) == [world.prop.pk]
        assert other.pk not in property_ids(world.manager, world.syndicat)

    def test_syndic_reaches_every_property_of_their_syndicat(self, world):
        other = f.make_property(syndicat=world.syndicat)
        assert set(property_ids(world.syndic, world.syndicat)) == {world.prop.pk, other.pk}

    def test_a_property_of_another_syndicat_is_excluded(self, world):
        elsewhere = f.make_property()
        assert elsewhere.pk not in property_ids(world.admin, world.syndicat)
