from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.common.models import EntityType
from apps.common.serializers import UserSummarySerializer
from apps.common.serializers.attachments import AttachmentsField
from apps.properties.enums import Feature
from apps.properties.models import (
    FEATURE_FLAG_FIELDS,
    Building,
    OwnershipEndReason,
    Promoter,
    Property,
    Syndicat,
    Unit,
    UnitOwnership,
    UnitType,
)

# ----------------------------------------------------------------------------- output


class SyndicatSerializer(serializers.ModelSerializer):
    logo = AttachmentsField(EntityType.SYNDICAT_LOGO, single=True)

    class Meta:
        model = Syndicat
        fields = [
            "id",
            "name",
            "legal_name",
            "registration_number",
            "contact_email",
            "contact_phone",
            "address",
            "city",
            "country",
            "is_active",
            "logo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PromoterSerializer(serializers.ModelSerializer):
    representative_user = UserSummarySerializer(read_only=True)

    class Meta:
        model = Promoter
        fields = [
            "id",
            "name",
            "legal_name",
            "registration_number",
            "contact_email",
            "contact_phone",
            "address",
            "representative_user",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


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
            "is_active",
            "features",
            "logo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_features(self, obj) -> dict[str, bool]:
        return {feature: getattr(obj, flag) for feature, flag in FEATURE_FLAG_FIELDS.items()}


class BuildingSerializer(serializers.ModelSerializer):
    units_count = serializers.SerializerMethodField()

    class Meta:
        model = Building
        fields = [
            "id",
            "property",
            "name",
            "address",
            "floors_count",
            "description",
            "units_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_units_count(self, obj) -> int:
        # Lists annotate it in one query; single objects count on the spot.
        annotated = getattr(obj, "units_count", None)
        return annotated if annotated is not None else obj.units.count()


class UnitSerializer(serializers.ModelSerializer):
    property = serializers.IntegerField(source="building.property_id", read_only=True)

    class Meta:
        model = Unit
        fields = [
            "id",
            "building",
            "property",
            "number",
            "label",
            "floor",
            "unit_type",
            "area_sqm",
            "rooms_count",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class OwnershipSerializer(serializers.ModelSerializer):
    owner = UserSummarySerializer(read_only=True)
    # Empty while the ownership is active.
    end_reason = serializers.ChoiceField(
        choices=OwnershipEndReason.choices, allow_blank=True, read_only=True
    )

    class Meta:
        model = UnitOwnership
        fields = [
            "id",
            "unit",
            "owner",
            "ownership_share",
            "start_date",
            "end_date",
            "status",
            "is_promoter_default",
            "end_reason",
            "acquisition_reference",
            "created_at",
        ]
        read_only_fields = fields


# ----------------------------------------------------------------------------- input


class SyndicatInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    registration_number = serializers.CharField(max_length=64, required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    country = serializers.CharField(max_length=120, required=False, allow_blank=True)


@extend_schema_serializer(component_name="Syndicat")
class SyndicatUpdateSerializer(SyndicatInputSerializer):
    name = serializers.CharField(max_length=200, required=False)
    is_active = serializers.BooleanField(required=False)


class PromoterInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    representative_email = serializers.EmailField()
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    registration_number = serializers.CharField(max_length=64, required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)


@extend_schema_serializer(component_name="Promoter")
class PromoterUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    registration_number = serializers.CharField(max_length=64, required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)


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
    is_active = serializers.BooleanField(required=False)


class PromoterChangeSerializer(serializers.Serializer):
    promoter_id = serializers.IntegerField(min_value=1)
    effective_date = serializers.DateField()


class BuildingInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    address = serializers.CharField(required=False, allow_blank=True)
    floors_count = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True)


@extend_schema_serializer(component_name="Building")
class BuildingUpdateSerializer(BuildingInputSerializer):
    name = serializers.CharField(max_length=120, required=False)


class UnitInputSerializer(serializers.Serializer):
    number = serializers.CharField(max_length=32)
    label = serializers.CharField(max_length=120, required=False, allow_blank=True)
    floor = serializers.IntegerField(min_value=-20, max_value=300, required=False, allow_null=True)
    unit_type = serializers.ChoiceField(choices=UnitType.choices, required=False)
    area_sqm = serializers.DecimalField(
        max_digits=8, decimal_places=2, min_value=0, required=False, allow_null=True
    )
    rooms_count = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)


@extend_schema_serializer(component_name="Unit")
class UnitUpdateSerializer(UnitInputSerializer):
    number = serializers.CharField(max_length=32, required=False)


class OwnershipAcquirerSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    share = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True, default=None
    )


class OwnershipTransferSerializer(serializers.Serializer):
    acquirers = OwnershipAcquirerSerializer(many=True, allow_empty=False)
    effective_date = serializers.DateField()
    reference = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")


class OwnershipCoOwnerSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    share = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True, default=None
    )
    start_date = serializers.DateField()


class OwnershipEndSerializer(serializers.Serializer):
    end_date = serializers.DateField()
    reason = serializers.ChoiceField(
        choices=[OwnershipEndReason.DEPARTURE, OwnershipEndReason.CORRECTION],
        default=OwnershipEndReason.DEPARTURE,
    )


# ----------------------------------------------------------------------- ui config


class UIConfigSyndicatSerializer(serializers.ModelSerializer):
    """Step `syndicat`: the syndicats the signed-in user may open."""

    logo = AttachmentsField(EntityType.SYNDICAT_LOGO, single=True)
    accessible_properties_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Syndicat
        fields = ["id", "name", "city", "country", "logo", "accessible_properties_count"]
        read_only_fields = fields


class UIConfigPropertySerializer(serializers.ModelSerializer):
    """Step `property`: the properties reachable inside the chosen syndicat."""

    logo = AttachmentsField(EntityType.PROPERTY_LOGO, single=True)
    features = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = ["id", "syndicat", "name", "city", "country", "logo", "features"]
        read_only_fields = fields

    def get_features(self, obj) -> dict[str, bool]:
        return {feature: getattr(obj, flag) for feature, flag in FEATURE_FLAG_FIELDS.items()}


class UIConfigSearchQueryParamsSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, max_length=120)


class PropertyStatisticsSerializer(serializers.Serializer):
    buildings = serializers.IntegerField()
    units = serializers.IntegerField()
    units_leased = serializers.IntegerField()
    units_held_by_promoter = serializers.IntegerField()
