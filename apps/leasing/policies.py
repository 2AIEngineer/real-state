"""Who may do what with leases, their members and inspection records.

Management of the unit runs leases: creation, changes, termination,
members, inspections. A lease is read by management, by the unit's owners
and by anyone who is or was on it. Members edit their own details and
documents; identity documents are seen only by the member and management.
Only syndics and admins delete a lease for good.
"""

from django.db.models import Q

from apps.accounts.services.authorization import AccessService
from apps.leasing.models import Lease, LeaseComponentState, LeaseMember
from apps.properties.models import Unit


class LeasePolicy:
    @staticmethod
    def visible_filter(user) -> Q:
        return (
            Q(unit__building__property_id__in=AccessService.managed_property_ids(user))
            | Q(unit_id__in=AccessService.owned_unit_ids(user))
            | Q(members__user=user)
        )

    @staticmethod
    def can_view(user, lease: Lease) -> bool:
        return (
            AccessService.manages_property(user, lease.unit.building.property)
            or AccessService.is_owner_of(user, lease.unit)
            or lease.members.filter(user=user).exists()
        )

    @staticmethod
    def can_create(user, unit: Unit) -> bool:
        return AccessService.manages_property(user, unit.building.property)

    @staticmethod
    def can_update(user, lease: Lease) -> bool:
        return AccessService.manages_property(user, lease.unit.building.property)

    @staticmethod
    def can_terminate(user, lease: Lease) -> bool:
        """Terminate at term or early, or cancel a lease that never took effect."""
        return AccessService.manages_property(user, lease.unit.building.property)

    @staticmethod
    def can_delete(user, lease: Lease) -> bool:
        return AccessService.manages_syndicat(user, lease.unit.building.property.syndicat)


class LeaseMemberPolicy:
    @staticmethod
    def can_view(user, member: LeaseMember) -> bool:
        return member.user_id == user.pk or LeasePolicy.can_view(user, member.lease)

    @staticmethod
    def can_manage_members(user, lease: Lease) -> bool:
        """Add members and record departures."""
        return AccessService.manages_property(user, lease.unit.building.property)

    @staticmethod
    def can_update(user, member: LeaseMember) -> bool:
        """Members edit their own row and documents; management edits any."""
        return member.user_id == user.pk or AccessService.manages_property(
            user, member.lease.unit.building.property
        )

    @staticmethod
    def can_change_signatory(user, member: LeaseMember) -> bool:
        return AccessService.manages_property(user, member.lease.unit.building.property)


class LeaseComponentStatePolicy:
    @staticmethod
    def can_view(user, state: LeaseComponentState) -> bool:
        return LeasePolicy.can_view(user, state.lease)

    @staticmethod
    def can_record(user, lease: Lease) -> bool:
        """Record, edit, delete inspections and attach their files."""
        return AccessService.manages_property(user, lease.unit.building.property)
