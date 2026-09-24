import datetime as dt
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.amenities.models import BookingMode, BookingStatus
from apps.amenities.services import AmenityService, BookingService
from apps.common.exceptions import (
    BusinessRuleViolation,
    InvalidInput,
    InvalidTransition,
    PermissionDenied,
)

pytestmark = pytest.mark.django_db


def amenity(world, **data):
    defaults = {
        "name": data.pop("name", "Gym"),
        "requires_approval": False,
        "min_duration_minutes": 30,
        "max_duration_minutes": 180,
    }
    return AmenityService.create(actor=world.manager, prop=world.prop, data={**defaults, **data})


def slot(days=1, hour=10, hours=1):
    start = (timezone.now() + dt.timedelta(days=days)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    return start, start + dt.timedelta(hours=hours)


def book(world, target, user=None, days=1, hour=10, hours=1, **kwargs):
    start, end = slot(days, hour, hours)
    return BookingService.book(
        actor=user or world.tenant, amenity=target, start=start, end=end, **kwargs
    )


class TestExclusive:
    def test_overlap_is_rejected_by_the_database_constraint(self, world):
        gym = amenity(world)
        book(world, gym)
        with pytest.raises(BusinessRuleViolation) as exc:
            book(world, gym, user=world.owner)
        assert exc.value.code == "slot_unavailable"

    def test_back_to_back_slots_are_fine(self, world):
        gym = amenity(world)
        book(world, gym, hour=10)
        assert book(world, gym, user=world.owner, hour=11).status == BookingStatus.CONFIRMED

    def test_cancelled_booking_frees_the_slot(self, world):
        gym = amenity(world)
        BookingService.cancel(actor=world.tenant, booking=book(world, gym))
        book(world, gym, user=world.owner)


class TestShared:
    def test_capacity_is_enforced(self, world):
        pool = amenity(world, name="Pool", booking_mode=BookingMode.SHARED, capacity=5)
        book(world, pool, party_size=3)
        book(world, pool, user=world.owner, party_size=2)
        with pytest.raises(BusinessRuleViolation) as exc:
            book(world, pool, user=world.co_tenant, party_size=1)
        assert exc.value.code == "capacity_exceeded"


class TestRules:
    def test_duration_and_opening_hours(self, world):
        room = amenity(world, name="Room", opening_time=dt.time(8), closing_time=dt.time(20))
        with pytest.raises(InvalidInput):
            book(world, room, hours=4)
        with pytest.raises(InvalidInput):
            book(world, room, hour=19, hours=2)

    def test_past_and_far_future_are_refused(self, world):
        gym = amenity(world, max_advance_days=7)
        with pytest.raises(InvalidInput):
            book(world, gym, days=-1)
        with pytest.raises(InvalidInput):
            book(world, gym, days=30)

    def test_only_owners_tenants_and_management_book(self, world):
        with pytest.raises(PermissionDenied):
            book(world, amenity(world), user=world.security)

    def test_approval_flow(self, world):
        hall = amenity(world, name="Party hall", requires_approval=True)
        booking = book(world, hall)
        assert booking.status == BookingStatus.PENDING
        booking = BookingService.decide(actor=world.manager, booking=booking, approve=True)
        assert booking.status == BookingStatus.CONFIRMED
        with pytest.raises(InvalidTransition):
            BookingService.decide(actor=world.manager, booking=booking, approve=False)

    def test_pending_booking_also_holds_the_slot(self, world):
        hall = amenity(world, name="Party hall", requires_approval=True)
        book(world, hall)
        with pytest.raises(BusinessRuleViolation):
            book(world, hall, user=world.owner)

    def test_inactive_amenity_cannot_be_booked(self, world):
        gym = AmenityService.update(
            actor=world.manager, amenity=amenity(world), changes={"is_active": False}
        )
        with pytest.raises(BusinessRuleViolation):
            book(world, gym)


class TestPrices:
    def test_prices_default_to_zero(self, world):
        gym = amenity(world)
        assert (gym.fee, gym.security_fee, gym.hourly_price) == (0, 0, 0)

    def test_prices_are_stored(self, world):
        hall = amenity(
            world,
            name="Party hall",
            fee=Decimal("20.00"),
            security_fee=Decimal("15.50"),
            hourly_price=Decimal("8.00"),
        )
        hall.refresh_from_db()
        assert (hall.fee, hall.security_fee, hall.hourly_price) == (
            Decimal("20.00"),
            Decimal("15.50"),
            Decimal("8.00"),
        )

    def test_hourly_price_can_be_set_back_to_free(self, world):
        hall = amenity(world, name="Party hall", hourly_price=Decimal("8.00"))
        hall = AmenityService.update(
            actor=world.manager, amenity=hall, changes={"hourly_price": Decimal("0")}
        )
        assert hall.hourly_price == 0

    def test_negative_price_is_refused(self, world):
        with pytest.raises(InvalidInput) as exc:
            amenity(world, security_fee=Decimal("-1"))
        assert exc.value.field == "security_fee"
