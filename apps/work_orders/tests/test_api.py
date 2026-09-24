import pytest

pytestmark = pytest.mark.django_db


def test_work_order_lifecycle_over_http(api, world):
    manager = api(world.manager, world.syndicat, world.prop)
    created = manager.post(
        "/api/v1/work-orders/",
        {"title": "Fix the lift", "assignee_id": world.maintenance.pk},
        format="json",
    )
    assert created.status_code == 201
    work_order_id = created.json()["id"]

    mine = api(world.maintenance, world.syndicat, world.prop).get(
        "/api/v1/work-orders/", {"assigned_to_me": "true"}
    )
    assert [w["id"] for w in mine.json()["results"]] == [work_order_id]

    started = api(world.maintenance, world.syndicat, world.prop).post(
        f"/api/v1/work-orders/{work_order_id}/transitions/", {"action": "start"}, format="json"
    )
    assert started.status_code == 200 and started.json()["status"] == "IN_PROGRESS"


def test_a_tenant_cannot_create_a_work_order(api, world):
    response = api(world.tenant, world.syndicat, world.prop).post(
        "/api/v1/work-orders/", {"title": "Nope"}, format="json"
    )
    assert response.status_code == 403
