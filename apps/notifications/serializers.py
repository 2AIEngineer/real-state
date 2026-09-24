"""Serializers of the notifications module (shape validation only)."""

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.notifications.models import (
    ExpoPushToken,
    InboxNotification,
    NotificationCategory,
    NotificationPreference,
)
from apps.notifications.services.preferences import PREFERENCE_FIELDS


class InboxNotificationSerializer(serializers.ModelSerializer):
    target_type = serializers.SerializerMethodField()

    class Meta:
        model = InboxNotification
        fields = [
            "id",
            "category",
            "notification_type",
            "severity",
            "title",
            "body",
            "data",
            "target_type",
            "object_id",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_target_type(self, obj) -> str | None:
        return (
            f"{obj.content_type.app_label}.{obj.content_type.model}"
            if obj.content_type_id
            else None
        )


class NotificationsQueryParamsSerializer(serializers.Serializer):
    unread = serializers.BooleanField(required=False, default=False)
    category = serializers.ChoiceField(choices=NotificationCategory.choices, required=False)


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = list(PREFERENCE_FIELDS)


@extend_schema_serializer(component_name="NotificationPreference")
class NotificationPreferenceUpdateSerializer(serializers.Serializer):
    def get_fields(self):
        return {name: serializers.BooleanField(required=False) for name in PREFERENCE_FIELDS}


class PushTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpoPushToken
        fields = [
            "device_id",
            "expo_push_token",
            "platform",
            "is_active",
            "created_at",
            "last_seen_at",
        ]
        read_only_fields = ["is_active", "created_at", "last_seen_at"]


class PushTokenRegisterSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=191)
    expo_push_token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(
        choices=[("ios", "iOS"), ("android", "Android"), ("web", "Web")], required=False, default=""
    )


class NotificationUnreadCountSerializer(serializers.Serializer):
    unread = serializers.IntegerField()


class NotificationsMarkedReadSerializer(serializers.Serializer):
    updated = serializers.IntegerField(help_text="Number of notifications marked as read.")
