from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.chat.contexts import CONTEXT_KINDS
from apps.chat.models import ChatMessage, ChatRoom
from apps.chat.services import ChatService
from apps.common.models import EntityType
from apps.common.serializers import UserSummarySerializer
from apps.common.serializers.attachments import AttachmentsField


class ChatRoomSerializer(serializers.ModelSerializer):
    context_type = serializers.SerializerMethodField()
    context_id = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "property",
            "context_type",
            "context_id",
            "last_message_at",
            "unread_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_unread_count(self, obj) -> int:
        """Messages from others since the viewer last read the room."""
        annotated = getattr(obj, "unread_count", None)
        if annotated is not None:
            return annotated
        return ChatService.unread_count(user=self.context["request"].user, room=obj)

    def get_context_type(self, obj) -> str:
        return next(kind for kind in CONTEXT_KINDS if getattr(obj, f"{kind}_id"))

    def get_context_id(self, obj) -> int:
        return getattr(obj, f"{self.get_context_type(obj)}_id")


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = UserSummarySerializer(read_only=True)
    media = AttachmentsField(EntityType.CHAT_MESSAGE, single=True)

    class Meta:
        model = ChatMessage
        fields = ["id", "chat_room", "sender", "body", "media", "created_at", "edited_at"]
        read_only_fields = fields


class ChatRoomOpenSerializer(serializers.Serializer):
    context_type = serializers.ChoiceField(choices=[(k, k) for k in CONTEXT_KINDS])
    context_id = serializers.IntegerField(min_value=1)


class ChatMessagesQueryParamsSerializer(serializers.Serializer):
    before_id = serializers.IntegerField(min_value=1, required=False)


@extend_schema_serializer(component_name="ChatMessage")
class ChatMessageEditSerializer(serializers.Serializer):
    body = serializers.CharField(allow_blank=True, trim_whitespace=True)


class ChatMessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(required=False, allow_blank=True, default="", trim_whitespace=True)
    media = serializers.FileField(required=False, allow_null=True, default=None)
