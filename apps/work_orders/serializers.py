from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.common.attachments.rules import EntityType
from apps.common.attachments.serializers import AttachmentsField
from apps.common.serializers import UserSummarySerializer
from apps.work_orders.models import WorkOrder, WorkOrderCategory, WorkOrderPriority, WorkOrderStatus


class WorkOrderSerializer(serializers.ModelSerializer):
    assignee = UserSummarySerializer(read_only=True, allow_null=True)
    files = AttachmentsField(EntityType.WORK_ORDER)

    class Meta:
        model = WorkOrder
        fields = [
            "id",
            "property",
            "building",
            "unit",
            "service_request",
            "title",
            "description",
            "category",
            "priority",
            "status",
            "assignee",
            "scheduled_start",
            "scheduled_end",
            "due_date",
            "started_at",
            "completed_at",
            "completion_note",
            "cancelled_at",
            "cancellation_reason",
            "files",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class WorkOrderFieldsSerializer(serializers.Serializer):
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.ChoiceField(choices=WorkOrderCategory.choices, required=False)
    priority = serializers.ChoiceField(choices=WorkOrderPriority.choices, required=False)
    scheduled_start = serializers.DateTimeField(required=False, allow_null=True)
    scheduled_end = serializers.DateTimeField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)


class WorkOrderCreateSerializer(WorkOrderFieldsSerializer):
    building_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, default=None
    )
    unit_id = serializers.IntegerField(min_value=1, required=False, allow_null=True, default=None)
    service_request_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, default=None
    )
    assignee_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, default=None
    )
    title = serializers.CharField(max_length=200)
    files = serializers.ListField(child=serializers.FileField(), required=False, default=list)


@extend_schema_serializer(component_name="WorkOrder")
class WorkOrderUpdateSerializer(WorkOrderFieldsSerializer):
    title = serializers.CharField(max_length=200, required=False)
    assignee_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class WorkOrdersQueryParamsSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=WorkOrderStatus.choices, required=False)
    assigned_to_me = serializers.BooleanField(required=False, default=False)


class WorkOrderTransitionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["start", "hold", "complete", "cancel"])
    note = serializers.CharField(required=False, allow_blank=True, default="", max_length=4000)
