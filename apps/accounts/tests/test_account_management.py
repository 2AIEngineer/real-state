"""Who manages which accounts: admins every role; syndics and managers the roles they handle.

| Actor   | Roles managed                                               |
|---------|-------------------------------------------------------------|
| admin   | all, admin and provider included                            |
| syndic  | syndic, manager, security, cleaning, maintenance, standard  |
| manager | manager, security, cleaning, maintenance, standard          |
"""

import pytest
from django.utils import timezone

from apps.accounts.enums import StructuralRole
from apps.accounts.models import UserProperty
from apps.accounts.policies import AccountPolicy, can_give_role
from apps.accounts.services.accounts import AccountService
from apps.accounts.services.status import AccountStatusService
from apps.common.exceptions import PermissionDenied
from tests import factories as f

pytestmark = pytest.mark.django_db

SYNDIC_ROLES = {"syndic", "manager", "security", "cleaning", "maintenance", "standard"}
MANAGER_ROLES = {"manager", "security", "cleaning", "maintenance", "standard"}


@pytest.mark.parametrize("role", StructuralRole.values)
def test_roles_each_actor_gives(world, role):
    assert can_give_role(world.admin, role)
    assert can_give_role(world.syndic, role) == (role in SYNDIC_ROLES)
    assert can_give_role(world.manager, role) == (role in MANAGER_ROLES)


def account_of_the_property(world, role):
    """An account with `role`, tied to the property the syndic and manager run."""
    user = f.make_user()
    target = {
        "syndic": world.syndicat,
        "manager": world.prop,
        "maintenance": world.prop,
        "security": world.building,
        "cleaning": world.building,
    }.get(role)
    f.assign_role(user, role, target)
    if role in ("standard", "admin", "provider"):
        f.make_owner(world.other_unit, user, world.admin)  # tied through a unit
    return user


@pytest.mark.parametrize("role", StructuralRole.values)
def test_accounts_each_actor_manages(world, role):
    account = account_of_the_property(world, role)

    assert AccountPolicy.can_manage_account(world.admin, account)
    assert AccountPolicy.can_manage_account(world.syndic, account) == (role in SYNDIC_ROLES)
    assert AccountPolicy.can_manage_account(world.manager, account) == (role in MANAGER_ROLES)


def test_a_syndic_edits_deactivates_and_deletes_a_manager(world):
    manager = account_of_the_property(world, "manager")

    AccountService.update_profile(actor=world.syndic, user=manager, changes={"phone": "0600"})
    AccountStatusService.deactivate(actor=world.syndic, user=manager)
    manager.refresh_from_db()
    # Deactivation revoked the assignments: the syndic still reaches the account.
    AccountStatusService.reactivate(actor=world.syndic, user=manager)
    AccountStatusService.delete(actor=world.syndic, user=manager)


def test_a_manager_cannot_touch_a_syndic_nor_a_provider(world):
    provider = account_of_the_property(world, "provider")

    for account in (world.syndic, provider):
        with pytest.raises(PermissionDenied):
            AccountStatusService.delete(actor=world.manager, user=account)
        with pytest.raises(PermissionDenied):
            AccountService.update_profile(actor=world.manager, user=account, changes={"phone": "1"})


def test_accounts_outside_their_properties_stay_out_of_reach(world):
    stranger = f.make_user()

    assert not AccountPolicy.can_manage_account(world.syndic, stranger)
    assert not AccountPolicy.can_manage_account(world.manager, stranger)


def test_a_manager_now_working_elsewhere_is_out_of_the_former_syndic_reach(world):
    manager = account_of_the_property(world, "manager")
    UserProperty.objects.filter(user=manager).update(is_active=False, revoked_at=timezone.now())
    f.assign_role(manager, "manager", f.make_property())

    assert not AccountPolicy.can_manage_account(world.syndic, manager)
