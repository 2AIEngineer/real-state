"""What each kind of file may be: its formats, how many, how big, and who may read it.

Every file belongs to one entity, named by its type and its id (`EntityType`).
The type also says which slot of the record the file fills (a lease member has
a proof of identity and a proof of address: two types). For each type, `RULES`
fixes the accepted formats, the maximum number of files, the maximum size of
one file, and whether the file is public. When the maximum is 1, a new upload
replaces the current file.

A *public* file (a logo, a product photo) has a link that never expires. Every
other file is private: its link is personal and expires (see `links.py`).
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import models

MB = 1024 * 1024

IMAGES = frozenset({"image/jpeg", "image/png", "image/webp", "image/heic"})
PDF = frozenset({"application/pdf"})
OFFICE = frozenset(
    {
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
)
TEXT = frozenset({"text/csv", "text/plain"})
DOCUMENTS = IMAGES | PDF | OFFICE | TEXT
PHOTOS_AND_PDF = IMAGES | PDF

# The stored name ends with the extension of the *detected* format, never with
# the one the client sent: a PDF named `x.html` is stored and served as a PDF.
EXTENSIONS: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/csv": ".csv",
    "text/plain": ".txt",
}

# Formats a browser shows by itself; the others are downloaded.
SHOWN_INLINE = IMAGES | PDF | TEXT


class EntityType(models.TextChoices):
    SYNDICAT_LOGO = "syndicat_logo", "Syndicat logo"
    PROPERTY_LOGO = "property_logo", "Property logo"
    ANNOUNCEMENT = "announcement", "Announcement files"
    EVENT = "event", "Event files"
    SURVEY = "survey", "Survey files"
    LIBRARY_DOCUMENT = "library_document", "Library document file"
    AMENITY = "amenity", "Amenity images"
    PRODUCT = "product", "Store product images"
    MARKETPLACE_LISTING = "marketplace_listing", "Marketplace listing images"
    SERVICE_REQUEST = "service_request", "Service request files"
    SERVICE_REQUEST_RESOLUTION = (
        "service_request_resolution",
        "Resolution evidence of a service request round",
    )
    WORK_ORDER = "work_order", "Work order files"
    LEASE_COMPONENT_STATE = "lease_component_state", "Inspection files"
    LEASE_MEMBER_IDENTITY = "lease_member_identity", "Lease member proof of identity"
    LEASE_MEMBER_ADDRESS = "lease_member_address", "Lease member proof of address"
    VISITOR_ID_CARD = "visitor_id_card", "Visitor identity card"
    SHORT_TERM_RENTAL_MEMBER_ID_CARD = (
        "short_term_rental_member_id_card",
        "Short-term rental member identity card",
    )
    CHAT_MESSAGE = "chat_message", "Chat message file"


@dataclass(frozen=True)
class AttachmentRule:
    allowed_types: frozenset[str]
    max_files: int
    max_size_bytes: int
    public: bool = False

    def describe_types(self) -> str:
        return ", ".join(sorted(t.split("/")[-1] for t in self.allowed_types))


def _rule(types, *, files: int, mb: int, public: bool = False) -> AttachmentRule:
    return AttachmentRule(types, max_files=files, max_size_bytes=mb * MB, public=public)


RULES: dict[str, AttachmentRule] = {
    # Public: shown to anyone who has the link (branding and catalogue pictures).
    EntityType.SYNDICAT_LOGO: _rule(IMAGES, files=1, mb=10, public=True),
    EntityType.PROPERTY_LOGO: _rule(IMAGES, files=1, mb=10, public=True),
    EntityType.AMENITY: _rule(IMAGES, files=20, mb=10, public=True),
    EntityType.PRODUCT: _rule(IMAGES, files=20, mb=10, public=True),
    EntityType.MARKETPLACE_LISTING: _rule(IMAGES, files=20, mb=10, public=True),
    # Private: residents' content and personal documents.
    EntityType.ANNOUNCEMENT: _rule(DOCUMENTS, files=30, mb=25),
    EntityType.EVENT: _rule(DOCUMENTS, files=30, mb=25),
    EntityType.SURVEY: _rule(DOCUMENTS, files=30, mb=25),
    EntityType.LIBRARY_DOCUMENT: _rule(DOCUMENTS, files=1, mb=25),
    EntityType.SERVICE_REQUEST: _rule(PHOTOS_AND_PDF, files=30, mb=20),
    EntityType.SERVICE_REQUEST_RESOLUTION: _rule(PHOTOS_AND_PDF, files=30, mb=20),
    EntityType.WORK_ORDER: _rule(PHOTOS_AND_PDF, files=30, mb=20),
    EntityType.LEASE_COMPONENT_STATE: _rule(PHOTOS_AND_PDF, files=30, mb=20),
    EntityType.LEASE_MEMBER_IDENTITY: _rule(PHOTOS_AND_PDF, files=1, mb=10),
    EntityType.LEASE_MEMBER_ADDRESS: _rule(PHOTOS_AND_PDF, files=1, mb=10),
    EntityType.VISITOR_ID_CARD: _rule(PHOTOS_AND_PDF, files=1, mb=10),
    EntityType.SHORT_TERM_RENTAL_MEMBER_ID_CARD: _rule(PHOTOS_AND_PDF, files=1, mb=10),
    # One file per chat message: png, jpeg or pdf.
    EntityType.CHAT_MESSAGE: _rule(
        frozenset({"image/png", "image/jpeg", "application/pdf"}), files=1, mb=10
    ),
}

# Types holding a single file (a new upload replaces it).
SINGLE_FILE_TYPES: tuple[str, ...] = tuple(
    sorted(t for t, rule in RULES.items() if rule.max_files == 1)
)
