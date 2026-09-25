"""Properties, their plan (features) and statistics."""

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.common.attachments.rules import EntityType
from apps.common.attachments.serializers import AttachmentsField
from apps.properties import timezones
from apps.properties.enums import Feature
from apps.properties.models import (
    FEATURE_FLAG_FIELDS,
    Property,
)


class TimeZoneField(serializers.CharField):
    """An IANA time zone name, such as `Africa/Casablanca` or `America/Montreal`."""

    def __init__(self, **kwargs):
        super().__init__(max_length=64, **kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if not timezones.is_known(value):
            raise serializers.ValidationError(f"'{value}' is not a known IANA time zone.")
        return value


class PropertySerializer(serializers.ModelSerializer):
    features = serializers.SerializerMethodField()
    logo = AttachmentsField(EntityType.PROPERTY_LOGO, single=True)

    class Meta:
        model = Property
        fields = [
            "id",
            "syndicat",
            "promoter",
            "name",
            "description",
            "address",
            "city",
            "country",
            "contact_email",
            "contact_phone",
            "timezone",
            "is_active",
            "features",
            "logo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_features(self, obj) -> dict[str, bool]:
        return {feature: getattr(obj, flag) for feature, flag in FEATURE_FLAG_FIELDS.items()}


class PropertyFeaturesSerializer(serializers.Serializer):
    def get_fields(self):
        return {feature.value: serializers.BooleanField(required=False) for feature in Feature}


class PropertyInputSerializer(serializers.Serializer):
    syndicat_id = serializers.IntegerField(min_value=1)
    promoter_id = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    country = serializers.CharField(max_length=120, required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    timezone = TimeZoneField(required=False)
    features = PropertyFeaturesSerializer(required=False)


@extend_schema_serializer(component_name="Property")
class PropertyUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    country = serializers.CharField(max_length=120, required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    timezone = TimeZoneField(required=False)
    is_active = serializers.BooleanField(required=False)


class PropertyStatisticsSerializer(serializers.Serializer):
    buildings = serializers.IntegerField()
    units = serializers.IntegerField()
    units_leased = serializers.IntegerField()
    units_held_by_promoter = serializers.IntegerField()
