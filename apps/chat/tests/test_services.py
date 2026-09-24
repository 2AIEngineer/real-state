import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.chat.services import ChatService
from apps.common.exceptions import InvalidInput, NotFound
from apps.notifications.models import InboxNotification
from apps.service_requests.models import ServiceRequestCategory
from apps.service_requests.services import ServiceRequestService
from tests import factories as f

pytestmark = pytest.mark.django_db


@pytest.fixture
def room(world):
    sr = ServiceRequestService.submit(
        actor=world.tenant,
        prop=world.prop,
        unit=world.unit,
        title="Leak",
        description="...",
        category=ServiceRequestCategory.PLUMBING,
    )
    return ChatService.open_room(actor=world.tenant, kind="service_request", object_id=sr.pk)


def test_opening_is_idempotent(world, room):
    again = ChatService.open_room(
        actor=world.manager, kind="service_request", object_id=room.service_request_id
    )
    assert again.pk == room.pk


def test_participants_are_derived_from_the_context(world, room):
    with pytest.raises(NotFound):
        ChatService.get_room(actor=world.co_tenant, room_id=room.pk)
    assert ChatService.get_room(actor=world.syndic, room_id=room.pk) == room


def test_messages_cross_between_initiator_and_staff(world, room):
    ChatService.post(actor=world.tenant, room=room, body="Any news?")
    assert InboxNotification.objects.filter(
        notification_type="chat.message", user=world.manager
    ).exists()
    assert not InboxNotification.objects.filter(
        notification_type="chat.message", user=world.tenant
    ).exists()
    ChatService.post(actor=world.manager, room=room, body="Plumber comes tomorrow")
    assert InboxNotification.objects.filter(
        notification_type="chat.message", user=world.tenant
    ).exists()


def test_media_rules(world, room):
    message = ChatService.post(actor=world.tenant, room=room, media=f.pdf())
    assert message.body == ""
    gif = SimpleUploadedFile("a.gif", b"GIF89a" + b"\x00" * 20)
    with pytest.raises(InvalidInput):
        ChatService.post(actor=world.tenant, room=room, media=gif)
    with pytest.raises(InvalidInput):
        ChatService.post(actor=world.tenant, room=room, body="   ")


def test_unread_counter(world, room):
    ChatService.post(actor=world.tenant, room=room, body="Hello")
    ChatService.post(actor=world.tenant, room=room, body="Hello?")
    listed = ChatService.list_rooms(actor=world.manager, property_id=world.prop.pk).get(pk=room.pk)
    assert listed.unread_count == 2
    ChatService.mark_read(actor=world.manager, room=room)
    assert (
        ChatService.list_rooms(actor=world.manager, property_id=world.prop.pk)
        .get(pk=room.pk)
        .unread_count
        == 0
    )
    assert (
        ChatService.list_rooms(actor=world.tenant, property_id=world.prop.pk)
        .get(pk=room.pk)
        .unread_count
        == 0
    )


def test_author_edits_their_message(world, room):
    message = ChatService.post(actor=world.tenant, room=room, body="Typo")
    edited = ChatService.edit_message(actor=world.tenant, message=message, body="Fixed")
    assert edited.body == "Fixed" and edited.edited_at is not None
    from apps.common.exceptions import PermissionDenied

    with pytest.raises(PermissionDenied):  # management may delete, never rewrite
        ChatService.edit_message(actor=world.manager, message=message, body="Rewritten")


def test_edited_message_still_needs_content(world, room):
    message = ChatService.post(actor=world.tenant, room=room, body="Something")
    with pytest.raises(InvalidInput):
        ChatService.edit_message(actor=world.tenant, message=message, body="   ")


def test_a_message_reduced_to_its_media_stays_valid(world, room):
    message = ChatService.post(actor=world.tenant, room=room, body="See photo", media=f.png())
    assert ChatService.edit_message(actor=world.tenant, message=message, body="").body == ""


def test_every_conversation_context_has_its_room_field():
    """One entry of `CONTEXTS` per one-to-one field of `ChatRoom`, and no other."""
    from django.db.models import OneToOneField

    from apps.chat.contexts import CONTEXTS
    from apps.chat.models import ChatRoom

    room_fields = {
        field.name for field in ChatRoom._meta.get_fields() if isinstance(field, OneToOneField)
    }
    assert set(CONTEXTS) == room_fields
