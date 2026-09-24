import pytest

pytestmark = pytest.mark.django_db


def test_visitor_arrival_and_departure_over_http(api, world):
    security = api(world.security, world.syndicat, world.prop)
    created = security.post(
        "/api/v1/visitors/",
        {"unit_id": world.unit.pk, "first_name": "Ada", "last_name": "Lovelace"},
        format="json",
    )
    assert created.status_code == 201 and created.json()["status"] == "ARRIVED"

    left = security.post(f"/api/v1/visitors/{created.json()['id']}/departure/", {}, format="json")
    assert left.status_code == 200 and left.json()["status"] == "LEFT"


def test_a_denied_visit_needs_a_reason(api, world):
    response = api(world.security, world.syndicat, world.prop).post(
        "/api/v1/visitors/",
        {"unit_id": world.unit.pk, "first_name": "Bob", "last_name": "B", "admitted": False},
        format="json",
    )
    assert response.status_code == 400 and response.json()["error"]["field"] == "denial_reason"
