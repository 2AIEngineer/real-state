"""Syndicats."""

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.common.files.rules import EntityType
from apps.common.files.serializers import AttachmentsField
from apps.properties.models import (
    Syndicat,
)


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
