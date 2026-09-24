import datetime as dt

import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db


def test_event_lifecycle_over_http(api, world):
    manager = api(world.manager, world.syndicat, world.prop)
    start = timezone.now() + dt.timedelta(days=2)
    created = manager.post(
        "/api/v1/events/",
        {
            "title": "BBQ",
            "start_at": start.isoformat(),
            "end_at": (start + dt.timedelta(hours=3)).isoformat(),
            "target_roles": ["tenant"],
        },
        format="json",
    )
    assert created.status_code == 201
    event_id = created.json()["id"]

    listed = api(world.tenant, world.syndicat, world.prop).get("/api/v1/events/")
    assert [e["id"] for e in listed.json()["results"]] == [event_id]

    cancelled = manager.post(
        f"/api/v1/events/{event_id}/cancel/", {"reason": "Rain"}, format="json"
    )
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"


def test_a_tenant_cannot_create_an_event(api, world):
    start = timezone.now() + dt.timedelta(days=2)
    response = api(world.tenant, world.syndicat, world.prop).post(
        "/api/v1/events/",
        {
            "title": "Party",
            "start_at": start.isoformat(),
            "end_at": (start + dt.timedelta(hours=1)).isoformat(),
            "target_roles": ["tenant"],
        },
        format="json",
    )
    assert response.status_code == 403
