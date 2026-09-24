import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.enums import PropertyRole
from apps.common.exceptions import InvalidInput, InvalidTransition
from apps.events.models import EventStatus
from apps.events.services import EventService
from apps.notifications.models import InboxNotification

pytestmark = pytest.mark.django_db


def create(world, **kwargs):
    start = timezone.now() + dt.timedelta(days=3)
    return EventService.create(
        actor=world.manager,
        prop=world.prop,
        title="BBQ",
        start_at=start,
        end_at=start + dt.timedelta(hours=3),
        target_roles=[PropertyRole.OWNER, PropertyRole.TENANT],
        **kwargs,
    )


def notified(event_type):
    return set(
        InboxNotification.objects.filter(notification_type=event_type).values_list(
            "user_id", flat=True
        )
    )


def test_creation_notifies_the_targeted_roles(world):
    create(world)
    assert {world.owner.pk, world.tenant.pk, world.co_tenant.pk} <= notified("event.created")


def test_significant_change_notifies_but_cosmetic_does_not(world):
    event = create(world)
    EventService.update(actor=world.manager, event=event, changes={"description": "Bring salads"})
    assert notified("event.updated") == set()
    EventService.update(actor=world.manager, event=event, changes={"location": "Rooftop"})
    assert world.tenant.pk in notified("event.updated")


def test_schedule_must_be_consistent(world):
    event = create(world)
    with pytest.raises(InvalidInput):
        EventService.update(
            actor=world.manager,
            event=event,
            changes={"end_at": event.start_at - dt.timedelta(hours=1)},
        )


def test_cancelled_event_is_frozen(world):
    event = EventService.cancel(actor=world.manager, event=create(world), reason="Rain")
    assert event.status == EventStatus.CANCELLED and world.tenant.pk in notified("event.cancelled")
    with pytest.raises(InvalidTransition):
        EventService.update(actor=world.manager, event=event, changes={"title": "x"})


def test_archiving_an_upcoming_event_notifies(world):
    event = create(world)
    EventService.archive(actor=world.manager, event=event)
    assert world.owner.pk in notified("event.archived")
    assert list(EventService.list_visible(actor=world.owner, prop=world.prop)) == []


def test_completion_job(world):
    event = create(world)
    count = EventService.complete_past(now=event.end_at + dt.timedelta(minutes=1))
    event.refresh_from_db()
    assert count == 1 and event.status == EventStatus.COMPLETED
    assert {world.owner.pk, world.tenant.pk} <= notified("event.completed")
    assert EventService.complete_past(now=event.end_at + dt.timedelta(minutes=2)) == 0  # idempotent
