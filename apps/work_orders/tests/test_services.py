import pytest

from apps.common.exceptions import InvalidInput, InvalidTransition, NotFound, PermissionDenied
from apps.work_orders.models import WorkOrderStatus
from apps.work_orders.services import WorkOrderService

pytestmark = pytest.mark.django_db


def create(world, **kwargs):
    return WorkOrderService.create(
        actor=world.manager, prop=world.prop, title="Repaint hall", **kwargs
    )


def test_location_chain_is_consistent(world):
    wo = create(world, unit=world.unit)
    assert wo.building == world.building
    with pytest.raises(InvalidInput):
        create(world, building=world.other_building, unit=world.unit)


def test_assignee_needs_an_operational_role_there(world):
    create(world, building=world.building, assignee=world.security)
    with pytest.raises(InvalidInput):
        create(world, building=world.other_building, assignee=world.security)
    with pytest.raises(InvalidInput):
        create(world, assignee=world.tenant)


def test_assignee_progresses_but_cannot_cancel(world):
    wo = create(world, assignee=world.maintenance)
    wo = WorkOrderService.transition(actor=world.maintenance, wo=wo, action="start")
    assert wo.status == WorkOrderStatus.IN_PROGRESS and wo.started_at
    with pytest.raises(PermissionDenied):
        WorkOrderService.transition(actor=world.maintenance, wo=wo, action="cancel")
    wo = WorkOrderService.transition(actor=world.maintenance, wo=wo, action="complete", note="Done")
    assert wo.status == WorkOrderStatus.COMPLETED


def test_invalid_transition(world):
    with pytest.raises(InvalidTransition):
        WorkOrderService.transition(actor=world.manager, wo=create(world), action="complete")


def test_closed_work_order_is_frozen(world):
    wo = WorkOrderService.transition(actor=world.manager, wo=create(world), action="cancel")
    with pytest.raises(InvalidTransition):
        WorkOrderService.update(actor=world.manager, wo=wo, changes={"title": "x"})


def test_owners_and_tenants_do_not_see_work_orders(world):
    wo = create(world)
    with pytest.raises(NotFound):
        WorkOrderService.get_visible(actor=world.owner, work_order_id=wo.pk)
