from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.accounts.enums import PropertyRole
from apps.announcements.models import Announcement, AnnouncementCategory, AnnouncementPriority
from apps.common.models import EntityType
from apps.common.serializers import UserSummarySerializer
from apps.common.serializers.attachments import AttachmentsField


class AnnouncementSerializer(serializers.ModelSerializer):
    created_by = UserSummarySerializer(read_only=True)
    files = AttachmentsField(EntityType.ANNOUNCEMENT)

    class Meta:
        model = Announcement
        fields = [
            "id",
            "property",
            "building",
            "title",
            "body",
            "category",
            "priority",
            "target_roles",
            "published_at",
            "expires_at",
            "created_by",
            "files",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AnnouncementCreateSerializer(serializers.Serializer):
    building_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, default=None
    )
    title = serializers.CharField(max_length=200)
    body = serializers.CharField()
    category = serializers.ChoiceField(
        choices=AnnouncementCategory.choices, default=AnnouncementCategory.GENERAL
    )
    priority = serializers.ChoiceField(
        choices=AnnouncementPriority.choices, default=AnnouncementPriority.NORMAL
    )
    target_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=PropertyRole.choices), allow_empty=False
    )
    published_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
    expires_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
    files = serializers.ListField(child=serializers.FileField(), required=False, default=list)


@extend_schema_serializer(component_name="Announcement")
class AnnouncementUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    body = serializers.CharField(required=False)
    category = serializers.ChoiceField(choices=AnnouncementCategory.choices, required=False)
    priority = serializers.ChoiceField(choices=AnnouncementPriority.choices, required=False)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class AnnouncementsQueryParamsSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=AnnouncementCategory.choices, required=False)
    include_expired = serializers.BooleanField(required=False, default=False)
