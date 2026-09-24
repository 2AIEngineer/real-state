import pytest

from tests import factories as f

pytestmark = pytest.mark.django_db


def test_request_lifecycle_over_http(api, world):
    created = api(world.tenant, world.syndicat, world.prop).post(
        "/api/v1/service-requests/",
        {
            "unit_id": world.unit.pk,
            "title": "Leak",
            "description": "Sink",
            "category": "plumbing",
            "files": [f.png()],
        },
        format="multipart",
    )
    assert created.status_code == 201 and len(created.json()["files"]) == 1
    sr_id = created.json()["id"]
    assert (
        api(world.manager, world.syndicat, world.prop)
        .post(
            f"/api/v1/service-requests/{sr_id}/assignments/",
            {"resolver_ids": [world.maintenance.pk]},
            format="json",
        )
        .status_code
        == 201
    )
    assert (
        api(world.maintenance, world.syndicat, world.prop)
        .post(f"/api/v1/service-requests/{sr_id}/resolve/", {"note": "Fixed"}, format="multipart")
        .status_code
        == 200
    )
    closed = api(world.tenant, world.syndicat, world.prop).post(
        f"/api/v1/service-requests/{sr_id}/feedback/",
        {"notice": "DONE", "rating": 4},
        format="json",
    )
    assert closed.json()["status"] == "CLOSED"


def test_invalid_transition_is_a_409(api, world):
    created = (
        api(world.tenant, world.syndicat, world.prop)
        .post("/api/v1/service-requests/", {"title": "Noise", "description": "..."}, format="json")
        .json()
    )
    response = api(world.manager, world.syndicat, world.prop).post(
        f"/api/v1/service-requests/{created['id']}/close/"
    )
    assert response.status_code == 409 and response.json()["error"]["code"] == "invalid_transition"


def test_remove_a_file_from_a_request(api, world):
    created = (
        api(world.tenant, world.syndicat, world.prop)
        .post(
            "/api/v1/service-requests/",
            {"title": "Leak", "description": "d", "files": [f.png()]},
            format="multipart",
        )
        .json()
    )
    attachment_id = created["files"][0]["id"]
    # The unit owner cannot touch it; the uploader can.
    assert (
        api(world.owner, world.syndicat, world.prop)
        .delete(f"/api/v1/service-requests/{created['id']}/files/{attachment_id}/")
        .status_code
        == 404
    )
    assert (
        api(world.tenant, world.syndicat, world.prop)
        .delete(f"/api/v1/service-requests/{created['id']}/files/{attachment_id}/")
        .status_code
        == 204
    )
