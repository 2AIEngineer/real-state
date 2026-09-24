"""Syndics and the syndicats they run (a syndicat covers its properties, present and future)."""

from __future__ import annotations

from apps.accounts.models import ROLES_ASSIGNED_TO_SYNDICATS, UserSyndicat
from apps.accounts.policies import can_assign_syndicat
from apps.accounts.services.assignments.base import AssignmentService
from apps.accounts.services.authorization import AccessService
from apps.properties.models import Syndicat


class SyndicatAssignmentService(AssignmentService):
    model = UserSyndicat
    place_model = Syndicat
    place_field = "syndicat"
    places_label = "syndicats"
    ids_field = "syndicat_ids"
    roles = ROLES_ASSIGNED_TO_SYNDICATS
    unique_constraint = "unique_active_user_syndicat"

    @staticmethod
    def can_assign_place(actor, syndicat) -> bool:
        return can_assign_syndicat(actor, syndicat)

    @staticmethod
    def property_id_of(syndicat) -> None:
        return None  # a syndicat is not inside a property

    @classmethod
    def restrict_to_managed(cls, rows, actor):
        """Someone else only sees the syndicats containing a property they manage."""
        return rows.filter(
            syndicat__properties__id__in=AccessService.managed_property_ids(actor)
        ).distinct()

    @classmethod
    def assign(cls, *, actor, user, syndicat_ids) -> list[UserSyndicat]:
        return cls._assign(actor=actor, user=user, ids=syndicat_ids)
