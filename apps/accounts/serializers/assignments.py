"""Roles, and the places where a role is exercised."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.enums import StructuralRole
from apps.accounts.models import (
    UserBuilding,
    UserProperty,
    UserSyndicat,
)

User = get_user_model()


class AssignmentSerializer(serializers.ModelSerializer):
    """What every assignment row carries, whatever the table (`UserAssignmentBase`).

    The three serializers below add the one thing that differs: the place. They
    are separate on purpose — a reader of a payload sees `syndicat`, `property`
    or `building`, and never has to ask which kind of row it is looking at.
    """

    granted_by = serializers.IntegerField(source="granted_by_id", allow_null=True)
    revoked_by = serializers.IntegerField(source="revoked_by_id", allow_null=True)

    class Meta:
        fields = [
            "id",
            "is_active",
            "granted_by",
            "created_at",
            "revoked_at",
            "revoked_by",
        ]
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
