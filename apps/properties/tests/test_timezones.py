"""Dates and clock times are those of the property, not of the server."""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from apps.amenities.services import AmenityService, BookingService
from apps.common.exceptions import InvalidInput
from apps.leasing.models import LeaseStatus
from apps.leasing.services import LeaseService
from apps.properties import timezones

pytestmark = pytest.mark.django_db


def set_zone(prop, name):
    prop.timezone = name
    prop.save(update_fields=["timezone"])


def test_a_new_property_takes_the_default_zone(world, settings):
    assert world.prop.timezone == settings.TIME_ZONE


def test_opening_hours_are_read_on_the_clocks_of_the_property(world):
    set_zone(world.prop, "America/Montreal")
    room = AmenityService.create(
        actor=world.manager,
        prop=world.prop,
        data={
            "name": "Room",
            "requires_approval": False,
            "min_duration_minutes": 30,
            "max_duration_minutes": 180,
            "opening_time": dt.time(8),
            "closing_time": dt.time(20),
        },
    )
    montreal = ZoneInfo("America/Montreal")
    tomorrow = (timezone.now() + dt.timedelta(days=1)).astimezone(montreal).date()
    nine_in_montreal = dt.datetime.combine(tomorrow, dt.time(9), tzinfo=montreal)

    booking = BookingService.book(
        actor=world.tenant,
        amenity=room,
        start=nine_in_montreal,
        end=nine_in_montreal + dt.timedelta(hours=1),
    )
    assert booking.pk
    # 07:00 in Montreal is 11:00 or 12:00 UTC: open for UTC, closed for the property.
    seven_in_montreal = nine_in_montreal - dt.timedelta(hours=2)
    with pytest.raises(InvalidInput):
        BookingService.book(
            actor=world.tenant,
            amenity=room,
            start=seven_in_montreal,
            end=seven_in_montreal + dt.timedelta(minutes=30),
        )


def test_a_lease_ends_when_the_day_is_over_where_the_property_is(world):
    set_zone(world.prop, "Pacific/Kiritimati")  # UTC+14: already tomorrow there
    local_today = timezones.today(world.prop)
    world.lease.end_date = local_today - dt.timedelta(days=1)
    world.lease.save(update_fields=["end_date"])

    assert LeaseService.expire_due() == 1
    world.lease.refresh_from_db()
    assert world.lease.status != LeaseStatus.ACTIVE


def test_an_unknown_zone_is_refused(api, world):
    response = api(world.admin, world.syndicat, world.prop).patch(
        f"/api/v1/properties/{world.prop.pk}/", {"timezone": "Mars/Olympus"}, format="json"
    )

    assert response.status_code == 400


def test_the_zone_is_set_through_the_api(api, world):
    response = api(world.admin, world.syndicat, world.prop).patch(
        f"/api/v1/properties/{world.prop.pk}/", {"timezone": "Europe/Paris"}, format="json"
    )

    assert response.status_code == 200 and response.json()["timezone"] == "Europe/Paris"
