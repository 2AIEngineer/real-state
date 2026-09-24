from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.common.files.rules import EntityType
from apps.common.files.serializers import AttachmentsField
from apps.common.serializers import UserSummarySerializer
from apps.short_term_rental.models import (
    Gender,
    ShortTermRental,
    ShortTermRentalMember,
    ShortTermRentalStatus,
)


class ShortTermRentalMemberSerializer(serializers.ModelSerializer):
    id_card = AttachmentsField(EntityType.SHORT_TERM_RENTAL_MEMBER_ID_CARD, single=True)

    class Meta:
        model = ShortTermRentalMember
        fields = [
            "id",
            "short_term_rental",
            "first_name",
            "last_name",
            "gender",
            "date_of_birth",
            "nationality",
            "id_document_number",
            "phone",
            "email",
            "id_card",
            "created_at",
        ]
        read_only_fields = fields


class ShortTermRentalSerializer(serializers.ModelSerializer):
    initiated_by = UserSummarySerializer(read_only=True)
    members = ShortTermRentalMemberSerializer(many=True, read_only=True)

    class Meta:
        model = ShortTermRental
        fields = [
            "id",
            "unit",
            "initiated_by",
            "initiator_capacity",
            "lease",
            "checkin_date",
            "checkout_date",
            "status",
            "primary_member",
            "members",
            "notes",
            "checked_in_at",
            "completed_at",
            "cancelled_at",
            "cancellation_reason",
            "created_at",
        ]
        read_only_fields = fields


class ShortTermRentalMemberInputSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=120)
    last_name = serializers.CharField(max_length=120)
    gender = serializers.ChoiceField(choices=Gender.choices, required=False)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    nationality = serializers.CharField(max_length=80, required=False, allow_blank=True)
    id_document_number = serializers.CharField(max_length=64, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)


class ShortTermRentalMemberCreateSerializer(ShortTermRentalMemberInputSerializer):
    make_primary = serializers.BooleanField(required=False, default=False)


@extend_schema_serializer(component_name="ShortTermRentalMember")
class ShortTermRentalMemberUpdateSerializer(ShortTermRentalMemberCreateSerializer):
    first_name = serializers.CharField(max_length=120, required=False)
    last_name = serializers.CharField(max_length=120, required=False)


class ShortTermRentalCreateSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField(min_value=1)
    checkin_date = serializers.DateField()
    checkout_date = serializers.DateField()
    notes = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)
    members = ShortTermRentalMemberInputSerializer(many=True, allow_empty=False)
    primary_index = serializers.IntegerField(min_value=0, default=0)


class ShortTermRentalRescheduleSerializer(serializers.Serializer):
    checkin_date = serializers.DateField()
    checkout_date = serializers.DateField()


class ShortTermRentalsQueryParamsSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField(min_value=1, required=False)
    status = serializers.ChoiceField(choices=ShortTermRentalStatus.choices, required=False)
