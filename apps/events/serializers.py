from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.accounts.enums import PropertyRole
from apps.common.files.rules import EntityType
from apps.common.files.serializers import AttachmentsField
from apps.common.serializers import UserSummarySerializer
from apps.events.models import Event, EventStatus


class EventSerializer(serializers.ModelSerializer):
    created_by = UserSummarySerializer(read_only=True)
    files = AttachmentsField(EntityType.EVENT)

    class Meta:
        model = Event
        fields = [
            "id",
            "property",
            "building",
            "title",
            "description",
            "location",
            "start_at",
            "end_at",
            "status",
            "target_roles",
            "cancelled_at",
            "cancellation_reason",
            "completed_at",
            "created_by",
            "files",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class EventCreateSerializer(serializers.Serializer):
    building_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, default=None
    )
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    location = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    target_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=PropertyRole.choices), allow_empty=False
    )
    files = serializers.ListField(child=serializers.FileField(), required=False, default=list)


@extend_schema_serializer(component_name="Event")
class EventUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(max_length=200, required=False, allow_blank=True)
    start_at = serializers.DateTimeField(required=False)
    end_at = serializers.DateTimeField(required=False)


class EventsQueryParamsSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=EventStatus.choices, required=False)
    starts_after = serializers.DateTimeField(required=False)
    starts_before = serializers.DateTimeField(required=False)
