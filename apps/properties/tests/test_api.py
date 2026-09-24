import datetime as dt

import pytest

from tests import factories as f

pytestmark = pytest.mark.django_db


def test_property_creation_flow(api, world):
    client = api(world.admin, world.syndicat, world.prop)
    promoter = client.post(
        "/api/v1/promoters/",
        {"name": "Build Co", "representative_email": "rep@build.test"},
        format="json",
    )
    assert promoter.status_code == 201
    prop = client.post(
        "/api/v1/properties/",
        {
            "syndicat_id": world.syndicat.pk,
            "promoter_id": promoter.json()["id"],
            "name": "Palms",
            "features": {"store": False},
        },
        format="json",
    )
    assert prop.status_code == 201 and prop.json()["features"]["store"] is False
    building = client.post(
        f"/api/v1/properties/{prop.json()['id']}/buildings/", {"name": "A"}, format="json"
    ).json()
    unit = client.post(
        f"/api/v1/buildings/{building['id']}/units/", {"number": "1", "floor": -1}, format="json"
    )
    assert unit.status_code == 201
    history = client.get(f"/api/v1/units/{unit.json()['id']}/ownerships/").json()["results"]
    assert history[0]["is_promoter_default"] is True


def test_ownership_transfer(api, world):
    buyer = f.make_user()
    response = api(world.manager, world.syndicat, world.prop).post(
        f"/api/v1/units/{world.other_unit.pk}/ownerships/transfer/",
        {"acquirers": [{"user_id": buyer.pk}], "effective_date": str(dt.date.today())},
        format="json",
    )
    assert response.status_code == 201 and response.json()[0]["owner"]["id"] == buyer.pk


def test_owners_and_tenants_see_only_their_units(api, world):
    body = (
        api(world.tenant, world.syndicat, world.prop)
        .get(f"/api/v1/buildings/{world.building.pk}/units/")
        .json()
    )
    assert [u["id"] for u in body["results"]] == [world.unit.pk]


def test_logo_upload(api, world):
    response = api(world.syndic, world.syndicat, world.prop).patch(
        f"/api/v1/properties/{world.prop.pk}/logo/", {"file": f.png()}, format="multipart"
    )
    assert response.status_code == 200 and response.json()["logo"]["mime_type"] == "image/png"


def test_manager_cannot_change_the_property_record(api, world):
    response = api(world.manager, world.syndicat, world.prop).patch(
        f"/api/v1/properties/{world.prop.pk}/", {"name": "Renamed"}, format="json"
    )
    assert response.status_code == 403
