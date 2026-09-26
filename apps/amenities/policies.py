"""Who may do what with amenities and their bookings.

Amenities are visible to everyone linked to the property and managed by its
management. Owners, tenants and management book them; a booking is seen
and cancelled by its booker or by management, which alone decides on
bookings awaiting approval and deletes them.
"""

from django.db.models import Q

from apps.accounts.services.authorization import AccessService
from apps.amenities.models import Amenity, Booking
from apps.properties.models import Property


class AmenityPolicy:
    @staticmethod
    def can_list(user, prop: Property) -> bool:
        return AccessService.is_staff_or_resident_of_property(user, prop)

    @staticmethod
    def can_see_inactive(user, prop: Property) -> bool:
        return AccessService.manages_property(user, prop)

    @staticmethod
    def can_view(user, amenity: Amenity) -> bool:
        """Also covers its availability schedule."""
        return AccessService.is_staff_or_resident_of_property(user, amenity.property)

    @staticmethod
    def can_create(user, prop: Property) -> bool:
        return AccessService.manages_property(user, prop)

    @staticmethod
    def can_update(user, amenity: Amenity) -> bool:
        """Editing its rules and its images."""
        return AccessService.manages_property(user, amenity.property)

    @staticmethod
    def can_delete(user, amenity: Amenity) -> bool:
        return AccessService.manages_property(user, amenity.property)


class BookingPolicy:
    @staticmethod
    def visible_filter(user) -> Q:
        """The user's own bookings, plus every booking of the properties they manage."""
        return Q(booker=user) | Q(amenity__property_id__in=AccessService.managed_property_ids(user))

    @staticmethod
    def can_view(user, booking: Booking) -> bool:
        return booking.booker_id == user.pk or AccessService.manages_property(
            user, booking.amenity.property
        )

    @staticmethod
    def can_book(user, prop: Property) -> bool:
        return AccessService.is_resident_of_property(user, prop) or AccessService.manages_property(
            user, prop
        )

    @staticmethod
    def can_decide(user, booking: Booking) -> bool:
        """Approve or reject a booking awaiting approval."""
        return AccessService.manages_property(user, booking.amenity.property)

    @staticmethod
    def can_cancel(user, booking: Booking) -> bool:
        """When they may do it (before start, before end) is a booking rule, see the service."""
        return booking.booker_id == user.pk or AccessService.manages_property(
            user, booking.amenity.property
        )

    @staticmethod
    def can_delete(user, booking: Booking) -> bool:
        return AccessService.manages_property(user, booking.amenity.property)
