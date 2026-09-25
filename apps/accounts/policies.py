"""Who may do what with accounts, with their role, and with their assignments.

Three questions live here, in that order:

1. **The account** (`AccountPolicy`) — creating accounts, finding them, editing
   a profile, changing an e-mail, deactivating.
2. **The role** (`can_give_role` when an account is created, `can_change_role`
   when it already has one) — which platform-wide role an actor may give.
3. **The places** (`can_assign_syndicat`, `can_assign_property`,
   `can_assign_building`) — where an actor may attach staff. Each one answers
   one question only: *does the actor run this place?* Whether the account on
   the receiving end may be assigned at all — a role the actor hands out, and
   never the actor's own account — is `can_assign_account`, and the assignment
   services ask both.

The rules, in one table (`roles_handled_by`):

| Actor   | Creates, edits, deactivates and deletes the accounts of the roles |
|---------|-------------------------------------------------------------------|
| admin   | every role, admin and provider included (only admins handle those) |
| syndic  | syndic, manager, security, cleaning, maintenance, standard         |
| manager | manager, security, cleaning, maintenance, standard                 |

A syndic or a manager acts on the accounts they can see (tied to the
properties they manage, or created by them), never on their own account for
its role, status or deletion; everyone edits their own profile.
"""

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from apps.accounts.enums import MANAGEMENT_ROLES, StructuralRole
from apps.accounts.models import UserBuilding, UserProperty, UserSyndicat
from apps.accounts.services.authorization import AccessService
from apps.leasing.models import LeaseStatus
from apps.properties.models import Building, OwnershipStatus, Property, Syndicat, Unit

User = get_user_model()

FIELD_STAFF = (
    StructuralRole.MAINTENANCE,
    StructuralRole.SECURITY,
    StructuralRole.CLEANING,
)


def users_linked_to_properties(property_ids) -> QuerySet:
    """Users assigned to, owning in, or renting in the given properties."""
    units = Unit.objects.filter(building__property_id__in=property_ids).values("id")
    syndicats = Property.objects.filter(id__in=property_ids).values("syndicat_id")
    return User.objects.filter(
        Q(
            pk__in=UserSyndicat.objects.filter(is_active=True, syndicat_id__in=syndicats).values(
                "user_id"
            )
        )
        | Q(
            pk__in=UserProperty.objects.filter(is_active=True, property_id__in=property_ids).values(
                "user_id"
            )
        )
        | Q(
            pk__in=UserBuilding.objects.filter(
                is_active=True, building__property_id__in=property_ids
            ).values("user_id")
        )
        | Q(
            unit_ownerships__status=OwnershipStatus.ACTIVE,
            unit_ownerships__unit_id__in=units,
        )
        | Q(
            lease_memberships__left_at__isnull=True,
            lease_memberships__lease__status=LeaseStatus.ACTIVE,
            lease_memberships__lease__unit_id__in=units,
        )
    ).distinct()


def _has_active_assignment(account) -> bool:
    return any(
        model.objects.filter(user=account, is_active=True).exists()
        for model in (UserSyndicat, UserProperty, UserBuilding)
    )


def _was_assigned_in(account, property_ids) -> bool:
    """Whether `account` held an assignment, even revoked, in one of these properties."""
    syndicats = Property.objects.filter(id__in=property_ids).values("syndicat_id")
    return (
        UserSyndicat.objects.filter(user=account, syndicat_id__in=syndicats).exists()
        or UserProperty.objects.filter(user=account, property_id__in=property_ids).exists()
        or UserBuilding.objects.filter(
            user=account, building__property_id__in=property_ids
        ).exists()
    )


# --------------------------------------------------------------------- accounts


