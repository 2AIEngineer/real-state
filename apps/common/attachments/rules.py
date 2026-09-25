"""What each kind of file may be: its formats, how many, how big, and which record owns it.

Every file belongs to one entity, named by its type and its id (`EntityType`).
The type also says which slot of the record the file fills (a lease member has
a proof of identity and a proof of address: two types). For each type, `RULES`
fixes the accepted formats, the maximum number of files, the maximum size of
one file, and the model that owns the files. When the maximum is 1, a new upload
replaces the current file.

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
    # The model the files belong to ("app_label.Model"): when one of its rows is
    # deleted, directly or by cascade, its files go with it (`apps.common.deletion`).
    owner: str

    def describe_types(self) -> str:
        return ", ".join(sorted(t.split("/")[-1] for t in self.allowed_types))


def _rule(types, *, owner: str, files: int, mb: int) -> AttachmentRule:
    return AttachmentRule(types, max_files=files, max_size_bytes=mb * MB, owner=owner)


RULES: dict[str, AttachmentRule] = {
    EntityType.SYNDICAT_LOGO: _rule(IMAGES, owner="properties.Syndicat", files=1, mb=10),
    EntityType.PROPERTY_LOGO: _rule(IMAGES, owner="properties.Property", files=1, mb=10),
    EntityType.AMENITY: _rule(IMAGES, owner="amenities.Amenity", files=20, mb=10),
    EntityType.PRODUCT: _rule(IMAGES, owner="store.Product", files=20, mb=10),
    EntityType.MARKETPLACE_LISTING: _rule(
        IMAGES, owner="marketplace.MarketplaceListing", files=20, mb=10
    ),
    EntityType.ANNOUNCEMENT: _rule(DOCUMENTS, owner="announcements.Announcement", files=30, mb=25),
    EntityType.EVENT: _rule(DOCUMENTS, owner="events.Event", files=30, mb=25),
    EntityType.SURVEY: _rule(DOCUMENTS, owner="surveys.Survey", files=30, mb=25),
    EntityType.LIBRARY_DOCUMENT: _rule(DOCUMENTS, owner="library.LibraryDocument", files=1, mb=25),
    EntityType.SERVICE_REQUEST: _rule(
        PHOTOS_AND_PDF, owner="service_requests.ServiceRequest", files=30, mb=20
    ),
    EntityType.SERVICE_REQUEST_RESOLUTION: _rule(
        PHOTOS_AND_PDF, owner="service_requests.ServiceRequestAssignment", files=30, mb=20
    ),
    EntityType.WORK_ORDER: _rule(PHOTOS_AND_PDF, owner="work_orders.WorkOrder", files=30, mb=20),
    EntityType.LEASE_COMPONENT_STATE: _rule(
        PHOTOS_AND_PDF, owner="leasing.LeaseComponentState", files=30, mb=20
    ),
    EntityType.LEASE_MEMBER_IDENTITY: _rule(
        PHOTOS_AND_PDF, owner="leasing.LeaseMember", files=1, mb=10
    ),
    EntityType.LEASE_MEMBER_ADDRESS: _rule(
        PHOTOS_AND_PDF, owner="leasing.LeaseMember", files=1, mb=10
    ),
    EntityType.VISITOR_ID_CARD: _rule(PHOTOS_AND_PDF, owner="visitors.Visitor", files=1, mb=10),
    EntityType.SHORT_TERM_RENTAL_MEMBER_ID_CARD: _rule(
        PHOTOS_AND_PDF, owner="short_term_rental.ShortTermRentalMember", files=1, mb=10
    ),
    # One file per chat message: png, jpeg or pdf.
    EntityType.CHAT_MESSAGE: _rule(
        frozenset({"image/png", "image/jpeg", "application/pdf"}),
        owner="chat.ChatMessage",
        files=1,
        mb=10,
    ),
}


def entity_types_owned_by(model_label: str) -> tuple[str, ...]:
    return tuple(t for t, rule in RULES.items() if rule.owner == model_label)


# Types holding a single file (a new upload replaces it).
SINGLE_FILE_TYPES: tuple[str, ...] = tuple(
    sorted(t for t, rule in RULES.items() if rule.max_files == 1)
)
