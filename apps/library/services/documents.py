"""Documents of the library, each addressed to target roles and holding one file."""

from __future__ import annotations

from django.db import transaction
from django.db.models import QuerySet

from apps.common.db import apply_changes
from apps.common.exceptions import InvalidInput, NotFound, PermissionDenied
from apps.common.files.rules import EntityType
from apps.common.files.service import AttachmentService
from apps.common.services.audit import AuditService
from apps.library import notices
from apps.library.audit import LibraryAudit
from apps.library.models import Folder, LibraryDocument
from apps.library.policies import DocumentPolicy
from apps.notifications.services import SnapshotService, delete_notification_traces
from apps.properties.enums import Feature
from apps.properties.models import Property
from apps.properties.services import FeatureGate

DOCUMENT_FIELDS = ("title", "description")


class DocumentService:
    @staticmethod
    def list_visible(
        *, actor, prop: Property, folder_id: int | None = None, search: str | None = None
    ) -> QuerySet[LibraryDocument]:
        if not DocumentPolicy.can_list(actor, prop):
            raise PermissionDenied("You have no link with this property.")
        FeatureGate.require(prop, Feature.LIBRARY)
        qs = (
            LibraryDocument.objects.filter(property=prop)
            .filter(DocumentPolicy.visible_filter(actor))
            .select_related("folder", "created_by")
        )
        if folder_id is not None:
            qs = qs.filter(folder_id=folder_id)
        if search:
            qs = qs.filter(title__icontains=search)
        return qs

    @staticmethod
    def get_visible(*, actor, prop: Property, document_id: int) -> LibraryDocument:
        document = (
            LibraryDocument.objects.filter(pk=document_id, property=prop)
            .filter(DocumentPolicy.visible_filter(actor))
            .select_related("folder", "property", "created_by")
            .first()
        )
        if document is None:
            raise NotFound("Document not found.")
        return document

    @staticmethod
    @transaction.atomic
    def publish(
        *, actor, folder: Folder, title: str, target_roles: list[str], upload, description: str = ""
    ) -> LibraryDocument:
        prop = folder.property
        if not DocumentPolicy.can_publish(actor, prop):
            raise PermissionDenied("Only the property management can publish documents.")
        FeatureGate.require(prop, Feature.LIBRARY)
        roles = SnapshotService.validate_target_roles(target_roles)
        document = LibraryDocument.objects.create(
            folder=folder,
            property=prop,
            title=title.strip(),
            description=description,
            target_roles=roles,
            created_by=actor,
        )
        AttachmentService.attach_one(
            entity_type=EntityType.LIBRARY_DOCUMENT,
            entity_id=document.pk,
            upload=upload,
            uploaded_by=actor,
        )
        recipients = SnapshotService.freeze(target=document, prop=prop, target_roles=roles)
        AuditService.record(
            actor=actor,
            action=LibraryAudit.DOCUMENT_PUBLISHED,
            target=document,
            property_id=prop.pk,
        )
        notices.document_published(document, recipients=recipients, actor=actor)
        return document

    @staticmethod
    @transaction.atomic
    def update(*, actor, document: LibraryDocument, changes: dict) -> LibraryDocument:
        if not DocumentPolicy.can_update(actor, document):
            raise PermissionDenied("Only the property management can edit documents.")
        fields = apply_changes(document, changes, DOCUMENT_FIELDS)
        if "folder" in changes:
            folder = changes["folder"]
            if folder.property_id != document.property_id:
                raise InvalidInput("The folder belongs to another property.", field="folder_id")
            document.folder = folder
            fields.append("folder")
        if fields:
            document.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=LibraryAudit.DOCUMENT_UPDATED,
                target=document,
                property_id=document.property_id,
            )
        return document

    @staticmethod
    @transaction.atomic
    def replace_file(*, actor, document: LibraryDocument, upload) -> None:
        if not DocumentPolicy.can_update(actor, document):
            raise PermissionDenied("Only the property management can edit documents.")
        AttachmentService.attach_one(
            entity_type=EntityType.LIBRARY_DOCUMENT,
            entity_id=document.pk,
            upload=upload,
            uploaded_by=actor,
        )

    @staticmethod
    @transaction.atomic
    def delete(*, actor, document: LibraryDocument) -> None:
        if not DocumentPolicy.can_delete(actor, document):
            raise PermissionDenied("Only the property management can delete documents.")
        AuditService.record(
            actor=actor,
            action=LibraryAudit.DOCUMENT_DELETED,
            target=document,
            property_id=document.property_id,
        )
        AttachmentService.delete_for_entity(EntityType.LIBRARY_DOCUMENT, document.pk)
        delete_notification_traces(document)
        document.delete()
