"""Managers and maintenance agents, and the properties they work on.

A property created in a syndicat where a manager already runs a property is
assigned to that manager.
"""

from __future__ import annotations

from apps.accounts.audit import AssignmentAudit
from apps.accounts.enums import StructuralRole
from apps.accounts.models import ROLES_ASSIGNED_TO_PROPERTIES, UserProperty
from apps.accounts.policies import can_assign_property
from apps.accounts.services.assignments.base import (
    AssignmentService,
    User,
    actor_or_none,
)
from apps.accounts.services.authorization import AccessService
from apps.common.services.audit import AuditService
from apps.properties.models import Property


class PropertyAssignmentService(AssignmentService):
    model = UserProperty
    place_model = Property
    place_field = "property"
    places_label = "properties"
    ids_field = "property_ids"
    roles = ROLES_ASSIGNED_TO_PROPERTIES
    unique_constraint = "unique_active_user_property"

    @staticmethod
    def can_assign_place(actor, prop) -> bool:
        return can_assign_property(actor, prop)

    @staticmethod
    def property_id_of(prop) -> int:
        return prop.pk

    @classmethod
    def restrict_to_managed(cls, rows, actor):
        """Someone else only sees the properties they manage."""
        return rows.filter(property_id__in=AccessService.managed_property_ids(actor))

    @classmethod
    def assign(cls, *, actor, user, property_ids) -> list[UserProperty]:
        return cls._assign(actor=actor, user=user, ids=property_ids)

    @classmethod
    def assign_new_property_to_its_managers(
        cls, *, prop: Property, actor
    ) -> list[UserProperty]:
        """Give a new property to the managers already running a property of its syndicat.

        Called by `PropertyService.create`, in the same transaction.
        """
        running_a_property_there = UserProperty.objects.filter(
            is_active=True, property__syndicat_id=prop.syndicat_id
        ).values("user_id")
        managers = User.objects.filter(
            role=StructuralRole.MANAGER, is_active=True, pk__in=running_a_property_there
        )
        created = []
        for manager in managers:
            row = UserProperty.objects.create(
                user=manager, property=prop, granted_by=actor_or_none(actor)
            )
            cls._audit_granted(
                row,
                actor=actor,
                property_id=prop.pk,
                reason="new_property_in_managed_syndicat",
            )
            created.append(row)
        return created

    @classmethod
    def delete_for_property(cls, *, prop: Property, actor) -> int:
        """Remove the assignment rows of a property that is being deleted.

        Called by `PropertyService.delete`: the property is gone, so are the
        rows pointing at it, active or already revoked. Each active one is
        journaled first.
        """
        rows = UserProperty.objects.filter(property=prop).select_related("user")
        for row in rows.filter(is_active=True):
            AuditService.record(
                actor=actor,
                action=AssignmentAudit.DELETED,
                target=row,
                property_id=prop.pk,
                metadata={
                    "user_id": row.user_id,
                    "role": row.user.role,
                    "reason": "property_deleted",
                },
            )
        count, _ = rows.delete()
        return count
