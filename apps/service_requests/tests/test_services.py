import pytest

from apps.common.exceptions import InvalidInput, InvalidTransition, PermissionDenied
from apps.notifications.models import InboxNotification
from apps.service_requests.models import (
    RequesterNotice,
    ServiceRequestCategory,
    ServiceRequestStatus,
)
from apps.service_requests.services import Feedback, RoundService, ServiceRequestService
from tests import factories as f

pytestmark = pytest.mark.django_db


def submit(world, actor=None, unit="default", **kwargs):
    return ServiceRequestService.submit(
        actor=actor or world.tenant,
        prop=world.prop,
        unit=world.unit if unit == "default" else unit,
        title="Leak",
        description="Kitchen sink leaks",
        category=ServiceRequestCategory.PLUMBING,
        **kwargs,
    )


def notified(event_type):
    return set(
        InboxNotification.objects.filter(notification_type=event_type).values_list(
            "user_id", flat=True
        )
    )


class TestSubmission:
    def test_tenant_submits_for_their_unit_and_everyone_concerned_is_told(self, world):
        sr = submit(world)
        assert sr.requester == world.tenant
        assert {world.tenant.pk, world.manager.pk, world.syndic.pk, world.admin.pk} <= notified(
            "service_request.created"
        )

    def test_cannot_submit_for_someone_elses_unit(self, world):
        with pytest.raises(PermissionDenied):
            submit(world, actor=world.tenant, unit=world.other_unit)

    def test_outsider_cannot_submit_for_common_areas(self, world):
        with pytest.raises(PermissionDenied):
            submit(world, actor=world.outsider, unit=None)

    def test_owner_submits_for_common_areas(self, world):
        assert submit(world, actor=world.owner, unit=None).unit is None


class TestLifecycle:
    def test_full_round_trip(self, world):
        sr = submit(world)
        RoundService.assign(actor=world.manager, sr=sr, resolvers=[world.maintenance])
        assert world.maintenance.pk in notified("service_request.assigned")
        RoundService.resolve(actor=world.maintenance, sr=sr, note="Seal replaced", files=[f.png()])
        sr.refresh_from_db()
        assert sr.status == ServiceRequestStatus.RESOLVED
        sr = RoundService.give_feedback(
            actor=world.tenant, sr=sr, feedback=Feedback(RequesterNotice.DONE, rating=5)
        )
        assert sr.status == ServiceRequestStatus.CLOSED
        assert sr.assignments.get().requester_rating == 5

    def test_not_done_reopens_a_new_round(self, world):
        sr = submit(world)
        RoundService.assign(actor=world.manager, sr=sr, resolvers=[world.maintenance])
        RoundService.resolve(actor=world.maintenance, sr=sr)
        sr = RoundService.give_feedback(
            actor=world.tenant, sr=sr, feedback=Feedback(RequesterNotice.NOT_DONE, rating=2)
        )
        assert sr.status == ServiceRequestStatus.OPEN and sr.current_round == 2
        RoundService.assign(actor=world.manager, sr=sr, resolvers=[world.maintenance])
        assert sr.assignments.filter(resolver=world.maintenance).count() == 2

    def test_request_is_resolved_only_when_every_resolver_is_done(self, world):
        second = f.make_user()
        f.assign_role(second, "maintenance", world.prop)
        sr = submit(world)
        RoundService.assign(actor=world.manager, sr=sr, resolvers=[world.maintenance, second])
        RoundService.resolve(actor=world.maintenance, sr=sr)
        sr.refresh_from_db()
        assert sr.status == ServiceRequestStatus.IN_PROGRESS

    def test_resolver_must_hold_maintenance_role(self, world):
        with pytest.raises(InvalidInput):
            RoundService.assign(actor=world.manager, sr=submit(world), resolvers=[world.security])

    def test_only_assigned_resolver_resolves(self, world):
        sr = submit(world)
        RoundService.assign(actor=world.manager, sr=sr, resolvers=[world.maintenance])
        with pytest.raises(PermissionDenied):
            RoundService.resolve(actor=world.manager, sr=sr)

    def test_only_requester_gives_feedback(self, world):
        sr = submit(world)
        RoundService.assign(actor=world.manager, sr=sr, resolvers=[world.maintenance])
        RoundService.resolve(actor=world.maintenance, sr=sr)
        with pytest.raises(PermissionDenied):
            RoundService.give_feedback(
                actor=world.co_tenant, sr=sr, feedback=Feedback(RequesterNotice.DONE)
            )

    def test_cancelled_request_cannot_be_assigned(self, world):
        sr = ServiceRequestService.cancel(actor=world.tenant, sr=submit(world))
        with pytest.raises(InvalidTransition):
            RoundService.assign(actor=world.manager, sr=sr, resolvers=[world.maintenance])

    def test_visibility(self, world):
        sr = submit(world)
        assert (
            list(
                ServiceRequestService.list_visible(actor=world.co_tenant, property_id=world.prop.pk)
            )
            == []
        )
        assert list(
            ServiceRequestService.list_visible(actor=world.manager, property_id=world.prop.pk)
        ) == [sr]
        RoundService.assign(actor=world.manager, sr=sr, resolvers=[world.maintenance])
        assert list(
            ServiceRequestService.list_visible(actor=world.maintenance, property_id=world.prop.pk)
        ) == [sr]