class AccountPolicy:
    """Account management is open to admins and to syndics and managers
    assigned somewhere. Staff see the accounts tied to the properties they
    manage and the accounts they created, and manage those holding a role they
    handle (`can_manage_account`). Everyone edits their own profile."""

    @staticmethod
    def can_manage_accounts(user) -> bool:
        """Create accounts, send invitations, search the directory."""
        if not user.is_active:
            return False
        if AccessService.is_platform_admin(user):
            return True
        return user.role in MANAGEMENT_ROLES and any(
            model.objects.filter(user=user, is_active=True).exists()
            for model in (UserSyndicat, UserProperty)
        )

    @staticmethod
    def searchable_filter(user, *, property_id: int | None = None, query: str | None = None) -> Q:
        """Accounts the user may find when searching."""
        if AccessService.is_platform_admin(user):
            return (
                Q(pk__in=users_linked_to_properties([property_id]).values("pk"))
                if property_id
                else Q()
            )
        managed = AccessService.managed_property_ids(user)
        if property_id:
            managed = managed.filter(id=property_id)
        # Accounts created by the user are visible even before any link exists
        # (e.g. a tenant account created just before the lease is recorded).
        reach = Q(pk__in=users_linked_to_properties(managed).values("pk")) | Q(created_by=user)
        if query and "@" in query and not property_id:
            # Exact e-mail lookup lets staff attach an existing platform
            # account (e.g. an owner elsewhere) without browsing others.
            reach |= Q(email__iexact=query.strip())
        return reach

    @staticmethod
    def can_view(user, account) -> bool:
        if user.pk == account.pk or AccessService.is_platform_admin(user):
            return True
        if account.created_by_id == user.pk:
            return True
        managed = AccessService.managed_property_ids(user)
        if users_linked_to_properties(managed).filter(pk=account.pk).exists():
            return True
        # An account left without any active assignment (deactivated, or revoked
        # everywhere) stays in the reach of whoever ran the places it was assigned
        # to, so it can be reactivated, reassigned or deleted. One working
        # elsewhere now is out of their reach.
        return not _has_active_assignment(account) and _was_assigned_in(account, managed)

    @staticmethod
    def can_manage_account(user, account) -> bool:
        """Edit, invite, deactivate, reactivate or delete someone else's account:
        an admin, or a syndic or manager who sees the account and handles its role."""
        if AccessService.is_platform_admin(user):
            return True
        return (
            user.is_active
            and user.pk != account.pk
            and account.role in roles_handled_by(user)
            and AccountPolicy.can_view(user, account)
        )

    @staticmethod
    def can_invite(user, account) -> bool:
        return AccountPolicy.can_manage_account(user, account)

    @staticmethod
    def can_edit_profile(user, account) -> bool:
        return user.pk == account.pk or AccountPolicy.can_manage_account(user, account)

    @staticmethod
    def can_change_email(user, account) -> bool:
        """The holder (who confirms their password) or whoever manages the account."""
        return user.pk == account.pk or AccountPolicy.can_manage_account(user, account)

    @staticmethod
    def can_change_status(user, account) -> bool:
        """Deactivate, reactivate and delete an account (never one's own)."""
        return user.pk != account.pk and AccountPolicy.can_manage_account(user, account)

    @staticmethod
    def can_edit_provider_profile(user, account) -> bool:
        """Providers are handled by admins only, besides the provider themselves."""
        return user.pk == account.pk or AccountPolicy.can_manage_account(user, account)


# ------------------------------------------------------------------------ roles


def roles_handled_by(user) -> tuple[str, ...]:
    """The roles whose accounts a syndic or a manager creates, edits, deactivates,
    deletes and assigns. Admins handle every role (checked before this is asked);
    admin and provider accounts are theirs alone."""
    if user.role == StructuralRole.SYNDIC:
        return (
            StructuralRole.SYNDIC,
            StructuralRole.MANAGER,
            *FIELD_STAFF,
            StructuralRole.STANDARD,
        )
    if user.role == StructuralRole.MANAGER:
        return (StructuralRole.MANAGER, *FIELD_STAFF, StructuralRole.STANDARD)
    return ()


def can_give_role(user, role: str) -> bool:
    """Whether `user` may hand out this role at all — when creating an account,
    or when changing the role of one. Admins give any role; a syndic or a
    manager gives the roles they handle."""
    if AccessService.is_platform_admin(user):
        return True
    if not user.is_active:
        return False
    return role in roles_handled_by(user)


def can_change_role(user, account, new_role: str) -> bool:
    """Replace the role of `account` with `new_role`: both roles must be ones
    the actor hands out, and nobody changes their own role."""
    if AccessService.is_platform_admin(user):
        return True
    if user.pk == account.pk:
        return False
    return can_give_role(user, new_role) and can_give_role(user, account.role)


# ------------------------------------------------------------------ assignments


def can_assign_account(user, account) -> bool:
    """Whether `user` may grant or revoke assignments *of this account*.

    Admins: any account. A syndic or a manager: an account holding one of the
    roles they hand out, and never their own account. Says nothing about the
    place, which the three functions below answer.
    """
    if AccessService.is_platform_admin(user):
        return True
    return user.is_active and user.pk != account.pk and account.role in roles_handled_by(user)


def can_assign_syndicat(user, syndicat: Syndicat) -> bool:
    """Whether `user` runs this syndicat: an admin, or a syndic assigned to it."""
    return AccessService.manages_syndicat(user, syndicat)


def can_assign_property(user, prop: Property) -> bool:
    """Whether `user` runs this property: an admin, its syndic, or its manager."""
    return AccessService.manages_property(user, prop)


def can_assign_building(user, building: Building) -> bool:
    """Whether `user` runs the property this building belongs to."""
    return AccessService.manages_property(user, building.property)


def can_see_all_assignments_of(user, account) -> bool:
    """Whether `user` sees every assignment of the account, and not only those
    in the properties they manage."""
    return user.pk == account.pk or AccessService.is_platform_admin(user)
