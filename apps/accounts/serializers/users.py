"""Accounts: creating, reading and editing them, and provider profiles."""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.accounts.enums import Gender, StructuralRole
from apps.accounts.models import (
    Language,
    ProviderProfile,
    ProviderServiceType,
)

User = get_user_model()


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
    phone = serializers.CharField(
        max_length=32, required=False, allow_blank=True, default=""
    )
    gender = serializers.ChoiceField(choices=Gender.choices, default=Gender.UNDISCLOSED)
    preferred_language = serializers.ChoiceField(
        choices=Language.choices, default=Language.FRENCH
    )
    role = serializers.ChoiceField(
        choices=StructuralRole.choices, default=StructuralRole.STANDARD
    )
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
    preferred_language = serializers.ChoiceField(
        choices=Language.choices, required=False
    )


class EmailChangeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    current_password = serializers.CharField(
        required=False, write_only=True, trim_whitespace=False
    )


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class AccountDeactivationSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=500
    )


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
    company_name = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    service_type = serializers.ChoiceField(
        choices=ProviderServiceType.choices, required=False
    )
    service_description = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    business_phone = serializers.CharField(
        max_length=32, required=False, allow_blank=True
    )
    website = serializers.URLField(required=False, allow_blank=True)
    registration_number = serializers.CharField(
        max_length=64, required=False, allow_blank=True
    )
