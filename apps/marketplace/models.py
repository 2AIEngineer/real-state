from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class ListingCategory(models.TextChoices):
    REAL_ESTATE_RENTAL = "real_estate_rental", "Real estate for rent"
    REAL_ESTATE_SALE = "real_estate_sale", "Real estate for sale"
    VARIOUS_OFFER = "various_offer", "Various offers"


class ListingStatus(models.TextChoices):
    PUBLISHED = "PUBLISHED", "Published"
    SOLD = "SOLD", "Sold / rented"
    ARCHIVED = "ARCHIVED", "Archived by the seller"
    MODERATED = "MODERATED", "Taken down by moderation"


class MarketplaceListing(TimeStampedModel):
    """Platform-wide classified ad, optionally attached to a property."""

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="marketplace_listings"
    )
    property = models.ForeignKey(
        "properties.Property",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="marketplace_listings",
    )
    category = models.CharField(max_length=24, choices=ListingCategory.choices)
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="MAD")
    is_negotiable = models.BooleanField(default=False)
    location = models.CharField(max_length=200, blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    contact_email = models.EmailField(blank=True)
    status = models.CharField(
        max_length=10, choices=ListingStatus.choices, default=ListingStatus.PUBLISHED
    )
    published_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    moderation_reason = models.TextField(blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-published_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(price__isnull=True) | Q(price__gte=0), name="listing_price_non_negative"
            )
        ]
        indexes = [
            models.Index(fields=["status", "category", "-published_at"]),
            models.Index(fields=["property", "status"]),
            models.Index(fields=["seller", "status"]),
        ]

    def __str__(self) -> str:
        return self.title
