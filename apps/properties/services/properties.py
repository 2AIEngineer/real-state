"""Properties: the residences, with their promoter, their plan and their logo."""

from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.db.models import QuerySet

from apps.accounts.services.assignments import PropertyAssignmentService
from apps.common.attachments.rules import EntityType
from apps.common.attachments.service import AttachmentService
from apps.common.db import apply_changes, translate_integrity_errors
from apps.common.deletion import destroy
from apps.common.exceptions import (
    BusinessRuleViolation,
    InvalidInput,
    NotFound,
    PermissionDenied,
)
from apps.common.services.audit import AuditService
from apps.properties import errors, notices
from apps.properties.audit import PropertyAudit
from apps.properties.models import (
    FEATURE_FLAG_FIELDS,
    OwnershipEndReason,
    OwnershipStatus,
    Promoter,
    Property,
    Syndicat,
    UnitOwnership,
)
from apps.properties.policies import PropertyPolicy
from apps.properties.services.ownership import close_ownership, open_promoter_default

PROPERTY_FIELDS = (
    "name",
    "description",
    "address",
    "city",
    "country",
    "contact_email",
    "contact_phone",
    "timezone",
)
PROPERTY_CONSTRAINTS = {"property_name_per_syndicat": errors.property_name_taken}


class PropertyService:
    @staticmethod
    def list_visible(*, actor) -> QuerySet[Property]:
        qs = Property.objects.select_related("syndicat", "promoter")
        return qs.filter(PropertyPolicy.visible_filter(actor))

    @staticmethod
    def list_reachable_in(
        *, actor, syndicat: Syndicat, search: str | None = None
    ) -> QuerySet[Property]:
        """Properties of `syndicat` the account may open, for the UI configuration path (step `property`)."""
        properties = PropertyService.list_visible(actor=actor).filter(syndicat=syndicat)
        if not PropertyPolicy.can_see_inactive(actor):
            properties = properties.filter(is_active=True)
        if search:
            properties = properties.filter(name__icontains=search)
        return properties.order_by("name", "id")

    @staticmethod
    def get_visible(*, actor, property_id: int, syndicat_id: int | None = None) -> Property:
        """The property, checked against the selected syndicat when one is given.

        `syndicat_id` is the syndicat selected by the client (header
        `X-Syndicat-Id`): the property must belong to it, so a stale or
        hand-crafted selection can never mix two syndicats' data.
        """
        prop = PropertyService.list_visible(actor=actor).filter(pk=property_id).first()
        if prop is None:
            raise NotFound("Property not found.")
        if syndicat_id is not None and prop.syndicat_id != syndicat_id:
            raise InvalidInput(
                "The selected property does not belong to the selected syndicat.",
                field="property_id",
                code="property_outside_syndicat",
            )
        return prop

    @staticmethod
    def get(*, property_id: int) -> Property:
        prop = (
            Property.objects.select_related("syndicat", "promoter__representative_user")
            .filter(pk=property_id)
            .first()
        )
        if prop is None:
            raise NotFound("Property not found.")
        return prop

    @staticmethod
    @transaction.atomic
    def create(
        *,
        actor,
        syndicat: Syndicat,
        promoter: Promoter,
        data: dict,
        features: dict[str, bool] | None = None,
    ) -> Property:
        if not PropertyPolicy.can_create(actor, syndicat):
            raise PermissionDenied(
                "Only administrators and syndics covering the whole syndicat can create properties."
            )
        if not syndicat.is_active:
            raise BusinessRuleViolation("Properties cannot be added to an inactive syndicat.")
        prop = Property(syndicat=syndicat, promoter=promoter, created_by=actor)
        apply_changes(prop, data, PROPERTY_FIELDS)
        if features:
            # Plan gating is a commercial decision: only platform admins set it.
            if not PropertyPolicy.can_set_plan(actor):
                raise errors.admins_only()
            for feature, enabled in features.items():
                setattr(prop, FEATURE_FLAG_FIELDS[feature], enabled)
        with translate_integrity_errors(PROPERTY_CONSTRAINTS):
            prop.save()
        AuditService.record(
            actor=actor, action=PropertyAudit.CREATED, target=prop, property_id=prop.pk
        )
        # Managers already running a property of this syndicat run this one too.
        PropertyAssignmentService.assign_new_property_to_its_managers(prop=prop, actor=actor)
        # A new property starts with the standard library tree. Local import:
        # the library module is built on top of properties.
        from apps.library.services import FolderService

        FolderService.create_default_folders(prop=prop)
        notices.property_created(prop, actor=actor)
        return prop

    @staticmethod
    @transaction.atomic
    def update(*, actor, prop: Property, changes: dict) -> Property:
        # Governance only: a manager runs the content of a property, never the record itself.
        if not PropertyPolicy.can_update(actor, prop):
            raise errors.record_managers_only()
        fields = apply_changes(prop, changes, PROPERTY_FIELDS)
        if "is_active" in changes:
            if not PropertyPolicy.can_change_status(actor):
                raise errors.admins_only()
            prop.is_active = changes["is_active"]
            fields.append("is_active")
        if fields:
            with translate_integrity_errors(PROPERTY_CONSTRAINTS):
                prop.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=PropertyAudit.UPDATED,
                target=prop,
                property_id=prop.pk,
                metadata={"fields": fields},
            )
        return prop

    @staticmethod
    @transaction.atomic
    def set_features(*, actor, prop: Property, features: dict[str, bool]) -> Property:
        if not PropertyPolicy.can_set_plan(actor):
            raise errors.admins_only()
        fields = []
        for feature, enabled in features.items():
            flag = FEATURE_FLAG_FIELDS[feature]
            setattr(prop, flag, enabled)
            fields.append(flag)
        if fields:
            prop.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=PropertyAudit.FEATURES_CHANGED,
                target=prop,
                property_id=prop.pk,
                metadata=features,
            )
        return prop

    @staticmethod
    @transaction.atomic
    def change_promoter(
        *, actor, prop: Property, promoter: Promoter, effective_date: dt.date
    ) -> Property:
        """Replace the promoter; units still held by the former promoter move
        to the new one (the ownership ledger keeps both periods)."""
        if not PropertyPolicy.can_change_promoter(actor):
            raise errors.admins_only()
        prop = Property.objects.select_for_update(of=("self",)).get(pk=prop.pk)
        if prop.promoter_id == promoter.pk:
            return prop
        former = prop.promoter
        prop.promoter = promoter
        prop.save(update_fields=["promoter", "updated_at"])
        defaults = UnitOwnership.objects.select_for_update(of=("self",)).filter(
            unit__building__property=prop,
            status=OwnershipStatus.ACTIVE,
            is_promoter_default=True,
            owner=former.representative_user,
        )
        for ownership in defaults:
            handover = max(effective_date, ownership.start_date)
            close_ownership(
                ownership,
                end_date=handover,
                reason=OwnershipEndReason.PROMOTER_CHANGE,
                actor=actor,
            )
            open_promoter_default(ownership.unit, prop=prop, start_date=handover, actor=actor)
        AuditService.record(
            actor=actor,
            action=PropertyAudit.PROMOTER_CHANGED,
            target=prop,
            property_id=prop.pk,
            metadata={"from": former.pk, "to": promoter.pk},
        )
        return prop

    @staticmethod
    @transaction.atomic
    def delete(*, actor, prop: Property) -> None:
        """Permanent removal of a property and all it holds. Deactivating it is
        the alternative that keeps its history."""
        if not PropertyPolicy.can_delete(actor):
            raise errors.admins_only()
        AuditService.record(
            actor=actor, action=PropertyAudit.DELETED, target=prop, property_id=prop.pk
        )
        # Who loses access is journaled before the rows go.
        PropertyAssignmentService.delete_for_property(prop=prop, actor=actor)
        destroy(prop)

    @staticmethod
    @transaction.atomic
    def set_logo(*, actor, prop: Property, upload) -> None:
        if not PropertyPolicy.can_update(actor, prop):
            raise errors.record_managers_only()
        AttachmentService.attach_one(
            entity_type=EntityType.PROPERTY_LOGO,
            entity_id=prop.pk,
            upload=upload,
            uploaded_by=actor,
        )
