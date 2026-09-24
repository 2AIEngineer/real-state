"""Who may do what in the document library.

Folders are visible to everyone linked to the property; documents only to
the roles they target. Management organises folders and documents.
"""

from django.db.models import Q

from apps.accounts.services.authorization import AccessService
from apps.accounts.services.visibility import readable_property_records
from apps.library.models import Folder, LibraryDocument
from apps.properties.models import Property


class FolderPolicy:
    @staticmethod
    def can_list(user, prop: Property) -> bool:
        return AccessService.is_staff_or_resident_of_property(user, prop)

    @staticmethod
    def can_view(user, folder: Folder) -> bool:
        return AccessService.is_staff_or_resident_of_property(user, folder.property)

    @staticmethod
    def can_create(user, prop: Property) -> bool:
        return AccessService.manages_property(user, prop)

    @staticmethod
    def can_update(user, folder: Folder) -> bool:
        return AccessService.manages_property(user, folder.property)

    @staticmethod
    def can_delete(user, folder: Folder) -> bool:
        return AccessService.manages_property(user, folder.property)


class DocumentPolicy:
    @staticmethod
    def visible_filter(user) -> Q:
        """Documents addressed to one of the user's roles (all for management)."""
        return readable_property_records(user)

    @staticmethod
    def can_list(user, prop: Property) -> bool:
        return AccessService.is_staff_or_resident_of_property(user, prop)

    @staticmethod
    def can_view(user, document: LibraryDocument) -> bool:
        return (
            LibraryDocument.objects.filter(pk=document.pk)
            .filter(DocumentPolicy.visible_filter(user))
            .exists()
        )

    @staticmethod
    def can_publish(user, prop: Property) -> bool:
        return AccessService.manages_property(user, prop)

    @staticmethod
    def can_update(user, document: LibraryDocument) -> bool:
        """Editing the details, moving it, replacing its file."""
        return AccessService.manages_property(user, document.property)

    @staticmethod
    def can_delete(user, document: LibraryDocument) -> bool:
        return AccessService.manages_property(user, document.property)
