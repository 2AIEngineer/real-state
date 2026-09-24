"""What a service's `delete()` takes with it: files and notification traces.

Nothing does this automatically — no signal, no cascade for `Attachment` or
`InboxNotification` (they reference a row by `entity_type`/`entity_id`, not by
a foreign key). Each service explicitly cleans up what it owns, in its own
`delete()`, before the row disappears.
"""

import pytest

from apps.common.files.rules import EntityType
from apps.common.files.service import AttachmentService
from apps.common.models import Attachment
from apps.notifications.models import InboxNotification, RecipientSnapshot
from apps.service_requests.models import ServiceRequest, ServiceRequestCategory
from apps.service_requests.services import RoundService, ServiceRequestService
from tests import factories as f

pytestmark = pytest.mark.django_db


@pytest.fixture
def request_with_files(world):
    return ServiceRequestService.submit(
        actor=world.tenant,
        prop=world.prop,
        unit=world.unit,
        title="Leak",
        description="Water everywhere",
        category=ServiceRequestCategory.OTHER,
        files=[f.png(), f.png()],
    )


def test_deleting_a_row_takes_its_own_files_with_it(world, request_with_files):
    sr = request_with_files
    assert AttachmentService.count(EntityType.SERVICE_REQUEST, sr.pk) == 2

    ServiceRequestService.delete(actor=world.manager, sr=sr)

    assert AttachmentService.count(EntityType.SERVICE_REQUEST, sr.pk) == 0


def test_deleting_a_row_takes_the_files_of_what_it_cascades(world, request_with_files):
    """The files of a round hang on the assignment, which the request cascades to."""
    sr = request_with_files
    RoundService.assign(actor=world.manager, sr=sr, resolvers=[world.maintenance])
    RoundService.resolve(actor=world.maintenance, sr=sr, files=[f.png()])
    assert Attachment.objects.filter(entity_type=EntityType.SERVICE_REQUEST_RESOLUTION).exists()

    ServiceRequestService.delete(actor=world.manager, sr=sr)

    assert not Attachment.objects.filter(entity_type=EntityType.SERVICE_REQUEST_RESOLUTION).exists()


def test_deleting_a_row_takes_the_notification_traces_pointing_at_it(world, request_with_files):
    sr = request_with_files
    reference = {"content_type__model": "servicerequest", "object_id": sr.pk}
    assert InboxNotification.objects.filter(**reference).exists()

    ServiceRequestService.delete(actor=world.manager, sr=sr)

    assert not InboxNotification.objects.filter(**reference).exists()
    assert not RecipientSnapshot.objects.filter(**reference).exists()


def test_a_row_deleted_through_the_orm_directly_leaves_its_files_orphaned(
    world, request_with_files
):
    """The cleanup lives in the service, not on the model: bypassing it (raw ORM,
    an admin action, a cascade from elsewhere) leaves files behind, later
    reclaimed by `purge_orphan_attachments`. Callers delete through the service."""
    sr = request_with_files

    ServiceRequest.objects.filter(pk=sr.pk).delete()

    assert AttachmentService.count(EntityType.SERVICE_REQUEST, sr.pk) == 2


def test_attach_one_fills_the_single_slot_of_an_entity(world):
    first = AttachmentService.attach_one(
        entity_type=EntityType.PROPERTY_LOGO,
        entity_id=world.prop.pk,
        upload=f.png(),
        uploaded_by=world.admin,
    )
    second = AttachmentService.attach_one(
        entity_type=EntityType.PROPERTY_LOGO,
        entity_id=world.prop.pk,
        upload=f.png(),
        uploaded_by=world.admin,
    )

    assert first.pk != second.pk
    assert AttachmentService.count(EntityType.PROPERTY_LOGO, world.prop.pk) == 1
