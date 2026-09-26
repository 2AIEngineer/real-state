"""The SessionContext handed to the client after login."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class SessionCredentialsSerializer(serializers.Serializer):
    access_token = serializers.CharField(allow_null=True)
    refresh_token = serializers.CharField(allow_null=True)


class SessionSelectionSerializer(serializers.Serializer):
    """The syndicat, or the property, the client has selected."""

    id = serializers.IntegerField(allow_null=True)
    name = serializers.CharField(allow_null=True)
    logo_url = serializers.CharField(allow_null=True)


class SessionFeaturesSerializer(serializers.Serializer):
    include_service_request = serializers.BooleanField()
    include_announcements = serializers.BooleanField()
    include_events = serializers.BooleanField()
    include_amenities = serializers.BooleanField()
    include_store = serializers.BooleanField()
    include_library = serializers.BooleanField()
    include_short_term_rental = serializers.BooleanField()
    include_surveys = serializers.BooleanField()
    include_marketplace = serializers.BooleanField()
    include_visitor = serializers.BooleanField()
    include_chat = serializers.BooleanField()


class SessionPropertySerializer(SessionSelectionSerializer):
    """The property the client has selected, with the modules enabled there."""

    features = SessionFeaturesSerializer()


class SessionUIConfigSerializer(serializers.Serializer):
    app_mode = serializers.ChoiceField(choices=["web", "mobile"], allow_null=True)
    step = serializers.ChoiceField(choices=["syndicat", "property", "dashboard"], allow_null=True)
    syndicat = SessionSelectionSerializer()
    property = SessionPropertySerializer()


class SessionRoleSerializer(serializers.Serializer):
    """The label of the account role, and one flag per role: only one is true."""

    label = serializers.CharField(allow_null=True)
    is_admin = serializers.BooleanField()
    is_syndic = serializers.BooleanField()
    is_manager = serializers.BooleanField()
    is_provider = serializers.BooleanField()
    is_security = serializers.BooleanField()
    is_cleaning = serializers.BooleanField()
    is_standard = serializers.BooleanField()
    is_maintenance = serializers.BooleanField()


class SessionUserStatusSerializer(serializers.Serializer):
    is_owner = serializers.BooleanField()
    is_tenant = serializers.BooleanField()


class SessionOwnershipSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField(allow_null=True)
    unit_number = serializers.CharField(allow_null=True)
    ownership_share = serializers.CharField(allow_null=True)


class SessionTenancySerializer(serializers.Serializer):
    lease_id = serializers.IntegerField(allow_null=True)
    unit_id = serializers.IntegerField(allow_null=True)
    unit_number = serializers.CharField(allow_null=True)
    is_signatory = serializers.BooleanField()


class SessionAssetsSerializer(serializers.Serializer):
    user_status = SessionUserStatusSerializer()
    ownerships = SessionOwnershipSerializer(many=True)
    tenancies = SessionTenancySerializer(many=True)


class SessionUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    first_name = serializers.CharField(allow_null=True)
    last_name = serializers.CharField(allow_null=True)
    full_name = serializers.CharField(allow_null=True)
    phone = serializers.CharField(allow_null=True)
    gender = serializers.CharField(allow_null=True)
    preferred_language = serializers.CharField(allow_null=True)
    role = SessionRoleSerializer()
    assets = SessionAssetsSerializer()


class SessionContextSerializer(serializers.Serializer):
    """What the client receives once logged in: credentials, UI configuration, user."""

    credentials = SessionCredentialsSerializer()
    ui_config = SessionUIConfigSerializer()
    user = SessionUserSerializer()
