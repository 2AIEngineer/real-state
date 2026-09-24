import pytest

from tests import factories as f

pytestmark = pytest.mark.django_db


def test_manager_is_assigned_to_the_selected_property(api, world):
    f.make_property(syndicat=world.syndicat)  # another property of the same syndicat: untouched
    response = api(world.syndic, syndicat=world.syndicat, prop=world.prop).post(
        "/api/v1/users/",
        {
            "email": "new.manager@example.test",
            "first_name": "N",
            "last_name": "M",
            "role": "manager",
        },
        format="json",
    )
    assert response.status_code == 201 and response.json()["role"] == "manager"
    client = api(world.syndic, world.syndicat, world.prop)
    properties = client.get(f"/api/v1/users/{response.json()['id']}/property-assignments/").json()
    assert [a["property"] for a in properties] == [world.prop.pk]
    assert client.get(f"/api/v1/users/{response.json()['id']}/syndicat-assignments/").json() == []


def test_a_second_property_is_granted_once_it_is_the_selected_one(api, world):
    other = f.make_property(syndicat=world.syndicat)
    created = (
        api(world.syndic, syndicat=world.syndicat, prop=world.prop)
        .post(
            "/api/v1/users/",
            {"email": "m2@example.test", "first_name": "N", "last_name": "M", "role": "manager"},
            format="json",
        )
        .json()
    )
    added = api(world.syndic, syndicat=world.syndicat, prop=other).post(
        f"/api/v1/users/{created['id']}/property-assignments/"
    )
    assert added.status_code == 201
    listed = (
        api(world.syndic, world.syndicat, world.prop)
        .get(f"/api/v1/users/{created['id']}/property-assignments/")
        .json()
    )
    assert {a["property"] for a in listed} == {world.prop.pk, other.pk}


def test_account_creation_requires_a_selected_syndicat(api, world):
    response = api(world.syndic).post(
        "/api/v1/users/",
        {"email": "m3@example.test", "first_name": "N", "last_name": "M"},
        format="json",
    )
    assert response.status_code == 400 and response.json()["error"]["code"] == "selection_required"


def test_a_role_exercised_in_a_property_requires_the_open_property(api, world):
    response = api(world.syndic, syndicat=world.syndicat).post(
        "/api/v1/users/",
        {"email": "m4@example.test", "first_name": "N", "last_name": "M", "role": "manager"},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["error"]["field"] == "X-Property-Id"


def test_role_change_refused_with_active_assignments(api, world):
    response = api(world.admin, world.syndicat, world.prop).post(
        f"/api/v1/users/{world.security.pk}/role/", {"role": "cleaning"}, format="json"
    )
    assert response.status_code == 409 and response.json()["error"]["code"] == "active_assignments"


def test_revoke_then_change_role(api, world):
    client = api(world.admin, world.syndicat, world.prop)
    row = client.get(f"/api/v1/users/{world.security.pk}/building-assignments/").json()[0]
    revoked = api(world.manager, world.syndicat, world.prop).post(
        f"/api/v1/building-assignments/{row['id']}/revoke/"
    )
    assert revoked.status_code == 200 and revoked.json()["is_active"] is False
    changed = client.post(
        f"/api/v1/users/{world.security.pk}/role/",
        {"role": "cleaning", "building_ids": [world.building.pk, world.other_building.pk]},
        format="json",
    )
    assert changed.status_code == 200 and changed.json()["role"] == "cleaning"


def test_buildings_outside_the_open_property_are_refused(api, world):
    elsewhere = f.make_building(f.make_property())
    response = api(world.admin, world.syndicat, world.prop).post(
        "/api/v1/users/",
        {
            "email": "guard@example.test",
            "first_name": "G",
            "last_name": "G",
            "role": "security",
            "building_ids": [elsewhere.pk],
        },
        format="json",
    )
    assert (
        response.status_code == 400
        and response.json()["error"]["code"] == "building_outside_property"
    )


def test_each_table_has_its_own_endpoint(api, world):
    """A syndic account is assigned to syndicats, and to nothing else."""
    client = api(world.admin, world.syndicat, world.prop)
    syndicats = client.get(f"/api/v1/users/{world.syndic.pk}/syndicat-assignments/").json()
    assert [row["syndicat"] for row in syndicats] == [world.syndicat.pk]
    assert syndicats[0]["syndicat_name"] == world.syndicat.name
    assert client.get(f"/api/v1/users/{world.syndic.pk}/property-assignments/").json() == []
    assert client.get(f"/api/v1/users/{world.syndic.pk}/building-assignments/").json() == []


def test_buildings_are_named_in_the_body_of_their_own_endpoint(api, world):
    guard = (
        api(world.admin, world.syndicat, world.prop)
        .post(
            "/api/v1/users/",
            {
                "email": "guard2@example.test",
                "first_name": "G",
                "last_name": "G",
                "role": "cleaning",
                "building_ids": [world.building.pk],
            },
            format="json",
        )
        .json()
    )
    added = api(world.admin, world.syndicat, world.prop).post(
        f"/api/v1/users/{guard['id']}/building-assignments/",
        {"building_ids": [world.other_building.pk]},
        format="json",
    )
    assert added.status_code == 201 and [row["building"] for row in added.json()] == [
        world.other_building.pk
    ]


def test_an_assignment_on_the_wrong_table_is_refused(api, world):
    """A cleaning account is placed by its buildings: the property table refuses it."""
    response = api(world.admin, world.syndicat, world.prop).post(
        f"/api/v1/users/{world.security.pk}/property-assignments/"
    )
    assert response.status_code == 400 and response.json()["error"]["field"] == "property_ids"
