from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.common.models import EntityType
from apps.common.serializers import UserSummarySerializer
from apps.common.serializers.attachments import AttachmentsField
from apps.leasing.models import (
    CheckPhase,
    ComponentCondition,
    Lease,
    LeaseComponentState,
    LeaseMember,
    LeaseStatus,
    LeaseTerminationReason,
)

# ----------------------------------------------------------------------------- output


class LeaseMemberSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    proof_of_identity = AttachmentsField(EntityType.LEASE_MEMBER_IDENTITY, single=True)
    proof_of_address = AttachmentsField(EntityType.LEASE_MEMBER_ADDRESS, single=True)
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = LeaseMember
        fields = [
            "id",
            "lease",
            "user",
            "joined_at",
            "left_at",
            "is_active",
            "is_signatory",
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relation",
            "vehicles_info",
            "pets_info",
            "proof_of_identity",
            "proof_of_address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_is_active(self, obj) -> bool:
        return obj.left_at is None


class LeaseSerializer(serializers.ModelSerializer):
    members = LeaseMemberSerializer(many=True, read_only=True)
    # Empty while the lease is running.
    termination_reason = serializers.ChoiceField(
        choices=LeaseTerminationReason.choices, allow_blank=True, read_only=True
    )
    property = serializers.IntegerField(source="unit.building.property_id", read_only=True)

    class Meta:
        model = Lease
        fields = [
            "id",
            "unit",
            "property",
            "start_date",
            "end_date",
            "status",
            "contract_reference",
            "notes",
            "terminated_on",
            "termination_reason",
            "cancelled_at",
            "cancellation_reason",
            "members",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class LeaseComponentStateSerializer(serializers.ModelSerializer):
    files = AttachmentsField(EntityType.LEASE_COMPONENT_STATE)

    class Meta:
        model = LeaseComponentState
        fields = [
            "id",
            "lease",
            "name",
            "description",
            "state",
            "on_check",
            "on_check_date",
            "recorded_by",
            "files",
            "created_at",
        ]
        read_only_fields = fields


# ----------------------------------------------------------------------------- input


class LeaseMemberVehicleSerializer(serializers.Serializer):
    plate_number = serializers.CharField(max_length=32)
    make = serializers.CharField(max_length=60, required=False, allow_blank=True)
    model = serializers.CharField(max_length=60, required=False, allow_blank=True)
    color = serializers.CharField(max_length=30, required=False, allow_blank=True)
    parking_spot = serializers.CharField(max_length=30, required=False, allow_blank=True)


class LeaseMemberPetSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=60)
    species = serializers.CharField(max_length=60)
    breed = serializers.CharField(max_length=60, required=False, allow_blank=True)


class LeaseMemberExtrasSerializer(serializers.Serializer):
    emergency_contact_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    emergency_contact_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    emergency_contact_relation = serializers.CharField(
        max_length=80, required=False, allow_blank=True
    )
    vehicles_info = LeaseMemberVehicleSerializer(many=True, required=False)
    pets_info = LeaseMemberPetSerializer(many=True, required=False)


class LeaseMemberInputSerializer(LeaseMemberExtrasSerializer):
    user_id = serializers.IntegerField(min_value=1)
    is_signatory = serializers.BooleanField(default=False)
    joined_at = serializers.DateField(required=False, allow_null=True, default=None)


class LeaseCreateSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField(min_value=1)
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True, default=None)
    contract_reference = serializers.CharField(
        max_length=120, required=False, allow_blank=True, allow_null=True, default=None
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    members = LeaseMemberInputSerializer(many=True, allow_empty=False)


@extend_schema_serializer(component_name="Lease")
class LeaseUpdateSerializer(serializers.Serializer):
    end_date = serializers.DateField(required=False, allow_null=True)
    contract_reference = serializers.CharField(
        max_length=120, required=False, allow_blank=True, allow_null=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class LeasesQueryParamsSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField(required=False, min_value=1)
    status = serializers.ChoiceField(choices=LeaseStatus.choices, required=False)


class LeaseTerminationSerializer(serializers.Serializer):
    effective_date = serializers.DateField()
    reason = serializers.ChoiceField(
        choices=LeaseTerminationReason.choices, default=LeaseTerminationReason.OTHER
    )


class LeaseMemberDepartureSerializer(serializers.Serializer):
    left_at = serializers.DateField()


@extend_schema_serializer(component_name="LeaseMember")
class LeaseMemberUpdateSerializer(LeaseMemberExtrasSerializer):
    is_signatory = serializers.BooleanField(required=False)


class LeaseComponentStateInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    state = serializers.ChoiceField(choices=ComponentCondition.choices)
    on_check = serializers.ChoiceField(choices=CheckPhase.choices)
    on_check_date = serializers.DateField()
    files = serializers.ListField(child=serializers.FileField(), required=False, default=list)


@extend_schema_serializer(component_name="LeaseComponentState")
class LeaseComponentStateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    state = serializers.ChoiceField(choices=ComponentCondition.choices, required=False)
    on_check_date = serializers.DateField(required=False)
