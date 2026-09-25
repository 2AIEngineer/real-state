"""`destroy` reaches every row a deletion cascades to, and cleans their files and notifications."""

import pytest

from apps.chat.services import ChatService
from apps.common.attachments.rules import EntityType
from apps.common.attachments.service import AttachmentService
from apps.common.deletion import destroy
from apps.common.models import Attachment
from apps.notifications.models import InboxNotification
from apps.service_requests.services import ServiceRequestService
from tests import factories as f

pytestmark = pytest.mark.django_db


def test_deleting_a_property_cleans_files_and_notifications_three_levels_down(world):
    sr = ServiceRequestService.submit(
        actor=world.tenant,
        prop=world.prop,
        title="Leak",
        description="d",
        category="plumbing",
        files=[f.png()],
    )
    room = ChatService.open_room(actor=world.tenant, kind="service_request", object_id=sr.pk)
    message = ChatService.post(actor=world.tenant, room=room, body="Photo", media=f.png())
    assert InboxNotification.objects.exists()
    AttachmentService.attach(
        entity_type=EntityType.PROPERTY_LOGO,
        entity_id=world.prop.pk,
        files=[f.png()],
        uploaded_by=world.admin,
    )

    destroy(world.prop)

    assert not Attachment.objects.filter(entity_type=EntityType.SERVICE_REQUEST).exists()
    assert not Attachment.objects.filter(
        entity_type=EntityType.CHAT_MESSAGE, entity_id=message.pk
    ).exists()
    assert not Attachment.objects.filter(entity_type=EntityType.PROPERTY_LOGO).exists()
    assert not InboxNotification.objects.filter(object_id=sr.pk).exists()
