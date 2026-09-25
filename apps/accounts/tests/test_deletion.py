"""Deleting an account is total; deactivating is the alternative that keeps it."""

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.services.status import AccountStatusService
from apps.announcements.services import AnnouncementService
from apps.common.exceptions import BusinessRuleViolation, PermissionDenied
from apps.leasing.models import Lease, LeaseMember, LeaseStatus
from apps.properties.models import OwnershipStatus, UnitOwnership
from apps.service_requests.models import ServiceRequest
from apps.service_requests.services import ServiceRequestService

pytestmark = pytest.mark.django_db
User = get_user_model()


def delete(world, user):
    AccountStatusService.delete(actor=world.admin, user=user)


def test_the_account_and_what_is_theirs_are_gone(world):
    sr = ServiceRequestService.submit(
        actor=world.tenant, prop=world.prop, title="Leak", description="d", category="plumbing"
    )

    delete(world, world.tenant)

    assert not User.objects.filter(pk=world.tenant.pk).exists()
    assert not ServiceRequest.objects.filter(pk=sr.pk).exists()
    assert not LeaseMember.objects.filter(user_id=world.tenant.pk).exists()


def test_what_they_wrote_for_the_residence_stays_without_author(world):
    announcement = AnnouncementService.publish(
        actor=world.manager,
        prop=world.prop,
        title="AGM",
        body="Friday",
        target_roles=["owner"],
        category="general",
    )

    delete(world, world.manager)

    announcement.refresh_from_db()
    assert announcement.created_by is None


def test_a_unit_left_without_owner_reverts_to_its_promoter(world):
    delete(world, world.owner)

    active = UnitOwnership.objects.filter(unit=world.unit, status=OwnershipStatus.ACTIVE)
    assert active.count() == 1 and active.get().is_promoter_default


def test_a_lease_left_without_occupant_ends(world):
    delete(world, world.tenant)
    assert Lease.objects.get(pk=world.lease.pk).status == LeaseStatus.ACTIVE  # co-tenant stays

    delete(world, world.co_tenant)
    assert Lease.objects.get(pk=world.lease.pk).status != LeaseStatus.ACTIVE


def test_nobody_deletes_their_own_account(world):
    for actor in (world.admin, world.syndic, world.manager):
        with pytest.raises((PermissionDenied, BusinessRuleViolation)):
            AccountStatusService.delete(actor=actor, user=actor)


def test_a_manager_deletes_an_account_of_their_property(world):
    AccountStatusService.delete(actor=world.manager, user=world.tenant)
    assert not User.objects.filter(pk=world.tenant.pk).exists()


def test_technical_accounts_go_with_their_promoter(world):
    with pytest.raises(BusinessRuleViolation):
        delete(world, world.prop.promoter.representative_user)


def test_delete_over_http(api, world):
    response = api(world.admin).delete(f"/api/v1/users/{world.outsider.pk}/")

    assert response.status_code == 204
    assert not User.objects.filter(pk=world.outsider.pk).exists()
