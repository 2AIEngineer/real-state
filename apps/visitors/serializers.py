from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.common.attachments.rules import EntityType
from apps.common.attachments.serializers import AttachmentsField
from apps.common.serializers import UserSummarySerializer
from apps.visitors.models import Visitor, VisitStatus


class VisitorSerializer(serializers.ModelSerializer):
    registered_by = UserSummarySerializer(read_only=True)
    id_card = AttachmentsField(EntityType.VISITOR_ID_CARD, single=True)

    class Meta:
        model = Visitor
        fields = [
            "id",
            "property",
            "unit",
            "first_name",
            "last_name",
            "phone",
            "visit_reason",
            "vehicle_plate",
            "status",
            "arrived_at",
            "left_at",
            "denial_reason",
            "notes",
            "registered_by",
            "id_card",
            "created_at",
        ]
        read_only_fields = fields


@extend_schema_serializer(component_name="Visitor")
class VisitorUpdateSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    visit_reason = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    vehicle_plate = serializers.CharField(
        max_length=32, required=False, allow_blank=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)


@extend_schema_serializer(component_name="VisitorCreate")
class VisitorCreateSerializer(VisitorUpdateSerializer):
    unit_id = serializers.IntegerField(min_value=1)
    first_name = serializers.CharField(max_length=120)
    last_name = serializers.CharField(max_length=120)
    admitted = serializers.BooleanField(default=True)
    denial_reason = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=2000
    )
    id_card = serializers.FileField(required=False, allow_null=True, default=None)


class VisitorsQueryParamsSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField(min_value=1, required=False)
    status = serializers.ChoiceField(choices=VisitStatus.choices, required=False)
    since = serializers.DateTimeField(required=False)


class VisitorDepartureSerializer(serializers.Serializer):
    left_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
