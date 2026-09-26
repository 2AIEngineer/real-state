"""The demo generator runs end to end, at a reduced size so the suite stays fast.

It goes through the business services: when a rule changes, this test says so
before a developer finds `seed_demo` broken.
"""

import io

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.accounts.enums import StructuralRole
from apps.amenities.models import Booking
from apps.demo.seed import commerce, operations, referential
from apps.leasing.models import Lease, LeaseStatus
from apps.notifications.models import NotificationPreference
from apps.properties.models import Building, Property, Syndicat, Unit, UnitOwnership
from apps.service_requests.models import ServiceRequest, ServiceRequestStatus
from apps.store.models import Order
from apps.visitors.models import Visitor

pytestmark = pytest.mark.django_db


@pytest.fixture
def small_demo(monkeypatch):
    monkeypatch.setattr(referential, "FLOORS", 3)
    monkeypatch.setattr(referential, "UNITS_PER_FLOOR", 4)
    monkeypatch.setattr(commerce, "BOOKINGS_PER_AMENITY", 3)
    monkeypatch.setattr(commerce, "ORDERS_PER_RESIDENCE", 6)
    monkeypatch.setattr(commerce, "LISTINGS_PER_RESIDENCE", 4)
    monkeypatch.setattr(operations, "VISITORS_PER_RESIDENCE", 6)
    monkeypatch.setattr(operations, "RENTALS_PER_RESIDENCE", 4)
    monkeypatch.setattr(
        operations,
        "REQUEST_OUTCOMES",
        ["closed", "open", "in_progress", "resolved", "cancelled", "reopened"],
    )


def test_the_demo_builds_a_complete_portfolio(small_demo):
    call_command("seed_demo", seed=3, stdout=io.StringIO())

    assert Syndicat.objects.count() == 2
    assert Property.objects.count() == 4
    assert Building.objects.count() == 8
    assert Unit.objects.count() == 8 * 3 * 4
    assert UnitOwnership.objects.filter(is_promoter_default=False).exists()
    assert Lease.objects.filter(status=LeaseStatus.ACTIVE).exists()
    assert Lease.objects.filter(status=LeaseStatus.TERMINATED).exists()
    statuses = set(ServiceRequest.objects.values_list("status", flat=True))
    assert {ServiceRequestStatus.OPEN, ServiceRequestStatus.CLOSED} <= statuses
    assert Booking.objects.exists() and Order.objects.exists() and Visitor.objects.exists()
    users = get_user_model().objects.filter(is_technical_account=False)
    assert not users.filter(notification_preference__isnull=True).exists()
    security = NotificationPreference.objects.filter(user__role=StructuralRole.SECURITY)
    assert security.exists() and not security.filter(announcements_enabled=True).exists()


def test_it_refuses_to_run_on_a_database_holding_data(small_demo, world):
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("seed_demo", stdout=io.StringIO())
