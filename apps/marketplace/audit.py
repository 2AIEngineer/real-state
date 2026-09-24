"""Actions this module writes in the audit journal."""

from enum import StrEnum


class MarketplaceAudit(StrEnum):
    LISTING_ARCHIVED = "marketplace.listing_archived"
    LISTING_DELETED = "marketplace.listing_deleted"
    LISTING_MODERATED = "marketplace.listing_moderated"
    LISTING_PUBLISHED = "marketplace.listing_published"
    LISTING_SOLD = "marketplace.listing_sold"
