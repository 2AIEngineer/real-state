"""The selected syndicat and property bound every dashboard route."""

import pytest

from apps.accounts.enums import StructuralRole
from tests import factories as f

pytestmark = pytest.mark.django_db


def submit(api, world):
    return api(world.tenant, world.syndicat, world.prop).post(
        "/api/v1/service-requests/", {"title": "Leak", "description": "Sink"}, format="json"
    )


def test_a_record_of_another_property_is_not_found_even_for_its_manager(api, world):
    other = f.make_property(syndicat=world.syndicat, name="Other")
    f.assign_role(world.manager, StructuralRole.MANAGER, other)
    sr_id = submit(api, world).json()["id"]

    response = api(world.manager, world.syndicat, other).get(f"/api/v1/service-requests/{sr_id}/")

    assert response.status_code == 404


def test_a_property_outside_the_selected_syndicat_is_refused(api, world):
    foreign = f.make_syndicat(name="Foreign")

    response = api(world.manager, foreign, world.prop).get("/api/v1/service-requests/")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "property_outside_syndicat"


def test_a_property_the_account_cannot_open_is_not_found(api, world):
    other = f.make_property(syndicat=world.syndicat, name="Other")

    response = api(world.tenant, world.syndicat, other).get("/api/v1/service-requests/")

    assert response.status_code == 404


def test_a_property_in_the_url_must_be_the_selected_one(api, world):
    other = f.make_property(syndicat=world.syndicat, name="Other")

    response = api(world.admin, world.syndicat, world.prop).get(f"/api/v1/properties/{other.pk}/")

    assert response.status_code == 404
