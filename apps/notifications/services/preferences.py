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


def _defaults_for(
    user_id: int, roles_by_user: dict[int, str], owner_or_tenant_ids: set[int]
) -> dict[str, bool]:
    field_only = (
        roles_by_user.get(user_id) in FIELD_ONLY_ROLES
        and user_id not in owner_or_tenant_ids
    )
    return {name: not field_only for name in CATEGORY_PREFERENCE_FIELD.values()}


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
        prefs = {
            p.user_id: p for p in NotificationPreference.objects.filter(user_id__in=ids)
        }
        missing = ids - prefs.keys()
        if missing:
            roles_by_user = dict(
                get_user_model()
                .objects.filter(pk__in=missing)
                .values_list("pk", "role")
            )
            owner_or_tenant_ids = set(
                UnitOwnership.objects.filter(
                    owner_id__in=missing, status=OwnershipStatus.ACTIVE
                ).values_list("owner_id", flat=True)
            ) | set(
                LeaseMember.objects.filter(
                    user_id__in=missing,
                    left_at__isnull=True,
                    lease__status=LeaseStatus.ACTIVE,
                ).values_list("user_id", flat=True)
            )
            NotificationPreference.objects.bulk_create(
                [
                    NotificationPreference(
                        user_id=uid,
                        **_defaults_for(uid, roles_by_user, owner_or_tenant_ids),
                    )
                    for uid in missing
                ],
                ignore_conflicts=True,
            )
            prefs.update(
                {
                    p.user_id: p
                    for p in NotificationPreference.objects.filter(user_id__in=missing)
                }
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
