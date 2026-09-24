"""Platform-wide classified ads, optionally attached to a property.

A listing is published with at least one image, and a published listing can
never drop to zero images.

    PUBLISHED ──mark_sold──▶ SOLD        (seller)
    PUBLISHED ──archive────▶ ARCHIVED    (seller: keeps the ad, off the catalogue)
    PUBLISHED ──moderate───▶ MODERATED   (platform moderation)
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.common.db import apply_changes, deleting
from apps.common.exceptions import (
    BusinessRuleViolation,
    InvalidInput,
    InvalidTransition,
    NotFound,
    PermissionDenied,
)
from apps.common.files.rules import EntityType
from apps.common.files.service import AttachmentService
from apps.common.services.audit import AuditService
from apps.marketplace import notices
from apps.marketplace.audit import MarketplaceAudit
from apps.marketplace.models import ListingStatus, MarketplaceListing
from apps.marketplace.policies import ListingPolicy
from apps.notifications.services import delete_notification_traces
from apps.properties.enums import Feature
from apps.properties.models import Property
from apps.properties.services import FeatureGate

User = get_user_model()

EDITABLE_FIELDS = (
    "category",
    "title",
    "description",
    "price",
    "currency",
    "is_negotiable",
    "location",
    "contact_phone",
    "contact_email",
)


class ListingService:
    @staticmethod
    def list_published(
        *,
        actor,
        property_id: int,
        category: str | None = None,
        search: str | None = None,
        max_price: Decimal | None = None,
    ) -> QuerySet[MarketplaceListing]:
        qs = MarketplaceListing.objects.filter(status=ListingStatus.PUBLISHED).select_related(
            "seller", "property"
        )
        # Listings of a property whose plan excludes the marketplace are hidden.
        qs = qs.filter(property_id=property_id, property__include_marketplace=True)
        if category:
            qs = qs.filter(category=category)
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))
        if max_price is not None:
            qs = qs.filter(price__lte=max_price)
        return qs

    @staticmethod
    def list_mine(*, actor, status: str | None = None) -> QuerySet[MarketplaceListing]:
        qs = MarketplaceListing.objects.filter(seller=actor).select_related("property")
        return qs.filter(status=status) if status else qs

    @staticmethod
    def get_visible(*, actor, prop: Property, listing_id: int) -> MarketplaceListing:
        """A listing of the selected property, or one attached to no property."""
        listing = (
            MarketplaceListing.objects.select_related("seller", "property")
            .filter(Q(property=prop) | Q(property__isnull=True), pk=listing_id)
            .first()
        )
        if listing is None or not ListingPolicy.can_view(actor, listing):
            raise NotFound("Listing not found.")
        return listing

    @staticmethod
    @transaction.atomic
    def publish(*, actor, data: dict, images, prop: Property) -> MarketplaceListing:
        """A listing is published inside the property currently selected by the seller."""
        FeatureGate.require(prop, Feature.MARKETPLACE)
        if not ListingPolicy.can_publish_in(actor, prop):
            raise PermissionDenied("You have no link with this property.")
        if not images:
            raise InvalidInput(
                "At least one image is required to publish a listing.", field="images"
            )
        if data.get("price") is not None and data["price"] < 0:
            raise InvalidInput("The price cannot be negative.", field="price")
        listing = MarketplaceListing(seller=actor, property=prop, published_at=timezone.now())
        apply_changes(listing, data, EDITABLE_FIELDS)
        listing.save()
        AttachmentService.attach(
            entity_type=EntityType.MARKETPLACE_LISTING,
            entity_id=listing.pk,
            files=list(images),
            uploaded_by=actor,
            field="images",
        )
        AuditService.record(
            actor=actor,
            action=MarketplaceAudit.LISTING_PUBLISHED,
            target=listing,
            property_id=prop.pk,
        )
        notices.listing_published(listing, actor=actor)
        return listing

    @staticmethod
    def _lock_own_published(actor, listing: MarketplaceListing) -> MarketplaceListing:
        listing = MarketplaceListing.objects.select_for_update(of=("self",)).get(pk=listing.pk)
        if not ListingPolicy.can_update(actor, listing):
            raise PermissionDenied("Only the seller can change this listing.")
        if listing.status != ListingStatus.PUBLISHED:
            raise InvalidTransition("This listing is closed.")
        return listing

    @staticmethod
    @transaction.atomic
    def update(*, actor, listing: MarketplaceListing, changes: dict) -> MarketplaceListing:
        listing = ListingService._lock_own_published(actor, listing)
        fields = apply_changes(listing, changes, EDITABLE_FIELDS)
        if listing.price is not None and listing.price < 0:
            raise InvalidInput("The price cannot be negative.", field="price")
        if fields:
            listing.save(update_fields=[*fields, "updated_at"])
        return listing

    @staticmethod
    @transaction.atomic
    def mark_sold(*, actor, listing: MarketplaceListing) -> MarketplaceListing:
        """The item found a buyer: the ad leaves the catalogue as sold."""
        return ListingService._close(actor=actor, listing=listing, status=ListingStatus.SOLD)

    @staticmethod
    @transaction.atomic
    def archive(*, actor, listing: MarketplaceListing) -> MarketplaceListing:
        """The seller puts the ad away without selling; the record stays."""
        return ListingService._close(actor=actor, listing=listing, status=ListingStatus.ARCHIVED)

    @staticmethod
    def _close(*, actor, listing: MarketplaceListing, status: str) -> MarketplaceListing:
        listing = ListingService._lock_own_published(actor, listing)
        listing.status = status
        listing.closed_at = timezone.now()
        listing.save(update_fields=["status", "closed_at", "updated_at"])
        AuditService.record(
            actor=actor,
            action=MarketplaceAudit(f"marketplace.listing_{status.lower()}"),
            target=listing,
            property_id=listing.property_id,
        )
        return listing

    @staticmethod
    @transaction.atomic
    def moderate(*, actor, listing: MarketplaceListing, reason: str) -> MarketplaceListing:
        if not ListingPolicy.can_moderate(actor, listing):
            raise PermissionDenied("Only moderators can remove listings.")
        listing = (
            MarketplaceListing.objects.select_for_update(of=("self",))
            .select_related("seller")
            .get(pk=listing.pk)
        )
        if listing.status != ListingStatus.PUBLISHED:
            raise InvalidTransition("Only published listings can be taken down.")
        listing.status = ListingStatus.MODERATED
        listing.closed_at = timezone.now()
        listing.moderation_reason = reason
        listing.moderated_by = actor
        listing.save(
            update_fields=["status", "closed_at", "moderation_reason", "moderated_by", "updated_at"]
        )
        AuditService.record(
            actor=actor,
            action=MarketplaceAudit.LISTING_MODERATED,
            target=listing,
            property_id=listing.property_id,
            metadata={"reason": reason},
        )
        notices.listing_moderated(listing, reason=reason)
        return listing

    @staticmethod
    @transaction.atomic
    def delete(*, actor, listing: MarketplaceListing) -> None:
        """The seller removes their own ad; moderators remove any."""
        if not ListingPolicy.can_delete(actor, listing):
            raise PermissionDenied(
                "Only the seller or a platform administrator can delete this listing."
            )
        AuditService.record(
            actor=actor,
            action=MarketplaceAudit.LISTING_DELETED,
            target=listing,
            property_id=listing.property_id,
        )
        with deleting("listing"):
            AttachmentService.delete_for_entity(EntityType.MARKETPLACE_LISTING, listing.pk)
            delete_notification_traces(listing)
            listing.delete()

    @staticmethod
    @transaction.atomic
    def add_images(*, actor, listing: MarketplaceListing, images) -> list:
        listing = ListingService._lock_own_published(actor, listing)
        return AttachmentService.attach(
            entity_type=EntityType.MARKETPLACE_LISTING,
            entity_id=listing.pk,
            files=list(images),
            uploaded_by=actor,
            field="images",
        )

    @staticmethod
    @transaction.atomic
    def remove_image(*, actor, listing: MarketplaceListing, attachment_id: int) -> None:
        listing = ListingService._lock_own_published(actor, listing)
        attachment = AttachmentService.get(
            entity_type=EntityType.MARKETPLACE_LISTING,
            entity_id=listing.pk,
            attachment_id=attachment_id,
        )
        if AttachmentService.count(EntityType.MARKETPLACE_LISTING, listing.pk) <= 1:
            raise BusinessRuleViolation(
                "A published listing must keep at least one image.", code="last_image"
            )
        AttachmentService.delete(attachment=attachment)
