from __future__ import annotations

from collections.abc import Iterable

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts.enums import StructuralRole
from apps.notifications.models import CATEGORY_PREFERENCE_FIELD, NotificationPreference

PREFERENCE_FIELDS: tuple[str, ...] = (
    "enabled_push",
    "enabled_email",
    *CATEGORY_PREFERENCE_FIELD.values(),
)

FEATURE_FIELDS: frozenset[str] = frozenset(CATEGORY_PREFERENCE_FIELD.values())

# Feature notifications each role starts with; everyone remains free to opt
# in or out afterwards. Field staff start with none: they still receive what
# concerns them directly (operational categories obey the channels only).
# Roles absent from the map start with every feature.
ROLE_ENABLED_FEATURES: dict[str, frozenset[str]] = {
    StructuralRole.SYNDIC: FEATURE_FIELDS - {"store_enabled"},
    StructuralRole.MANAGER: FEATURE_FIELDS - {"store_enabled"},
    StructuralRole.SECURITY: frozenset(),
    StructuralRole.CLEANING: frozenset(),
    StructuralRole.PROVIDER: frozenset(),
}


def defaults_for(role: str) -> dict[str, bool]:
    """The feature flags an account holding `role` starts with."""
    enabled = ROLE_ENABLED_FEATURES.get(role, FEATURE_FIELDS)
    return {name: name in enabled for name in FEATURE_FIELDS}


class PreferenceService:
    @staticmethod
    def auto_setup(user) -> NotificationPreference:
        """Sets up the preferences of a new account from its role (kept if they exist)."""
        preference, _ = NotificationPreference.objects.get_or_create(
            user=user, defaults=defaults_for(user.role)
        )
        return preference

    @staticmethod
    def resolve_many(user_ids: Iterable[int]) -> dict[int, NotificationPreference]:
        """Preferences for many users; a missing row is created from the role defaults."""
        ids = set(user_ids)
        prefs = {p.user_id: p for p in NotificationPreference.objects.filter(user_id__in=ids)}
        missing = ids - prefs.keys()
        if missing:
            roles_by_user = (
                get_user_model().objects.filter(pk__in=missing).values_list("pk", "role")
            )
            NotificationPreference.objects.bulk_create(
                [
                    NotificationPreference(user_id=uid, **defaults_for(role))
                    for uid, role in roles_by_user
                ],
                ignore_conflicts=True,
            )
            prefs.update(
                {p.user_id: p for p in NotificationPreference.objects.filter(user_id__in=missing)}
            )
        return prefs

    @staticmethod
    def get(*, user) -> NotificationPreference:
        return PreferenceService.resolve_many([user.pk])[user.pk]

    @staticmethod
    @transaction.atomic
    def update(*, user, changes: dict[str, bool]) -> NotificationPreference:
        preference = PreferenceService.get(user=user)
        preference = NotificationPreference.objects.select_for_update(of=("self",)).get(
            pk=preference.pk
        )
        fields = [name for name in changes if name in PREFERENCE_FIELDS]
        for name in fields:
            setattr(preference, name, bool(changes[name]))
        if fields:
            preference.save(update_fields=[*fields, "updated_at"])
        return preference
