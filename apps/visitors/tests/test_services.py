import pytest

from apps.common.exceptions import InvalidInput, InvalidTransition, NotFound, PermissionDenied
from apps.notifications.models import InboxNotification
from apps.visitors.models import VisitStatus
from apps.visitors.services import VisitorService
from tests import factories as f

pytestmark = pytest.mark.django_db


def register(world, actor=None, unit=None, **kwargs):
    return VisitorService.register(
        actor=actor or world.security,
        unit=unit or world.unit,
        first_name="Sam",
        last_name="Lee",
        **kwargs,
    )


def test_security_logs_visitors_in_their_building_only(world):
    register(world, id_card=f.png())
    with pytest.raises(PermissionDenied):
        register(world, unit=world.other_unit)


def test_owners_and_tenants_are_notified_and_can_read(world):
    visitor = register(world)
    assert InboxNotification.objects.filter(
        notification_type="visitor.arrived", user=world.tenant
    ).exists()
    assert VisitorService.get_visible(actor=world.owner, visitor_id=visitor.pk) == visitor
    with pytest.raises(NotFound):
        VisitorService.get_visible(actor=world.outsider, visitor_id=visitor.pk)


def test_owners_and_tenants_cannot_log_visitors(world):
    with pytest.raises(PermissionDenied):
        register(world, actor=world.tenant)


def test_denial_requires_a_reason(world):
    with pytest.raises(InvalidInput):
        register(world, admitted=False)
    assert register(world, admitted=False, denial_reason="No ID").status == VisitStatus.DENIED


def test_departure(world):
    visitor = VisitorService.mark_left(actor=world.security, visitor=register(world))
    assert visitor.status == VisitStatus.LEFT and visitor.left_at >= visitor.arrived_at
    with pytest.raises(InvalidTransition):
        VisitorService.mark_left(actor=world.security, visitor=visitor)


def test_cleaning_staff_of_the_building_see_no_visitor(world):
    register(world)
    cleaner = f.make_user()
    f.assign_role(cleaner, "cleaning", world.building)
    assert list(VisitorService.list_visible(actor=cleaner, property_id=world.prop.pk)) == []
    with pytest.raises(PermissionDenied):
        register(world, actor=cleaner)
