"""Who may do what with marketplace listings.

Published listings are open to every user. Only the seller changes their
listing. Moderators take a listing down: platform administrators anywhere,
and the management of the property a listing is attached to.
"""

from apps.accounts.services.authorization import AccessService
from apps.marketplace.models import ListingStatus, MarketplaceListing
from apps.properties.models import Property


class ListingPolicy:
    @staticmethod
    def can_view(user, listing: MarketplaceListing) -> bool:
        return (
            listing.status == ListingStatus.PUBLISHED
            or listing.seller_id == user.pk
            or AccessService.is_platform_admin(user)
        )

    @staticmethod
    def can_publish_in(user, prop: Property) -> bool:
        """Attaching a listing to a property requires a link with it."""
        return AccessService.is_staff_or_resident_of_property(user, prop)

    @staticmethod
    def can_update(user, listing: MarketplaceListing) -> bool:
        """Editing, images, marking sold and archiving."""
        return listing.seller_id == user.pk

    @staticmethod
    def can_moderate(user, listing: MarketplaceListing) -> bool:
        if AccessService.is_platform_admin(user):
            return True
        return listing.property_id is not None and AccessService.manages_property(
            user, listing.property
        )

    @staticmethod
    def can_delete(user, listing: MarketplaceListing) -> bool:
        return listing.seller_id == user.pk or AccessService.is_platform_admin(user)
