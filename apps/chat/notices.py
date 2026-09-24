"""What people are told about chat messages."""

from __future__ import annotations

from apps.chat.contexts import RoomContext, staff_of
from apps.chat.models import ChatMessage
from apps.notifications.models import NotificationCategory
from apps.notifications.services import NotificationIntent, NotificationService


def message_posted(message: ChatMessage, *, ctx: RoomContext, actor) -> None:
    """The initiator is told of a staff reply; the staff are told of the initiator's message."""
    from_initiator = ctx.initiator.pk == actor.pk
    preview = message.body[:140] if message.body else "Pièce jointe"
    NotificationService.notify(
        NotificationIntent(
            event_type="chat.message",
            category=NotificationCategory.CHAT,
            title=f"Nouveau message — {ctx.label}",
            body=f"{actor.get_full_name()} : {preview}",
            to=[] if from_initiator else [ctx.initiator],
            bcc=staff_of(ctx) if from_initiator else [],
            target=message,
            exclude=[actor],
            include_platform_admins=from_initiator,
            data={
                "chat_room_id": message.chat_room_id,
                "context_type": ctx.kind,
                "context_id": ctx.obj.pk,
            },
            action_path=f"/chat/{message.chat_room_id}",
        )
    )
