"""The ownership register of units."""

from rest_framework import serializers

from apps.common.serializers import UserSummarySerializer
from apps.properties.models import (
    OwnershipEndReason,
    UnitOwnership,
)


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


class OwnershipAcquirerSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    share = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True, default=None
    )


class OwnershipTransferSerializer(serializers.Serializer):
    acquirers = OwnershipAcquirerSerializer(many=True, allow_empty=False)
    effective_date = serializers.DateField()
    reference = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )


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
