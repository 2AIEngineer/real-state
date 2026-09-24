import pytest

from apps.common.exceptions import BusinessRuleViolation, InvalidInput, PermissionDenied
from apps.common.files.rules import EntityType
from apps.common.files.service import AttachmentService
from apps.marketplace.models import ListingCategory, ListingStatus
from apps.marketplace.services import ListingService
from apps.notifications.models import InboxNotification
from tests import factories as f

pytestmark = pytest.mark.django_db
DATA = {"category": ListingCategory.VARIOUS_OFFER, "title": "Bike", "description": "Good state"}


def test_at_least_one_image_is_required(world):
    with pytest.raises(InvalidInput):
        ListingService.publish(actor=world.tenant, data=DATA, images=[], prop=world.prop)


def test_property_listing_reaches_owners_and_tenants(world):
    ListingService.publish(actor=world.tenant, data=DATA, images=[f.png()], prop=world.prop)
    assert InboxNotification.objects.filter(
        notification_type="marketplace.listing_created", user=world.owner
    ).exists()


def test_listing_is_visible_to_the_other_residents_of_its_property(world):
    listing = ListingService.publish(
        actor=world.owner, data=DATA, images=[f.png()], prop=world.prop
    )
    assert listing in ListingService.list_published(actor=world.tenant, property_id=world.prop.pk)
    assert listing not in ListingService.list_published(
        actor=world.tenant, property_id=f.make_property().pk
    )


def test_non_member_cannot_attach_listing_to_property(world):
    with pytest.raises(PermissionDenied):
        ListingService.publish(actor=world.outsider, data=DATA, images=[f.png()], prop=world.prop)


def test_last_image_cannot_be_removed(world):
    listing = ListingService.publish(
        actor=world.tenant, data=DATA, images=[f.png()], prop=world.prop
    )
    image = AttachmentService.list_for_entity(EntityType.MARKETPLACE_LISTING, listing.pk).get()
    with pytest.raises(BusinessRuleViolation):
        ListingService.remove_image(actor=world.tenant, listing=listing, attachment_id=image.pk)


def test_sold_listing_leaves_the_catalogue(world):
    listing = ListingService.publish(
        actor=world.tenant, data=DATA, images=[f.png()], prop=world.prop
    )
    with pytest.raises(PermissionDenied):
        ListingService.mark_sold(actor=world.owner, listing=listing)
    ListingService.mark_sold(actor=world.tenant, listing=listing)
    assert listing not in ListingService.list_published(
        actor=world.tenant, property_id=world.prop.pk
    )


def test_seller_archives_an_ad_without_selling_it(world):
    listing = ListingService.publish(
        actor=world.tenant, data=DATA, images=[f.png()], prop=world.prop
    )
    listing = ListingService.archive(actor=world.tenant, listing=listing)
    assert listing.status == ListingStatus.ARCHIVED
    assert listing not in ListingService.list_published(
        actor=world.tenant, property_id=world.prop.pk
    )
    assert listing in ListingService.list_mine(actor=world.tenant)


def test_moderation(world):
    listing = ListingService.publish(
        actor=world.tenant, data=DATA, images=[f.png()], prop=world.prop
    )
    with pytest.raises(PermissionDenied):
        ListingService.moderate(actor=world.owner, listing=listing, reason="spam")
    listing = ListingService.moderate(actor=world.manager, listing=listing, reason="Not allowed")
    assert listing.status == ListingStatus.MODERATED
