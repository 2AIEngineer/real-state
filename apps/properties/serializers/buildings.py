"""Buildings and units."""

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.properties.models import (
    Building,
    Unit,
    UnitType,
)


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


class BuildingInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    address = serializers.CharField(required=False, allow_blank=True)
    floors_count = serializers.IntegerField(
        min_value=0, required=False, allow_null=True
    )
    description = serializers.CharField(required=False, allow_blank=True)


@extend_schema_serializer(component_name="Building")
class BuildingUpdateSerializer(BuildingInputSerializer):
    name = serializers.CharField(max_length=120, required=False)


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


class UnitInputSerializer(serializers.Serializer):
    number = serializers.CharField(max_length=32)
    label = serializers.CharField(max_length=120, required=False, allow_blank=True)
    floor = serializers.IntegerField(
        min_value=-20, max_value=300, required=False, allow_null=True
    )
    unit_type = serializers.ChoiceField(choices=UnitType.choices, required=False)
    area_sqm = serializers.DecimalField(
        max_digits=8, decimal_places=2, min_value=0, required=False, allow_null=True
    )
    rooms_count = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)


@extend_schema_serializer(component_name="Unit")
class UnitUpdateSerializer(UnitInputSerializer):
    number = serializers.CharField(max_length=32, required=False)
