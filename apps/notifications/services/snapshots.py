"""Frozen recipient lists for broadcasts (announcements, events, documents, surveys)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import QuerySet

from apps.accounts.enums import TARGETABLE_ROLES
from apps.accounts.services.directory import UserDirectory
from apps.common.exceptions import InvalidInput
from apps.notifications.models import RecipientSnapshot

User = get_user_model()


class SnapshotService:
    @staticmethod
    def validate_target_roles(target_roles) -> list[str]:
        """The normalised roles an announcement, event, document or survey is addressed to.

        Providers are platform-wide and attached to no property: a property
        broadcast cannot reach them, so targeting them is refused rather than
        silently resolving to nobody.
        """
        roles = sorted(set(target_roles))
        if not roles:
            raise InvalidInput(
                "At least one target role is required.", field="target_roles"
            )
        invalid = [role for role in roles if role not in TARGETABLE_ROLES]
        if invalid:
            raise InvalidInput(
                f"Role(s) that a property record cannot be addressed to: {', '.join(invalid)}.",
                field="target_roles",
            )
        return roles

    @staticmethod
    def freeze(*, target: models.Model, prop, target_roles, building=None) -> QuerySet:
        """Resolve who has the target roles now, store them, and return them."""
        matched = UserDirectory.users_by_property_role(prop, target_roles, building)
        content_type = ContentType.objects.get_for_model(target)
        RecipientSnapshot.objects.bulk_create(
            [
                RecipientSnapshot(
                    content_type=content_type,
                    object_id=target.pk,
                    user_id=uid,
                    matched_roles=sorted(roles),
                )
                for uid, roles in matched.items()
            ],
            ignore_conflicts=True,
        )
        return User.objects.filter(pk__in=matched.keys())

    @staticmethod
    def recipients(target: models.Model) -> QuerySet:
        content_type = ContentType.objects.get_for_model(target)
        user_ids = RecipientSnapshot.objects.filter(
            content_type=content_type, object_id=target.pk
        ).values("user_id")
        return User.objects.filter(pk__in=user_ids, is_active=True)

    @staticmethod
    def count(target: models.Model) -> int:
        content_type = ContentType.objects.get_for_model(target)
        return RecipientSnapshot.objects.filter(
            content_type=content_type, object_id=target.pk
        ).count()
