"""What people are told about work orders."""

from __future__ import annotations

from apps.notifications.models import NotificationCategory
from apps.notifications.services import NotificationIntent, NotificationService
from apps.work_orders.models import WorkOrder


def assigned(wo: WorkOrder, *, actor) -> None:
    """Tell the assignee, if there is one, that the work order is theirs."""
    if wo.assignee_id is None:
        return
    NotificationService.notify(
        NotificationIntent(
            event_type="work_order.assigned",
            category=NotificationCategory.WORK_ORDER,
            title=f"Ordre de travail #{wo.pk}",
            body=f"« {wo.title} » vous a été assigné.",
            to=[wo.assignee],
            target=wo,
            exclude=[actor],
            include_platform_admins=False,
            data={"work_order_id": wo.pk, "property_id": wo.property_id},
            action_path=f"/work-orders/{wo.pk}",
        )
    )
