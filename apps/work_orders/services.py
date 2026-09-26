"""Internal work orders on a property, building or unit.

OPEN ──start──▶ IN_PROGRESS ──complete──▶ COMPLETED
OPEN | IN_PROGRESS ⇄ ON_HOLD
OPEN | IN_PROGRESS | ON_HOLD ──cancel──▶ CANCELLED
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.accounts.enums import StructuralRole
from apps.accounts.services.authorization import AccessService
from apps.common.attachments.rules import EntityType
from apps.common.attachments.service import AttachmentService
from apps.common.db import apply_changes
from apps.common.deletion import destroy
from apps.common.exceptions import (
    InvalidInput,
    InvalidTransition,
    NotFound,
    PermissionDenied,
)
from apps.common.services.audit import AuditService
from apps.properties.models import Building, Property, Unit
from apps.service_requests.models import ServiceRequest
from apps.work_orders import notices
from apps.work_orders.audit import WorkOrderAudit
from apps.work_orders.models import WorkOrder, WorkOrderStatus
from apps.work_orders.policies import WorkOrderPolicy

EDITABLE_FIELDS = (
    "title",
    "description",
    "category",
    "priority",
    "scheduled_start",
    "scheduled_end",
    "due_date",
)
TERMINAL = (WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED)

TRANSITIONS: dict[str, tuple[str, ...]] = {
    "start": (WorkOrderStatus.OPEN, WorkOrderStatus.ON_HOLD),
    "hold": (WorkOrderStatus.OPEN, WorkOrderStatus.IN_PROGRESS),
    "complete": (WorkOrderStatus.IN_PROGRESS,),
    "cancel": (
        WorkOrderStatus.OPEN,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.ON_HOLD,
    ),
}


def _building_of(wo: WorkOrder) -> Building | None:
    """The building a work order concerns, if any (directly or through its unit)."""
    return wo.unit.building if wo.unit else wo.building


class WorkOrderService:
    @staticmethod
    def list_visible(
        *,
        actor,
        property_id: int,
        status: str | None = None,
        assigned_to_me: bool = False,
    ) -> QuerySet[WorkOrder]:
        qs = WorkOrder.objects.filter(
            WorkOrderPolicy.visible_filter(actor)
        ).select_related("property", "building", "unit", "assignee")
        if assigned_to_me:
            qs = qs.filter(assignee=actor)
        qs = qs.filter(property_id=property_id)
        if status:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def get_visible(*, actor, prop: Property, work_order_id: int) -> WorkOrder:
        wo = (
            WorkOrder.objects.select_related("property", "building", "unit", "assignee")
            .filter(pk=work_order_id, property=prop)
            .first()
        )
        if wo is None or not WorkOrderPolicy.can_view(actor, wo):
            raise NotFound("Work order not found.")
        return wo

    @staticmethod
    def _check_assignee(assignee, prop: Property, building: Building | None) -> None:
        """Who can carry out a work order:

        - a provider: they form a platform-wide pool, attached to no place;
        - the maintenance of the property;
        - the security or cleaning of the building, when the order concerns one.
        """
        if assignee is None:
            return
        if assignee.role == StructuralRole.PROVIDER and assignee.is_active:
            return
        if AccessService.is_maintenance_of(assignee, prop):
            return
        if building is not None and (
            AccessService.is_security_of(assignee, building)
            or AccessService.is_cleaning_of(assignee, building)
        ):
            return
        raise InvalidInput(
            "The assignee does not work on this property or building.",
            field="assignee_id",
        )

    @staticmethod
    @transaction.atomic
    def create(
        *,
        actor,
        prop: Property,
        title: str,
        building: Building | None = None,
        unit: Unit | None = None,
        service_request: ServiceRequest | None = None,
        assignee=None,
        data: dict | None = None,
        files=(),
    ) -> WorkOrder:
        if not WorkOrderPolicy.can_create(actor, prop):
            raise PermissionDenied(
                "Only the property management can create work orders."
            )
        if unit is not None:
            building = building or unit.building
            if unit.building_id != building.pk:
                raise InvalidInput("The unit is not in this building.", field="unit_id")
        if building is not None and building.property_id != prop.pk:
            raise InvalidInput(
                "The building belongs to another property.", field="building_id"
            )
        if service_request is not None and service_request.property_id != prop.pk:
            raise InvalidInput(
                "The service request belongs to another property.",
                field="service_request_id",
            )
        wo = WorkOrder(
            property=prop,
            building=building,
            unit=unit,
            service_request=service_request,
            title=title.strip(),
            created_by=actor,
        )
        apply_changes(wo, data or {}, EDITABLE_FIELDS)
        WorkOrderService._check_assignee(
            assignee, prop, unit.building if unit else building
        )
        wo.assignee = assignee
        if (
            wo.scheduled_start
            and wo.scheduled_end
            and wo.scheduled_end <= wo.scheduled_start
        ):
            raise InvalidInput(
                "The scheduled end must follow the start.", field="scheduled_end"
            )
        wo.save()
        AttachmentService.attach(
            entity_type=EntityType.WORK_ORDER,
            entity_id=wo.pk,
            files=list(files),
            uploaded_by=actor,
        )
        AuditService.record(
            actor=actor, action=WorkOrderAudit.CREATED, target=wo, property_id=prop.pk
        )
        notices.assigned(wo, actor=actor)
        return wo

    @staticmethod
    def _lock(wo: WorkOrder) -> WorkOrder:
        return (
            WorkOrder.objects.select_for_update(of=("self",))
            .select_related("property", "building", "unit", "assignee")
            .get(pk=wo.pk)
        )

    @staticmethod
    @transaction.atomic
    def update(*, actor, wo: WorkOrder, changes: dict) -> WorkOrder:
        if not WorkOrderPolicy.can_update(actor, wo):
            raise PermissionDenied("Only the property management can edit work orders.")
        wo = WorkOrderService._lock(wo)
        if wo.status in TERMINAL:
            raise InvalidTransition("A closed work order cannot be modified.")
        fields = apply_changes(wo, changes, EDITABLE_FIELDS)
        reassigned = False
        if "assignee" in changes and changes["assignee"] != wo.assignee:
            WorkOrderService._check_assignee(
                changes["assignee"], wo.property, _building_of(wo)
            )
            wo.assignee = changes["assignee"]
            fields.append("assignee")
            reassigned = True
        if (
            wo.scheduled_start
            and wo.scheduled_end
            and wo.scheduled_end <= wo.scheduled_start
        ):
            raise InvalidInput(
                "The scheduled end must follow the start.", field="scheduled_end"
            )
        if fields:
            wo.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=WorkOrderAudit.UPDATED,
                target=wo,
                property_id=wo.property_id,
                metadata={"fields": fields},
            )
        if reassigned:
            notices.assigned(wo, actor=actor)
        return wo

    @staticmethod
    @transaction.atomic
    def transition(*, actor, wo: WorkOrder, action: str, note: str = "") -> WorkOrder:
        wo = WorkOrderService._lock(wo)
        if not WorkOrderPolicy.can_view(actor, wo):
            raise NotFound("Work order not found.")
        if action == "cancel" and not WorkOrderPolicy.can_cancel(actor, wo):
            raise PermissionDenied("Only management can cancel a work order.")
        if action != "cancel" and not WorkOrderPolicy.can_progress(actor, wo):
            raise PermissionDenied(
                "Only management or the assignee can move this work order forward."
            )
        if action not in TRANSITIONS:
            raise InvalidInput("Unknown action.", field="action")
        if wo.status not in TRANSITIONS[action]:
            raise InvalidTransition(
                f"Cannot {action} a work order that is {wo.status.lower()}."
            )
        now = timezone.now()
        fields = ["status"]
        if action == "start":
            wo.status = WorkOrderStatus.IN_PROGRESS
            if wo.started_at is None:
                wo.started_at = now
                fields.append("started_at")
        elif action == "hold":
            wo.status = WorkOrderStatus.ON_HOLD
        elif action == "complete":
            wo.status = WorkOrderStatus.COMPLETED
            wo.completed_at = now
            wo.completion_note = note
            fields += ["completed_at", "completion_note"]
        else:
            wo.status = WorkOrderStatus.CANCELLED
            wo.cancelled_at = now
            wo.cancellation_reason = note
            fields += ["cancelled_at", "cancellation_reason"]
        wo.save(update_fields=[*fields, "updated_at"])
        AuditService.record(
            actor=actor,
            action=WorkOrderAudit(f"work_order.{action}"),
            target=wo,
            property_id=wo.property_id,
        )
        return wo

    @staticmethod
    @transaction.atomic
    def delete(*, actor, wo: WorkOrder) -> None:
        """Permanent removal of a work order and its files."""
        if not WorkOrderPolicy.can_delete(actor, wo):
            raise PermissionDenied(
                "Only the property management can delete work orders."
            )
        AuditService.record(
            actor=actor,
            action=WorkOrderAudit.DELETED,
            target=wo,
            property_id=wo.property_id,
            metadata={"status": wo.status, "title": wo.title},
        )
        destroy(wo)

    @staticmethod
    @transaction.atomic
    def add_files(*, actor, wo: WorkOrder, files) -> list:
        if not WorkOrderPolicy.can_add_files(actor, wo):
            raise NotFound("Work order not found.")
        return AttachmentService.attach(
            entity_type=EntityType.WORK_ORDER,
            entity_id=wo.pk,
            files=list(files),
            uploaded_by=actor,
        )
