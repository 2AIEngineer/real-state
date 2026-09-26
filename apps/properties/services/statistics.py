"""What the dashboard shows about a property: figures drawn from several modules."""

from __future__ import annotations

from apps.common.exceptions import PermissionDenied
from apps.leasing.models import Lease, LeaseStatus
from apps.properties import timezones
from apps.properties.models import (
    Building,
    OwnershipStatus,
    Property,
    Unit,
    UnitOwnership,
)
from apps.properties.policies import PropertyPolicy


class PropertyStatistics:
    @staticmethod
    def of(*, actor, prop: Property) -> dict[str, int]:
        if not PropertyPolicy.can_view_statistics(actor, prop):
            raise PermissionDenied("Only the property management can see its statistics.")
        units = Unit.objects.filter(building__property=prop)
        leased = (
            Lease.objects.filter(
                unit__in=units,
                status=LeaseStatus.ACTIVE,
                start_date__lte=timezones.today(prop),
            )
            .values("unit_id")
            .distinct()
            .count()
        )
        held_by_promoter = (
            UnitOwnership.objects.filter(
                unit__in=units, status=OwnershipStatus.ACTIVE, is_promoter_default=True
            )
            .values("unit_id")
            .distinct()
            .count()
        )
        return {
            "buildings": Building.objects.filter(property=prop).count(),
            "units": units.count(),
            "units_leased": leased,
            "units_held_by_promoter": held_by_promoter,
        }
