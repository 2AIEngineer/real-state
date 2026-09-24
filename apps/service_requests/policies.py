"""Who may do what with service requests.

A request is followed by its participants: the requester, the property
management and the maintenance staff assigned to it. Owners, tenants and
staff submit requests for units they are tied to; management assigns,
closes and deletes; the requester gives feedback and may cancel.
"""

from django.db.models import Q

from apps.accounts.services.authorization import AccessService
from apps.properties.models import Property, Unit
from apps.service_requests.models import ServiceRequest


class ServiceRequestPolicy:
    @staticmethod
    def visible_filter(user) -> Q:
        return (
            Q(requester=user)
            | Q(property_id__in=AccessService.managed_property_ids(user))
            | Q(assignments__resolver=user)
        )

    @staticmethod
    def is_management(user, sr: ServiceRequest) -> bool:
        return AccessService.manages_property(user, sr.property)

    @staticmethod
    def can_view(user, sr: ServiceRequest) -> bool:
        """Requester, management of the property, or a resolver of the request."""
        return (
            sr.requester_id == user.pk
            or ServiceRequestPolicy.is_management(user, sr)
            or sr.assignments.filter(resolver=user).exists()
        )

    @staticmethod
    def can_submit(user, prop: Property, unit: Unit | None) -> bool:
        """For a unit: staff working in its building, or its owners and tenants.
        For the property as a whole: anyone linked to it."""
        if unit is None:
            return AccessService.is_staff_or_resident_of_property(user, prop)
        return AccessService.is_staff_of_building(
            user, unit.building
        ) or AccessService.is_owner_or_tenant_of(user, unit)

    @staticmethod
    def can_add_files(user, sr: ServiceRequest) -> bool:
        return ServiceRequestPolicy.can_view(user, sr)

    @staticmethod
    def can_remove_file(user, sr: ServiceRequest, uploaded_by_id: int | None) -> bool:
        """The uploader takes back their file; management removes any."""
        return uploaded_by_id == user.pk or ServiceRequestPolicy.is_management(user, sr)

    @staticmethod
    def can_assign(user, sr: ServiceRequest) -> bool:
        return ServiceRequestPolicy.is_management(user, sr)

    @staticmethod
    def can_give_feedback(user, sr: ServiceRequest) -> bool:
        return sr.requester_id == user.pk

    @staticmethod
    def can_close(user, sr: ServiceRequest) -> bool:
        return ServiceRequestPolicy.is_management(user, sr)

    @staticmethod
    def can_cancel(user, sr: ServiceRequest) -> bool:
        return sr.requester_id == user.pk or ServiceRequestPolicy.is_management(user, sr)

    @staticmethod
    def can_delete(user, sr: ServiceRequest) -> bool:
        return ServiceRequestPolicy.is_management(user, sr)
