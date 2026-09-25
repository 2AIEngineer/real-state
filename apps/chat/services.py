"""Asynchronous, context-bound conversations.

A room belongs to exactly one business object (service request, booking or
order). Participants are never stored: they are derived from that object —
its initiator on one side, the staff in charge on the other.
"""

from __future__ import annotations

import datetime as dt

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Count, DateTimeField, F, OuterRef, Q, QuerySet, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.chat import notices
from apps.chat.contexts import CONTEXTS, context_of, load_context
from apps.chat.models import ChatMessage, ChatReadMarker, ChatRoom
from apps.chat.policies import ChatPolicy
from apps.common.attachments.rules import EntityType
from apps.common.attachments.service import AttachmentService
from apps.common.deletion import destroy
from apps.common.exceptions import InvalidInput, NotFound, PermissionDenied
from apps.properties.enums import Feature
from apps.properties.models import Property
from apps.properties.services import FeatureGate

User = get_user_model()

MAX_BODY_LENGTH = 4000
NEVER_READ = dt.datetime(1970, 1, 1, tzinfo=dt.UTC)


class ChatService:
    @staticmethod
    @transaction.atomic
    def open_room(*, actor, kind: str, object_id: int) -> ChatRoom:
        """Idempotent: returns the room of the context, creating it on first use."""
        ctx = load_context(kind, object_id)
        if ctx is None or not ChatPolicy.can_participate(actor, ctx):
            raise NotFound("Conversation context not found.")
        FeatureGate.require(ctx.prop, Feature.CHAT)
        existing = ChatRoom.objects.filter(**{kind: ctx.obj}).first()
        if existing:
            return existing
        try:
            with transaction.atomic():
                return ChatRoom.objects.create(property=ctx.prop, **{kind: ctx.obj})
        except IntegrityError:
            # Another participant opened it concurrently.
            return ChatRoom.objects.get(**{kind: ctx.obj})

    @staticmethod
    def _base_rooms() -> QuerySet[ChatRoom]:
        related = [path for spec in CONTEXTS.values() for path in spec.select_related]
        return ChatRoom.objects.select_related(*related)

    @staticmethod
    def list_rooms(*, actor, property_id: int) -> QuerySet[ChatRoom]:
        visible = ChatPolicy.visible_rooms_filter(actor)
        marker = ChatReadMarker.objects.filter(chat_room=OuterRef("pk"), user=actor).values(
            "last_read_at"
        )[:1]
        qs = (
            ChatService._base_rooms()
            .filter(visible)
            .distinct()
            .annotate(
                unread_count=Count(
                    "messages",
                    filter=~Q(messages__sender=actor)
                    & Q(
                        messages__created_at__gt=Coalesce(
                            Subquery(marker), Value(NEVER_READ, output_field=DateTimeField())
                        )
                    ),
                    distinct=True,
                )
            )
        )
        qs = qs.filter(property_id=property_id)
        return qs.order_by(F("last_message_at").desc(nulls_last=True), "-id")

    @staticmethod
    def unread_count(*, user, room: ChatRoom) -> int:
        """Messages from others posted since the user last read the room."""
        marker = (
            ChatReadMarker.objects.filter(chat_room=room, user=user)
            .values_list("last_read_at", flat=True)
            .first()
        )
        return (
            room.messages.exclude(sender=user).filter(created_at__gt=marker or NEVER_READ).count()
        )

    @staticmethod
    def get_room(*, actor, prop: Property, room_id: int) -> ChatRoom:
        room = ChatService._base_rooms().filter(pk=room_id, property=prop).first()
        if room is None or not ChatPolicy.can_participate(actor, context_of(room)):
            raise NotFound("Conversation not found.")
        return room

    @staticmethod
    def get_message(*, actor, room: ChatRoom, message_id: int) -> ChatMessage:
        if not ChatPolicy.can_participate(actor, context_of(room)):
            raise NotFound("Conversation not found.")
        message = (
            ChatMessage.objects.filter(pk=message_id, chat_room=room)
            .select_related("sender")
            .first()
        )
        if message is None:
            raise NotFound("Message not found.")
        return message

    @staticmethod
    def messages(*, actor, room: ChatRoom, before_id: int | None = None) -> QuerySet[ChatMessage]:
        if not ChatPolicy.can_participate(actor, context_of(room)):
            raise NotFound("Conversation not found.")
        qs = (
            ChatMessage.objects.filter(chat_room=room)
            .select_related("sender")
            .order_by("-created_at", "-id")
        )
        if before_id:
            qs = qs.filter(id__lt=before_id)
        return qs

    @staticmethod
    @transaction.atomic
    def post(*, actor, room: ChatRoom, body: str = "", media=None) -> ChatMessage:
        ctx = context_of(room)
        if not ChatPolicy.can_participate(actor, ctx):
            raise NotFound("Conversation not found.")
        FeatureGate.require(ctx.prop, Feature.CHAT)
        body = (body or "").strip()
        if not body and media is None:
            raise InvalidInput("A message needs text or a file.", field="body")
        if len(body) > MAX_BODY_LENGTH:
            raise InvalidInput(
                f"Messages are limited to {MAX_BODY_LENGTH} characters.", field="body"
            )
        message = ChatMessage.objects.create(chat_room=room, sender=actor, body=body)
        if media is not None:
            # Chat rule: one file per message, png/jpeg/jpg/pdf only.
            AttachmentService.attach_one(
                entity_type=EntityType.CHAT_MESSAGE,
                entity_id=message.pk,
                upload=media,
                uploaded_by=actor,
            )
        ChatRoom.objects.filter(pk=room.pk).update(
            last_message_at=message.created_at, updated_at=timezone.now()
        )
        ChatReadMarker.objects.update_or_create(
            chat_room=room, user=actor, defaults={"last_read_at": message.created_at}
        )

        notices.message_posted(message, ctx=ctx, actor=actor)
        return message

    @staticmethod
    @transaction.atomic
    def edit_message(*, actor, message: ChatMessage, body: str) -> ChatMessage:
        """Only the author rewrites their own message; the edit is visible."""
        ctx = context_of(message.chat_room)
        if not ChatPolicy.can_participate(actor, ctx):
            raise NotFound("Message not found.")
        if not ChatPolicy.can_edit_message(actor, message):
            raise PermissionDenied("Only the author can edit a message.")
        body = (body or "").strip()
        if not body and not AttachmentService.count(EntityType.CHAT_MESSAGE, message.pk):
            raise InvalidInput("A message needs text or a file.", field="body")
        if len(body) > MAX_BODY_LENGTH:
            raise InvalidInput(
                f"Messages are limited to {MAX_BODY_LENGTH} characters.", field="body"
            )
        message.body = body
        message.edited_at = timezone.now()
        message.save(update_fields=["body", "edited_at"])
        return message

    @staticmethod
    @transaction.atomic
    def delete_message(*, actor, message: ChatMessage) -> None:
        """A sender removes their own message; management removes any."""
        ctx = context_of(message.chat_room)
        if not ChatPolicy.can_participate(actor, ctx):
            raise NotFound("Message not found.")
        if not ChatPolicy.can_delete_message(actor, message, ctx):
            raise PermissionDenied(
                "Only the sender or the property management can delete this message."
            )
        destroy(message)

    @staticmethod
    @transaction.atomic
    def mark_read(*, actor, room: ChatRoom) -> None:
        if not ChatPolicy.can_participate(actor, context_of(room)):
            raise NotFound("Conversation not found.")
        ChatReadMarker.objects.update_or_create(
            chat_room=room, user=actor, defaults={"last_read_at": timezone.now()}
        )
