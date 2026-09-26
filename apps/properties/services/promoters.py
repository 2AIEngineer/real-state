"""Promoters: the developers of properties, each with a technical representative account."""

from __future__ import annotations

from django.db import transaction
from django.db.models import ProtectedError, QuerySet

from apps.accounts.services.technical import TechnicalAccountService
from apps.common.db import apply_changes, deleting, translate_integrity_errors
from apps.common.deletion import destroy
from apps.common.exceptions import NotFound
from apps.common.services.audit import AuditService
from apps.properties import errors
from apps.properties.audit import PromoterAudit
from apps.properties.models import Promoter
from apps.properties.policies import PromoterPolicy

PROMOTER_FIELDS = (
    "name",
    "legal_name",
    "registration_number",
    "contact_email",
    "contact_phone",
    "address",
)
PROMOTER_CONSTRAINTS = {"promoter_name_ci_unique": errors.promoter_name_taken}


class PromoterService:
    @staticmethod
    def list_visible(*, actor) -> QuerySet[Promoter]:
        return (
            Promoter.objects.filter(PromoterPolicy.visible_filter(actor))
            .distinct()
            .select_related("representative_user")
        )

    @staticmethod
    def get_visible(*, actor, promoter_id: int) -> Promoter:
        promoter = (
            PromoterService.list_visible(actor=actor).filter(pk=promoter_id).first()
        )
        if promoter is None:
            raise NotFound("Promoter not found.")
        return promoter

    @staticmethod
    def get(*, promoter_id: int) -> Promoter:
        """Reference lookup (any promoter may develop a new property)."""
        promoter = Promoter.objects.filter(pk=promoter_id).first()
        if promoter is None:
            raise NotFound("Promoter not found.", field="promoter_id")
        return promoter

    @staticmethod
    @transaction.atomic
    def create(*, actor, representative_email: str, data: dict) -> Promoter:
        """Creates the promoter and its technical representative account."""
        if not PromoterPolicy.can_manage(actor):
            raise errors.admins_only()
        representative = TechnicalAccountService.create(
            actor=actor, email=representative_email, display_name=data.get("name", "")
        )
        promoter = Promoter(representative_user=representative, created_by=actor)
        apply_changes(promoter, data, PROMOTER_FIELDS)
        with translate_integrity_errors(PROMOTER_CONSTRAINTS):
            promoter.save()
        AuditService.record(actor=actor, action=PromoterAudit.CREATED, target=promoter)
        return promoter

    @staticmethod
    @transaction.atomic
    def update(*, actor, promoter: Promoter, changes: dict) -> Promoter:
        if not PromoterPolicy.can_manage(actor):
            raise errors.admins_only()
        fields = apply_changes(promoter, changes, PROMOTER_FIELDS)
        if fields:
            with translate_integrity_errors(PROMOTER_CONSTRAINTS):
                promoter.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=PromoterAudit.UPDATED,
                target=promoter,
                metadata={"fields": fields},
            )
        return promoter

    @staticmethod
    @transaction.atomic
    def delete(*, actor, promoter: Promoter) -> None:
        """Removable while it develops no property. Its technical representative
        account goes with it, unless the ownership ledger still points at it."""
        if not PromoterPolicy.can_manage(actor):
            raise errors.admins_only()
        representative = promoter.representative_user
        AuditService.record(actor=actor, action=PromoterAudit.DELETED, target=promoter)
        # A promoter is a reference, not a container: a property it develops is
        # moved to another promoter (PATCH /properties/{id}/promoter/), never deleted with it.
        with deleting(
            "promoter", hint="Assign another promoter to its properties first."
        ):
            destroy(promoter)
        try:
            with transaction.atomic():
                if representative.is_technical_account:
                    representative.delete()
        except ProtectedError:
            pass  # still referenced by past ownerships: keep the account
