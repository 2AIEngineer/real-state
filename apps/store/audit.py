"""Actions this module writes in the audit journal."""

from enum import StrEnum


class StoreAudit(StrEnum):
    ORDER_CANCELLED = "store.order_cancelled"
    ORDER_CONFIRMED = "store.order_confirmed"
    ORDER_DELETED = "store.order_deleted"
    ORDER_DELIVERED = "store.order_delivered"
    ORDER_PLACED = "store.order_placed"
    PRODUCT_CREATED = "store.product_created"
    PRODUCT_DELETED = "store.product_deleted"
    PRODUCT_UPDATED = "store.product_updated"
