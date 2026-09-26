"""Promoters."""

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.common.serializers import UserSummarySerializer
from apps.properties.models import (
    Promoter,
)


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


class PromoterInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    representative_email = serializers.EmailField()
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    registration_number = serializers.CharField(
        max_length=64, required=False, allow_blank=True
    )
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(
        max_length=32, required=False, allow_blank=True
    )
    address = serializers.CharField(required=False, allow_blank=True)


@extend_schema_serializer(component_name="Promoter")
class PromoterUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    registration_number = serializers.CharField(
        max_length=64, required=False, allow_blank=True
    )
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(
        max_length=32, required=False, allow_blank=True
    )
    address = serializers.CharField(required=False, allow_blank=True)


class PromoterChangeSerializer(serializers.Serializer):
    promoter_id = serializers.IntegerField(min_value=1)
    effective_date = serializers.DateField()
