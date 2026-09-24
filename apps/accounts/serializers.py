from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.enums import Gender, StructuralRole
from apps.accounts.models import (
    Language,
    ProviderProfile,
    ProviderServiceType,
    UserBuilding,
    UserProperty,
    UserSyndicat,
)

User = get_user_model()


class LoginSerializer(TokenObtainPairSerializer):
    """Case-insensitive e-mail login."""

    def validate(self, attrs):
        attrs[self.username_field] = attrs[self.username_field].strip().lower()
        return super().validate(attrs)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    is_activated = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "gender",
            "preferred_language",
            "role",
            "is_active",
            "is_activated",
            "date_joined",
            "last_login",
            "deactivated_at",
        ]
        read_only_fields = fields

    def get_is_activated(self, obj) -> bool:
        """Whether the invitation was accepted (a password was set)."""
        return obj.has_usable_password()


class AccountOwnershipSerializer(serializers.Serializer):
    """A unit the account owns from the day it is registered."""

    unit_id = serializers.IntegerField(min_value=1)
    share = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        default=None,
        help_text="Percentage held; left out, a sole owner holds 100%.",
    )


class AccountTenancySerializer(serializers.Serializer):
    """The unit the account rents.

    It joins the lease running on that unit; when the unit has none — the
    ordinary case for its first tenant — a lease opens with the dates given
    here and the account as its signatory.
    """

    unit_id = serializers.IntegerField(min_value=1)
    is_signatory = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Ignored when the lease opens: its first tenant signs it.",
    )
    start_date = serializers.DateField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Start of the lease to open; today by default.",
    )
    end_date = serializers.DateField(required=False, allow_null=True, default=None)
    contract_reference = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )


class AccountCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    gender = serializers.ChoiceField(choices=Gender.choices, default=Gender.UNDISCLOSED)
    preferred_language = serializers.ChoiceField(choices=Language.choices, default=Language.FRENCH)
    role = serializers.ChoiceField(choices=StructuralRole.choices, default=StructuralRole.STANDARD)
    building_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
        help_text="Security, cleaning: buildings of the selected property.",
    )
    ownerships = AccountOwnershipSerializer(
        many=True,
        required=False,
        default=list,
        help_text="Standard account: the units it owns. Required unless it rents one.",
    )
    tenancy = AccountTenancySerializer(
        required=False,
        allow_null=True,
        default=None,
        help_text="Standard account: the unit it rents. Required unless it owns one.",
    )


@extend_schema_serializer(component_name="UserProfile")
class UserProfileUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=Gender.choices, required=False)
    preferred_language = serializers.ChoiceField(choices=Language.choices, required=False)


class EmailChangeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    current_password = serializers.CharField(required=False, write_only=True, trim_whitespace=False)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordSetSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class AccountDeactivationSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="", max_length=500)


class UserSearchQueryParamsSerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, max_length=120)
    include_inactive = serializers.BooleanField(required=False, default=False)


class ProviderProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderProfile
        fields = [
            "company_name",
            "service_type",
            "service_description",
            "address",
            "business_phone",
            "website",
            "registration_number",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


@extend_schema_serializer(component_name="ProviderProfile")
class ProviderProfileUpdateSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    service_type = serializers.ChoiceField(choices=ProviderServiceType.choices, required=False)
    service_description = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    business_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    registration_number = serializers.CharField(max_length=64, required=False, allow_blank=True)


# ---------------------------------------------------------------------- session
# The `SessionContext` the frontend expects after a successful login. Values the
# backend cannot know are null, lists empty (see `SessionService`).


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


# --------------------------------------------------------------------------
# Roles and assignments: where an account's role is exercised.
# --------------------------------------------------------------------------


class AssignmentSerializer(serializers.ModelSerializer):
    """What every assignment row carries, whatever the table (`UserAssignmentBase`).

    The three serializers below add the one thing that differs: the place. They
    are separate on purpose — a reader of a payload sees `syndicat`, `property`
    or `building`, and never has to ask which kind of row it is looking at.
    """

    granted_by = serializers.IntegerField(source="granted_by_id", allow_null=True)
    revoked_by = serializers.IntegerField(source="revoked_by_id", allow_null=True)

    class Meta:
        fields = ["id", "is_active", "granted_by", "created_at", "revoked_at", "revoked_by"]
        read_only_fields = fields


class UserSyndicatSerializer(AssignmentSerializer):
    """A syndic and a syndicat they run (its properties, present and future)."""

    syndicat_name = serializers.CharField(source="syndicat.name")

    class Meta(AssignmentSerializer.Meta):
        model = UserSyndicat
        fields = [*AssignmentSerializer.Meta.fields, "syndicat", "syndicat_name"]
        read_only_fields = fields


class UserPropertySerializer(AssignmentSerializer):
    """A manager or a maintenance agent, and a property they work on."""

    property_name = serializers.CharField(source="property.name")

    class Meta(AssignmentSerializer.Meta):
        model = UserProperty
        fields = [*AssignmentSerializer.Meta.fields, "property", "property_name"]
        read_only_fields = fields


class UserBuildingSerializer(AssignmentSerializer):
    """A security or cleaning agent, and a building they work in."""

    building_name = serializers.CharField(source="building.name")

    class Meta(AssignmentSerializer.Meta):
        model = UserBuilding
        fields = [*AssignmentSerializer.Meta.fields, "building", "building_name"]
        read_only_fields = fields


class BuildingAssignmentInputSerializer(serializers.Serializer):
    """The buildings a security or cleaning account is assigned to. They must
    belong to the selected property, which is what places them."""

    building_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        help_text="Buildings of the selected property.",
    )


class RoleChangeSerializer(serializers.Serializer):
    """The new role, and — for a security or cleaning role — the buildings it
    is exercised in. Every other role takes its place from the selected
    syndicat or the selected property."""

    role = serializers.ChoiceField(choices=StructuralRole.choices)
    building_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
        help_text="Security, cleaning: buildings of the selected property.",
    )


class AssignmentListQueryParamsSerializer(serializers.Serializer):
    include_revoked = serializers.BooleanField(required=False, default=False)
