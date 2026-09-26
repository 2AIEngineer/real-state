"""What the three assignment services share.

An assignment table says where a role is exercised: `UserSyndicat` for syndics,
`UserProperty` for managers and maintenance agents, `UserBuilding` for security
and cleaning agents. The three tables behave alike (grant, revoke, revoke all,
count, list) and differ only by their place, the roles they take and who may
manage them, which each subclass declares.
"""

from __future__ import annotations

from typing import ClassVar

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Model, QuerySet
from django.utils import timezone

from apps.accounts import errors
from apps.accounts.audit import AssignmentAudit
from apps.accounts.policies import can_assign_account, can_see_all_assignments_of
from apps.common.db import translate_integrity_errors
from apps.common.exceptions import (
    BusinessRuleViolation,
    InvalidInput,
    NotFound,
    PermissionDenied,
)
from apps.common.services.audit import AuditService

User = get_user_model()

CANNOT_MANAGE = "You cannot manage this account's assignments on this syndicat, property or building."


def actor_or_none(actor):
    return actor if getattr(actor, "pk", None) else None


def lock_assignable_account(user):
    """Lock the account: every change to one user's assignments runs one at a time."""
    user = User.objects.select_for_update().get(pk=user.pk)
    if not user.is_active or user.is_technical_account:
        raise BusinessRuleViolation("Only active personal accounts can be assigned.")
    return user


def load_places(model: type[Model], ids, *, field: str) -> list:
    """The rows with these ids, or NotFound naming the missing ones."""
    ids = list(dict.fromkeys(ids))
    found = {obj.pk: obj for obj in model.objects.filter(pk__in=ids)}
    missing = [i for i in ids if i not in found]
    if missing:
        raise NotFound(
            f"Unknown {model._meta.verbose_name} id(s): {missing}.", field=field
        )
    return [found[i] for i in ids]


class AssignmentService:
    """Base of the three services; a subclass declares its table and its rules."""

    model: ClassVar[type[Model]]  # the assignment table
    place_model: ClassVar[type[Model]]  # what the role is exercised on
    place_field: ClassVar[str]  # name of the foreign key to the place
    places_label: ClassVar[str]  # plural, for messages ("syndicats")
    ids_field: ClassVar[str]  # name of the request field carrying the place ids
    roles: ClassVar[tuple[str, ...]]  # roles taking this kind of assignment
    unique_constraint: ClassVar[str]

    # -- what a subclass specialises -------------------------------------------------
    @staticmethod
    def can_assign_place(actor, place) -> bool:
        raise NotImplementedError

    @staticmethod
    def property_id_of(place) -> int | None:
        """The property an assignment on `place` belongs to, for the journal."""
        raise NotImplementedError

    @classmethod
    def restrict_to_managed(cls, rows: QuerySet, actor) -> QuerySet:
        """What of a user's assignments the actor may see, when not all of it."""
        raise NotImplementedError

    @classmethod
    def validate_places(cls, user, places: list) -> None:
        """Extra rules on the places about to be granted (none by default)."""

    # -- shared behaviour ----------------------------------------------------------------
    @classmethod
    def _assign(cls, *, actor, user, ids) -> list:
        user = lock_assignable_account(user)
        if user.role not in cls.roles:
            raise InvalidInput(
                f"A {user.role} account is not assigned to {cls.places_label}.",
                field=cls.ids_field,
            )
        places = load_places(cls.place_model, ids, field=cls.ids_field)
        cls.validate_places(user, places)
        created = []
        for place in places:
            if not (
                can_assign_account(actor, user) and cls.can_assign_place(actor, place)
            ):
                raise PermissionDenied(CANNOT_MANAGE)
            with translate_integrity_errors(
                {cls.unique_constraint: errors.already_assigned}
            ):
                row = cls.model.objects.create(
                    **{
                        "user": user,
                        cls.place_field: place,
                        "granted_by": actor_or_none(actor),
                    }
                )
            cls._audit_granted(
                row,
                actor=actor,
                property_id=cls.property_id_of(place),
                reason="granted",
            )
            created.append(row)
        return created

    @classmethod
    @transaction.atomic
    def revoke(cls, *, actor, assignment_id: int):
        rows = cls.model.objects.select_related("user", cls.place_field)
        row = rows.filter(pk=assignment_id).first()
        if row is None:
            raise NotFound("Assignment not found.")
        lock_assignable_account(row.user)
        row = rows.select_for_update(of=("self",)).get(pk=row.pk)
        if not row.is_active:
            raise BusinessRuleViolation("This assignment is already revoked.")
        place = getattr(row, cls.place_field)
        if not (
            can_assign_account(actor, row.user) and cls.can_assign_place(actor, place)
        ):
            raise PermissionDenied(CANNOT_MANAGE)
        cls._revoke(row, actor=actor, reason="revoked")
        return row

    @classmethod
    def revoke_all(cls, *, actor, user, reason: str) -> int:
        """Revoke every active assignment of the user (callers hold the authorization)."""
        rows = list(
            cls.model.objects.filter(user=user, is_active=True).select_related(
                "user", cls.place_field
            )
        )
        for row in rows:
            cls._revoke(row, actor=actor, reason=reason)
        return len(rows)

    @classmethod
    def active_count(cls, user) -> int:
        return cls.model.objects.filter(user=user, is_active=True).count()

    @classmethod
    def list_for_user(cls, *, actor, user, include_revoked: bool = False) -> list:
        """The user's assignments; someone else only sees those within their own reach."""
        rows = cls.model.objects.filter(user=user).select_related(cls.place_field)
        if not include_revoked:
            rows = rows.filter(is_active=True)
        if not can_see_all_assignments_of(actor, user):
            rows = cls.restrict_to_managed(rows, actor)
        return list(rows)

    # -- journal -----------------------------------------------------------------------------
    @classmethod
    def _audit_granted(
        cls, row, *, actor, property_id: int | None, reason: str
    ) -> None:
        AuditService.record(
            actor=actor,
            action=AssignmentAudit.GRANTED,
            target=row,
            property_id=property_id,
            metadata={"user_id": row.user_id, "role": row.user.role, "reason": reason},
        )

    @classmethod
    def _revoke(cls, row, *, actor, reason: str) -> None:
        row.is_active = False
        row.revoked_at = timezone.now()
        row.revoked_by = actor_or_none(actor)
        row.save(update_fields=["is_active", "revoked_at", "revoked_by", "updated_at"])
        AuditService.record(
            actor=actor,
            action=AssignmentAudit.REVOKED,
            target=row,
            property_id=cls.property_id_of(getattr(row, cls.place_field)),
            metadata={"user_id": row.user_id, "role": row.user.role, "reason": reason},
        )
