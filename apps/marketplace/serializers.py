from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.common.models import EntityType
from apps.common.serializers import UserSummarySerializer
from apps.common.serializers.attachments import AttachmentsField
from apps.marketplace.models import ListingCategory, ListingStatus, MarketplaceListing


class MarketplaceListingSerializer(serializers.ModelSerializer):
    seller = UserSummarySerializer(read_only=True)
    images = AttachmentsField(EntityType.MARKETPLACE_LISTING)

    class Meta:
        model = MarketplaceListing
        fields = [
            "id",
            "seller",
            "property",
            "category",
            "title",
            "description",
            "price",
            "currency",
            "is_negotiable",
            "location",
            "contact_phone",
            "contact_email",
            "status",
            "published_at",
            "closed_at",
            "images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class MarketplaceListingFieldsSerializer(serializers.Serializer):
    price = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=0, required=False, allow_null=True
    )
    currency = serializers.CharField(min_length=3, max_length=3, required=False)
    is_negotiable = serializers.BooleanField(required=False)
    location = serializers.CharField(max_length=200, required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)


class MarketplaceListingCreateSerializer(MarketplaceListingFieldsSerializer):
    category = serializers.ChoiceField(choices=ListingCategory.choices)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField()
    images = serializers.ListField(child=serializers.FileField(), allow_empty=False)


@extend_schema_serializer(component_name="MarketplaceListing")
class MarketplaceListingUpdateSerializer(MarketplaceListingFieldsSerializer):
    category = serializers.ChoiceField(choices=ListingCategory.choices, required=False)
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False)


class MarketplaceListingsQueryParamsSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=ListingCategory.choices, required=False)
    search = serializers.CharField(required=False, allow_blank=True, max_length=120)
    max_price = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    mine = serializers.BooleanField(required=False, default=False)
    status = serializers.ChoiceField(choices=ListingStatus.choices, required=False)


class MarketplaceListingModerationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)


class MarketplaceListingImagesSerializer(serializers.Serializer):
    images = serializers.ListField(child=serializers.FileField(), allow_empty=False)
