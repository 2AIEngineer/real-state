"""Syndicats: the organisations that run properties."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Count, Q, QuerySet

from apps.accounts.services.authorization import AccessService
from apps.common.attachments.rules import EntityType
from apps.common.attachments.service import AttachmentService
from apps.common.db import apply_changes, translate_integrity_errors
from apps.common.deletion import destroy
from apps.common.exceptions import NotFound
from apps.common.services.audit import AuditService
from apps.properties import errors, notices
from apps.properties.audit import SyndicatAudit
from apps.properties.models import Syndicat
from apps.properties.policies import PropertyPolicy, SyndicatPolicy

SYNDICAT_FIELDS = (
    "name",
    "legal_name",
    "registration_number",
    "contact_email",
    "contact_phone",
    "address",
    "city",
    "country",
)
SYNDICAT_CONSTRAINTS = {"syndicat_name_ci_unique": errors.syndicat_name_taken}


class SyndicatService:
    @staticmethod
    def list_visible(*, actor) -> QuerySet[Syndicat]:
        return Syndicat.objects.filter(SyndicatPolicy.visible_filter(actor)).distinct()

    @staticmethod
    def get_visible(*, actor, syndicat_id: int) -> Syndicat:
        syndicat = SyndicatService.list_visible(actor=actor).filter(pk=syndicat_id).first()
        if syndicat is None:
            raise NotFound("Syndicat not found.")
        return syndicat

    @staticmethod
    def list_reachable(*, actor, search: str | None = None) -> QuerySet[Syndicat]:
        """Syndicats the account may open, each with the properties it can reach there.

        Used by the UI configuration path (step `syndicat`): a syndic sees the
        syndicat they run even before it has a single property yet, which
        `list_visible` alone cannot tell apart from one they have no link to.
        """
        reachable = AccessService.accessible_syndicat_ids(actor)
        syndicats = (
            Syndicat.objects.all()
            if reachable is None
            else Syndicat.objects.filter(pk__in=reachable)
        )
        if not PropertyPolicy.can_see_inactive(actor):
            syndicats = syndicats.filter(is_active=True)
        if search:
            syndicats = syndicats.filter(name__icontains=search)
        property_ids = AccessService.accessible_property_ids(actor)
        accessible = Q() if reachable is None else Q(properties__id__in=property_ids)
        return syndicats.annotate(
            accessible_properties_count=Count(
                "properties",
                filter=accessible & Q(properties__is_active=True),
                distinct=True,
            )
        ).order_by("name", "id")

    @staticmethod
    def get_reachable(*, actor, syndicat_id: int) -> Syndicat:
        syndicat = SyndicatService.list_reachable(actor=actor).filter(pk=syndicat_id).first()
        if syndicat is None:
            raise NotFound("Syndicat not found.")
        return syndicat

    @staticmethod
    @transaction.atomic
    def create(*, actor, data: dict) -> Syndicat:
        if not SyndicatPolicy.can_create(actor):
            raise errors.admins_only()
        syndicat = Syndicat(created_by=actor)
        apply_changes(syndicat, data, SYNDICAT_FIELDS)
        with translate_integrity_errors(SYNDICAT_CONSTRAINTS):
            syndicat.save()
        AuditService.record(actor=actor, action=SyndicatAudit.CREATED, target=syndicat)
        notices.syndicat_created(syndicat, actor=actor)
        return syndicat

    @staticmethod
    @transaction.atomic
    def update(*, actor, syndicat: Syndicat, changes: dict) -> Syndicat:
        # Governance only: managers never modify the syndicat record.
        if not SyndicatPolicy.can_update(actor, syndicat):
            raise errors.record_managers_only()
        fields = apply_changes(syndicat, changes, SYNDICAT_FIELDS)
        if "is_active" in changes:
            if not SyndicatPolicy.can_change_status(actor):
                raise errors.admins_only()
            syndicat.is_active = changes["is_active"]
            fields.append("is_active")
        if fields:
            with translate_integrity_errors(SYNDICAT_CONSTRAINTS):
                syndicat.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=SyndicatAudit.UPDATED,
                target=syndicat,
                metadata={"fields": fields},
            )
        return syndicat

    @staticmethod
    @transaction.atomic
    def delete(*, actor, syndicat: Syndicat) -> None:
        """Permanent removal of a syndicat and its properties. Deactivating it is
        the alternative that keeps them."""
        if not SyndicatPolicy.can_delete(actor):
            raise errors.admins_only()
        AuditService.record(actor=actor, action=SyndicatAudit.DELETED, target=syndicat)
        destroy(syndicat)

    @staticmethod
    @transaction.atomic
    def set_logo(*, actor, syndicat: Syndicat, upload) -> None:
        if not SyndicatPolicy.can_update(actor, syndicat):
            raise errors.record_managers_only()
        AttachmentService.attach_one(
            entity_type=EntityType.SYNDICAT_LOGO,
            entity_id=syndicat.pk,
            upload=upload,
            uploaded_by=actor,
        )
