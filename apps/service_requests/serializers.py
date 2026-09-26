from rest_framework import serializers

from apps.common.attachments.rules import EntityType
from apps.common.attachments.serializers import AttachmentsField
from apps.common.serializers import UserSummarySerializer
from apps.service_requests.models import (
    RequesterNotice,
    ServiceRequest,
    ServiceRequestAssignment,
    ServiceRequestCategory,
    ServiceRequestPriority,
    ServiceRequestStatus,
)


class ServiceRequestAssignmentSerializer(serializers.ModelSerializer):
    resolver = UserSummarySerializer(read_only=True)
    resolution_media = AttachmentsField(EntityType.SERVICE_REQUEST_RESOLUTION)

    class Meta:
        model = ServiceRequestAssignment
        fields = [
            "id",
            "resolver",
            "resolution_round",
            "assigned_by",
            "is_resolved",
            "resolved_at",
            "resolution_note",
            "resolution_media",
            "requester_notice",
            "requester_rating",
            "requester_comment",
            "feedback_at",
            "created_at",
        ]
        read_only_fields = fields


class ServiceRequestSerializer(serializers.ModelSerializer):
    requester = UserSummarySerializer(read_only=True)
    files = AttachmentsField(EntityType.SERVICE_REQUEST)

    class Meta:
        model = ServiceRequest
        fields = [
            "id",
            "property",
            "unit",
            "requester",
            "title",
            "description",
            "category",
            "priority",
            "status",
            "current_round",
            "resolved_at",
            "closed_at",
            "cancelled_at",
            "cancellation_reason",
            "files",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ServiceRequestCreateSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, default=None
    )
    title = serializers.CharField(max_length=200)
    description = serializers.CharField()
    category = serializers.ChoiceField(
        choices=ServiceRequestCategory.choices, default=ServiceRequestCategory.OTHER
    )
    priority = serializers.ChoiceField(
        choices=ServiceRequestPriority.choices, default=ServiceRequestPriority.MEDIUM
    )
    files = serializers.ListField(
        child=serializers.FileField(), required=False, default=list
    )


class ServiceRequestsQueryParamsSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=ServiceRequestStatus.choices, required=False
    )
    mine = serializers.BooleanField(required=False, default=False)


class ServiceRequestAssignSerializer(serializers.Serializer):
    resolver_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False, max_length=10
    )


class ServiceRequestResolveSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")
    files = serializers.ListField(
        child=serializers.FileField(), required=False, default=list
    )


class ServiceRequestFeedbackSerializer(serializers.Serializer):
    notice = serializers.ChoiceField(choices=RequesterNotice.choices)
    rating = serializers.IntegerField(
        min_value=1, max_value=5, required=False, allow_null=True, default=None
    )
    comment = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=2000
    )
