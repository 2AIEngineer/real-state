"""The profile of service providers (accounts holding the provider role)."""

from __future__ import annotations

from django.db import transaction

from apps.accounts.enums import StructuralRole
from apps.accounts.models import ProviderProfile
from apps.accounts.policies import AccountPolicy
from apps.common.db import apply_changes
from apps.common.exceptions import BusinessRuleViolation, NotFound, PermissionDenied

PROFILE_FIELDS = tuple(
    field.name
    for field in ProviderProfile._meta.concrete_fields
    if field.name not in {"id", "user", "created_at", "updated_at"}
)


class ProviderProfileService:
    @staticmethod
    def ensure_exists(*, user) -> ProviderProfile:
        profile, _ = ProviderProfile.objects.get_or_create(user=user)
        return profile

    @staticmethod
    def get(*, actor, user) -> ProviderProfile:
        profile = ProviderProfile.objects.filter(user=user).first()
        if profile is None:
            raise NotFound("This user has no provider profile.")
        return profile

    @staticmethod
    @transaction.atomic
    def update(*, actor, user, changes: dict) -> ProviderProfile:
        if actor.pk != user.pk and not AccountPolicy.can_view(actor, user):
            raise NotFound("User not found.")
        if not AccountPolicy.can_edit_provider_profile(actor, user):
            raise PermissionDenied("Only administrators, syndics and managers can manage accounts.")
        if user.role != StructuralRole.PROVIDER:
            raise BusinessRuleViolation(
                "Only accounts holding the provider role have a provider profile."
            )
        profile = ProviderProfileService.ensure_exists(user=user)
        fields = apply_changes(profile, changes, PROFILE_FIELDS)
        if fields:
            profile.save(update_fields=[*fields, "updated_at"])
        return profile
