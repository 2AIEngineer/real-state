"""What people are told about marketplace listings."""

from __future__ import annotations

from django.contrib.auth import get_user_model

from apps.accounts.enums import PropertyRole
from apps.accounts.services.directory import UserDirectory
from apps.marketplace.models import MarketplaceListing
from apps.notifications.models import NotificationCategory
from apps.notifications.services import NotificationIntent, NotificationService

User = get_user_model()


def listing_published(listing: MarketplaceListing, *, actor) -> None:
    """A new listing is announced to the owners and tenants of its property."""
    residents = UserDirectory.users_by_property_role(
        listing.property, [PropertyRole.OWNER, PropertyRole.TENANT]
    )
    price = f" — {listing.price} {listing.currency}" if listing.price is not None else ""
    NotificationService.notify(
        NotificationIntent(
            event_type="marketplace.listing_created",
            category=NotificationCategory.MARKETPLACE,
            title=f"Nouvelle annonce — {listing.property.name}",
            body=f"« {listing.title} »{price}",
            bcc=list(User.objects.filter(pk__in=residents.keys())),
            target=listing,
            exclude=[actor],
            data={"listing_id": listing.pk},
            action_path=f"/marketplace/{listing.pk}",
        )
    )


def listing_moderated(listing: MarketplaceListing, *, reason: str) -> None:
    NotificationService.notify(
        NotificationIntent(
            event_type="marketplace.listing_moderated",
            category=NotificationCategory.MARKETPLACE,
            title="Annonce retirée par la modération",
            body=f"« {listing.title} » : {reason}",
            to=[listing.seller],
            target=listing,
            include_platform_admins=False,
        )
    )
