from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.amenities.models import Amenity, Booking, BookingMode, BookingStatus
from apps.common.attachments.rules import EntityType
from apps.common.attachments.serializers import AttachmentsField
from apps.common.serializers import UserSummarySerializer


class AmenitySerializer(serializers.ModelSerializer):
    images = AttachmentsField(EntityType.AMENITY)

    class Meta:
        model = Amenity
        fields = [
            "id",
            "property",
            "building",
            "name",
            "description",
            "location",
            "rules",
            "booking_mode",
            "capacity",
            "requires_approval",
            "opening_time",
            "closing_time",
            "min_duration_minutes",
            "max_duration_minutes",
            "max_advance_days",
            "fee",
            "security_fee",
            "hourly_price",
            "is_active",
            "images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AmenitySlotSerializer(serializers.ModelSerializer):
    """Availability view: occupancy only, no personal data."""

    class Meta:
        model = Booking
        fields = ["start_datetime", "end_datetime", "status", "party_size"]
        read_only_fields = fields


class BookingSerializer(serializers.ModelSerializer):
    booker = UserSummarySerializer(read_only=True)
    amenity_name = serializers.CharField(source="amenity.name", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "amenity",
            "amenity_name",
            "booker",
            "start_datetime",
            "end_datetime",
            "status",
            "party_size",
            "booker_note",
            "decision_note",
            "decided_at",
            "cancelled_at",
            "cancellation_reason",
            "completed_at",
            "created_at",
        ]
        read_only_fields = fields


class AmenityFieldsSerializer(serializers.Serializer):
    description = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(max_length=200, required=False, allow_blank=True)
    rules = serializers.CharField(required=False, allow_blank=True)
    booking_mode = serializers.ChoiceField(choices=BookingMode.choices, required=False)
    capacity = serializers.IntegerField(min_value=1, max_value=10000, required=False)
    requires_approval = serializers.BooleanField(required=False)
    opening_time = serializers.TimeField(required=False, allow_null=True)
    closing_time = serializers.TimeField(required=False, allow_null=True)
    min_duration_minutes = serializers.IntegerField(
        min_value=5, max_value=10080, required=False
    )
    max_duration_minutes = serializers.IntegerField(
        min_value=5, max_value=10080, required=False
    )
    max_advance_days = serializers.IntegerField(
        min_value=0, max_value=730, required=False
    )
    # Left out on creation: 0 (nothing to pay).
    fee = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False
    )
    security_fee = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False
    )
    hourly_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        help_text="Leave out or 0 for a free amenity.",
    )


class AmenityCreateSerializer(AmenityFieldsSerializer):
    building_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, default=None
    )
    name = serializers.CharField(max_length=120)


@extend_schema_serializer(component_name="Amenity")
class AmenityUpdateSerializer(AmenityFieldsSerializer):
    name = serializers.CharField(max_length=120, required=False)
    is_active = serializers.BooleanField(required=False)


class AmenitiesQueryParamsSerializer(serializers.Serializer):
    include_inactive = serializers.BooleanField(required=False, default=False)


class AmenityScheduleQueryParamsSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()

    def validate(self, attrs):
        if attrs["end"] <= attrs["start"]:
            raise serializers.ValidationError({"end": "Must be after start."})
        return attrs


class BookingCreateSerializer(serializers.Serializer):
    amenity_id = serializers.IntegerField(min_value=1)
    start_datetime = serializers.DateTimeField()
    end_datetime = serializers.DateTimeField()
    party_size = serializers.IntegerField(min_value=1, default=1)
    note = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=2000
    )


class BookingsQueryParamsSerializer(serializers.Serializer):
    amenity_id = serializers.IntegerField(min_value=1, required=False)
    status = serializers.ChoiceField(choices=BookingStatus.choices, required=False)
    mine = serializers.BooleanField(required=False, default=False)


class BookingDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    note = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=2000
    )
