from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class ChatRoom(TimeStampedModel):
    """Asynchronous thread attached to exactly one business context.

    One room per context object (the FKs are one-to-one); participants are
    derived from that context, never stored.
    """

    service_request = models.OneToOneField(
        "service_requests.ServiceRequest",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="chat_room",
    )
    booking = models.OneToOneField(
        "amenities.Booking",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="chat_room",
    )
    order = models.OneToOneField(
        "store.Order", null=True, blank=True, on_delete=models.CASCADE, related_name="chat_room"
    )
    property = models.ForeignKey(
        "properties.Property", on_delete=models.CASCADE, related_name="chat_rooms"
    )
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-last_message_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(service_request__isnull=False, booking__isnull=True, order__isnull=True)
                    | Q(service_request__isnull=True, booking__isnull=False, order__isnull=True)
                    | Q(service_request__isnull=True, booking__isnull=True, order__isnull=False)
                ),
                name="chat_room_exactly_one_context",
            ),
        ]

    def __str__(self) -> str:
        return f"ChatRoom #{self.pk}"


class ChatMessage(models.Model):
    """A message; its optional single media file is an Attachment (chat_media)."""

    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="chat_messages"
    )
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["chat_room", "created_at"])]

    def __str__(self) -> str:
        return f"Message #{self.pk} in room {self.chat_room_id}"


class ChatReadMarker(models.Model):
    """How far a participant has read a room (drives unread counters)."""

    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="read_markers")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    last_read_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["chat_room", "user"], name="unique_chat_read_marker")
        ]
