import datetime as dt

import pytest

pytestmark = pytest.mark.django_db


def test_short_rental_declared_and_cancelled_over_http(api, world):
    tenant = api(world.tenant, world.syndicat, world.prop)
    checkin = dt.date.today() + dt.timedelta(days=5)
    created = tenant.post(
        "/api/v1/short-term-rentals/",
        {
            "unit_id": world.unit.pk,
            "checkin_date": checkin.isoformat(),
            "checkout_date": (checkin + dt.timedelta(days=2)).isoformat(),
            "members": [{"first_name": "Guest", "last_name": "One"}],
        },
        format="json",
    )
    assert created.status_code == 201, created.json()
    rental_id = created.json()["id"]

    listed = tenant.get("/api/v1/short-term-rentals/")
    assert [r["id"] for r in listed.json()["results"]] == [rental_id]

    cancelled = tenant.post(
        f"/api/v1/short-term-rentals/{rental_id}/cancel/",
        {"reason": "Change of plans"},
        format="json",
    )
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"
