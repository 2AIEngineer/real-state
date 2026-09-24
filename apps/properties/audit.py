"""Actions this module writes in the audit journal."""

from enum import StrEnum


class BuildingAudit(StrEnum):
    CREATED = "building.created"
    DELETED = "building.deleted"
    UPDATED = "building.updated"


class OwnershipAudit(StrEnum):
    CO_OWNER_ADDED = "ownership.co_owner_added"
    DELETED = "ownership.deleted"
    ENDED = "ownership.ended"
    TRANSFERRED = "ownership.transferred"


class PromoterAudit(StrEnum):
    CREATED = "promoter.created"
    DELETED = "promoter.deleted"
    UPDATED = "promoter.updated"


class PropertyAudit(StrEnum):
    CREATED = "property.created"
    DELETED = "property.deleted"
    FEATURES_CHANGED = "property.features_changed"
    PROMOTER_CHANGED = "property.promoter_changed"
    UPDATED = "property.updated"


class SyndicatAudit(StrEnum):
    CREATED = "syndicat.created"
    DELETED = "syndicat.deleted"
    UPDATED = "syndicat.updated"


class UnitAudit(StrEnum):
    CREATED = "unit.created"
    DELETED = "unit.deleted"
    UPDATED = "unit.updated"
