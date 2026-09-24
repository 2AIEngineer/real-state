import datetime as dt

import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db


def test_booking_conflict_over_http(api, world):
    amenity = (
        api(world.manager, world.syndicat, world.prop)
        .post("/api/v1/amenities/", {"name": "Tennis", "requires_approval": False}, format="json")
        .json()
    )
    start = (timezone.now() + dt.timedelta(days=2)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    payload = {
        "amenity_id": amenity["id"],
        "start_datetime": start.isoformat(),
        "end_datetime": (start + dt.timedelta(hours=1)).isoformat(),
    }
    assert (
        api(world.tenant, world.syndicat, world.prop)
        .post("/api/v1/bookings/", payload, format="json")
        .status_code
        == 201
    )
    conflict = api(world.owner, world.syndicat, world.prop).post(
        "/api/v1/bookings/", payload, format="json"
    )
    assert conflict.status_code == 409 and conflict.json()["error"]["code"] == "slot_unavailable"
    schedule = api(world.owner, world.syndicat, world.prop).get(
        f"/api/v1/amenities/{amenity['id']}/schedule/",
        {"start": start.isoformat(), "end": (start + dt.timedelta(days=1)).isoformat()},
    )
    assert schedule.status_code == 200 and "booker" not in schedule.json()[0]


def test_prices_over_http(api, world):
    client = api(world.manager, world.syndicat, world.prop)
    free = client.post("/api/v1/amenities/", {"name": "Garden"}, format="json").json()
    assert (free["fee"], free["security_fee"], free["hourly_price"]) == ("0.00", "0.00", "0.00")
    paid = client.post(
        "/api/v1/amenities/",
        {"name": "Party hall", "fee": "20.00", "security_fee": "15.50", "hourly_price": "8"},
        format="json",
    ).json()
    assert (paid["fee"], paid["security_fee"], paid["hourly_price"]) == ("20.00", "15.50", "8.00")
    negative = client.post("/api/v1/amenities/", {"name": "Pool", "fee": "-5"}, format="json")
    assert negative.status_code == 400
