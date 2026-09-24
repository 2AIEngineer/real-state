"""The UI configuration path: syndicats and properties the account may open."""

from rest_framework import serializers

from apps.common.files.rules import EntityType
from apps.common.files.serializers import AttachmentsField
from apps.properties.models import (
    FEATURE_FLAG_FIELDS,
    Property,
    Syndicat,
)


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
