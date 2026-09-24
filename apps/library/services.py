"""Document library: folder tree per property and documents addressed to target roles."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Count, QuerySet

from apps.common.db import apply_changes, translate_integrity_errors
from apps.common.exceptions import BusinessRuleViolation, InvalidInput, NotFound, PermissionDenied
from apps.common.files.rules import EntityType
from apps.common.files.service import AttachmentService
from apps.common.services.audit import AuditService
from apps.library import errors, notices
from apps.library.audit import LibraryAudit
from apps.library.models import Folder, LibraryDocument
from apps.library.policies import DocumentPolicy, FolderPolicy
from apps.notifications.services import SnapshotService, delete_notification_traces
from apps.properties.enums import Feature
from apps.properties.models import Property
from apps.properties.services import FeatureGate

DEFAULT_FOLDERS: tuple[tuple[str, str], ...] = (
    ("Notices and communication", "Avis et communication"),
    ("Rules and bylaws", "Règlements et statuts"),
    ("Meeting minutes", "Procès-verbaux"),
    ("Forms", "Formulaires"),
    ("Declarations", "Déclarations"),
    ("Service providers", "Prestataires de services"),
)
FOLDER_FIELDS = ("en_name", "fr_name", "description")
DOCUMENT_FIELDS = ("title", "description")
FOLDER_CONSTRAINTS = {
    "folder_en_name_per_parent": errors.folder_name_taken,
    "folder_fr_name_per_parent": errors.folder_name_taken,
}


class FolderService:
    @staticmethod
    def create_default_folders(*, prop: Property) -> list[Folder]:
        return Folder.objects.bulk_create(
            [
                Folder(property=prop, en_name=en, fr_name=fr, is_system=True)
                for en, fr in DEFAULT_FOLDERS
            ],
            ignore_conflicts=True,
        )

    @staticmethod
    def delete_system_folders(*, prop: Property) -> int:
        """Remove the folders seeded with the property, if still empty.

        Called when the property itself is deleted: user-made folders and any
        folder holding documents stay and block the deletion.
        """
        deleted = 0
        for folder in Folder.objects.filter(property=prop, is_system=True):
            if folder.subfolders.exists() or folder.documents.exists():
                continue
            folder.delete()
            deleted += 1
        return deleted

    @staticmethod
    def list_for_property(
        *, actor, prop: Property, parent_id: int | None = None, root_only: bool = False
    ) -> QuerySet[Folder]:
        if not FolderPolicy.can_list(actor, prop):
            raise PermissionDenied("You have no link with this property.")
        FeatureGate.require(prop, Feature.LIBRARY)
        # An aggregate drops `Meta.ordering`: say it again, or pages are not stable.
        qs = (
            Folder.objects.filter(property=prop)
            .annotate(subfolders_count=Count("subfolders", distinct=True))
            .order_by(*Folder._meta.ordering)
        )
        if parent_id is not None:
            qs = qs.filter(parent_folder_id=parent_id)
        elif root_only:
            qs = qs.filter(parent_folder__isnull=True)
        return qs

    @staticmethod
    def get_visible(*, actor, prop: Property, folder_id: int) -> Folder:
        folder = (
            Folder.objects.select_related("property").filter(pk=folder_id, property=prop).first()
        )
        if folder is None or not FolderPolicy.can_view(actor, folder):
            raise NotFound("Folder not found.")
        return folder

    @staticmethod
    def _check_parent(folder: Folder | None, parent: Folder | None, prop: Property) -> None:
        if parent is None:
            return
        if parent.property_id != prop.pk:
            raise InvalidInput(
                "The parent folder belongs to another property.", field="parent_folder_id"
            )
        if folder is None:
            return
        ancestor = parent
        while ancestor is not None:
            if ancestor.pk == folder.pk:
                raise InvalidInput(
                    "A folder cannot be moved inside itself.", field="parent_folder_id"
                )
            ancestor = ancestor.parent_folder

    @staticmethod
    @transaction.atomic
    def create(
        *,
        actor,
        prop: Property,
        en_name: str,
        fr_name: str,
        parent: Folder | None = None,
        description: str = "",
    ) -> Folder:
        if not FolderPolicy.can_create(actor, prop):
            raise PermissionDenied("Only the property management can create folders.")
        FeatureGate.require(prop, Feature.LIBRARY)
        FolderService._check_parent(None, parent, prop)
        with translate_integrity_errors(FOLDER_CONSTRAINTS):
            folder = Folder.objects.create(
                property=prop,
                parent_folder=parent,
                en_name=en_name.strip(),
                fr_name=fr_name.strip(),
                description=description,
                created_by=actor,
            )
        AuditService.record(
            actor=actor, action=LibraryAudit.FOLDER_CREATED, target=folder, property_id=prop.pk
        )
        return folder

    @staticmethod
    @transaction.atomic
    def update(*, actor, folder: Folder, changes: dict) -> Folder:
        if not FolderPolicy.can_update(actor, folder):
            raise PermissionDenied("Only the property management can edit folders.")
        fields = apply_changes(folder, changes, FOLDER_FIELDS)
        if "parent_folder" in changes:
            FolderService._check_parent(folder, changes["parent_folder"], folder.property)
            folder.parent_folder = changes["parent_folder"]
            fields.append("parent_folder")
        if fields:
            with translate_integrity_errors(FOLDER_CONSTRAINTS):
                folder.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=LibraryAudit.FOLDER_UPDATED,
                target=folder,
                property_id=folder.property_id,
            )
        return folder

    @staticmethod
    @transaction.atomic
    def delete(*, actor, folder: Folder) -> None:
        if not FolderPolicy.can_delete(actor, folder):
            raise PermissionDenied("Only the property management can delete folders.")
        if folder.is_system:
            raise BusinessRuleViolation("Default folders cannot be deleted.", code="system_folder")
        if folder.subfolders.exists() or folder.documents.exists():
            raise BusinessRuleViolation(
                "Only empty folders can be deleted.", code="folder_not_empty"
            )
        AuditService.record(
            actor=actor,
            action=LibraryAudit.FOLDER_DELETED,
            target=folder,
            property_id=folder.property_id,
        )
        folder.delete()


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
