"""Document library: a folder tree per property, documents addressed to target roles."""

from apps.library.services.documents import DocumentService
from apps.library.services.folders import FolderService

__all__ = ["DocumentService", "FolderService"]
