"""Actions this module writes in the audit journal."""

from enum import StrEnum


class WorkOrderAudit(StrEnum):
    CANCEL = "work_order.cancel"
    COMPLETE = "work_order.complete"
    CREATED = "work_order.created"
    DELETED = "work_order.deleted"
    HOLD = "work_order.hold"
    START = "work_order.start"
    UPDATED = "work_order.updated"
