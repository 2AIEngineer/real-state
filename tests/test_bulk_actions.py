"""Bulk actions of the dashboard: settle, in the selected property, what is past or due.

Each endpoint runs, on demand and for one property, the job `run_scheduled_jobs`
runs for every property. Management only; other properties are untouched.
"""

import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.enums import PropertyRole
from apps.amenities.models import Booking, BookingStatus
from apps.amenities.services import AmenityService, BookingService
from apps.events.models import Event, EventStatus
from apps.events.services import EventService
from apps.leasing.models import Lease, LeaseStatus
from apps.short_term_rental.models import ShortTermRental, ShortTermRentalStatus
from apps.short_term_rental.services import ShortTermRentalMemberInput, ShortTermRentalService
from apps.surveys.models import Survey, SurveyStatus
from apps.surveys.services import QuestionInput, SurveyService
from tests import factories as f

pytestmark = pytest.mark.django_db

NOW = timezone.now()
TODAY = timezone.localdate()


def run(api, user, world, path):
    return api(user, world.syndicat, world.prop).post(path)


def past_event(world, prop=None):
    event = EventService.create(
        actor=world.admin,
        prop=prop or world.prop,
        title="BBQ",
        start_at=NOW + dt.timedelta(days=1),
        end_at=NOW + dt.timedelta(days=1, hours=2),
        target_roles=[PropertyRole.OWNER],
    )
    Event.objects.filter(pk=event.pk).update(
        start_at=NOW - dt.timedelta(days=2), end_at=NOW - dt.timedelta(days=1)
    )
    return event


def test_events_that_ended_are_completed(api, world):
    event = past_event(world)
    elsewhere = past_event(world, prop=f.make_property(syndicat=world.syndicat))

    response = run(api, world.manager, world, "/api/v1/events/complete-past/")

    assert response.status_code == 200 and response.json() == {"count": 1}
    assert Event.objects.get(pk=event.pk).status == EventStatus.COMPLETED
    assert Event.objects.get(pk=elsewhere.pk).status == EventStatus.SCHEDULED


def test_leases_past_their_end_are_terminated(api, world):
    Lease.objects.filter(pk=world.lease.pk).update(end_date=TODAY - dt.timedelta(days=1))

    response = run(api, world.syndic, world, "/api/v1/leases/expire-due/")

    assert response.json() == {"count": 1}
    assert Lease.objects.get(pk=world.lease.pk).status == LeaseStatus.TERMINATED


def test_surveys_past_their_closing_date_are_closed(api, world):
    survey = SurveyService.create_draft(
        actor=world.manager,
        prop=world.prop,
        title="Lobby",
        target_roles=[PropertyRole.OWNER],
        questions=[QuestionInput("Repaint?", ["Yes", "No"])],
    )
    SurveyService.publish(actor=world.manager, survey=survey)
    Survey.objects.filter(pk=survey.pk).update(closes_at=NOW - dt.timedelta(hours=1))

    response = run(api, world.manager, world, "/api/v1/surveys/close-expired/")

    assert response.json() == {"count": 1}
    assert Survey.objects.get(pk=survey.pk).status == SurveyStatus.CLOSED


def test_bookings_whose_slot_ended_are_settled(api, world):
    def booking(requires_approval):
        amenity = AmenityService.create(
            actor=world.manager,
            prop=world.prop,
            data={"name": f"Room {requires_approval}", "requires_approval": requires_approval},
        )
        start = NOW + dt.timedelta(days=1)
        made = BookingService.book(
            actor=world.tenant, amenity=amenity, start=start, end=start + dt.timedelta(hours=1)
        )
        Booking.objects.filter(pk=made.pk).update(
            start_datetime=NOW - dt.timedelta(hours=3), end_datetime=NOW - dt.timedelta(hours=2)
        )
        return made

    confirmed, pending = booking(False), booking(True)

    response = run(api, world.manager, world, "/api/v1/bookings/complete-past/")

    assert response.json() == {"count": 2}
    assert Booking.objects.get(pk=confirmed.pk).status == BookingStatus.COMPLETED
    cancelled = Booking.objects.get(pk=pending.pk)
    assert cancelled.status == BookingStatus.CANCELLED and cancelled.cancellation_reason


def test_short_term_rentals_past_their_checkout_are_completed(api, world):
    rental = ShortTermRentalService.declare(
        actor=world.tenant,
        unit=world.unit,
        checkin_date=TODAY + dt.timedelta(days=2),
        checkout_date=TODAY + dt.timedelta(days=4),
        members=[ShortTermRentalMemberInput("Ana", "Diaz")],
    )
    ShortTermRental.objects.filter(pk=rental.pk).update(
        checkin_date=TODAY - dt.timedelta(days=4), checkout_date=TODAY - dt.timedelta(days=1)
    )

    response = run(api, world.manager, world, "/api/v1/short-term-rentals/complete-past/")

    assert response.json() == {"count": 1}
    assert ShortTermRental.objects.get(pk=rental.pk).status == ShortTermRentalStatus.COMPLETED


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/events/complete-past/",
        "/api/v1/leases/expire-due/",
        "/api/v1/surveys/close-expired/",
        "/api/v1/bookings/complete-past/",
        "/api/v1/short-term-rentals/complete-past/",
    ],
)
def test_only_the_management_runs_bulk_actions(api, world, path):
    assert run(api, world.tenant, world, path).status_code == 403
    assert run(api, world.security, world, path).status_code == 403
    assert run(api, world.admin, world, path).json() == {"count": 0}
