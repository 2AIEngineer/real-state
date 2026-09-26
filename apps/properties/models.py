from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.common.models import TimeStampedModel
from apps.properties.enums import Feature
from apps.properties.timezones import default_time_zone


class Syndicat(TimeStampedModel):
    """Company-like entity grouping several properties."""

    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(max_length=64, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                models.functions.Lower("name"), name="syndicat_name_ci_unique"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Promoter(TimeStampedModel):
    """Legal entity that developed one or more residences.

    Materialised by a representative user account which is the default,
    permanent owner of every unit of its properties.
    """

    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(max_length=64, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    representative_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="represented_promoter",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                models.functions.Lower("name"), name="promoter_name_ci_unique"
            ),
        ]

    def __str__(self) -> str:
        return self.name


FEATURE_FLAG_FIELDS: dict[str, str] = {
    feature.value: f"include_{feature.value}" for feature in Feature
}


class Property(TimeStampedModel):
    """A residence belonging to a syndicat, developed by a single promoter."""

    syndicat = models.ForeignKey(
        Syndicat, on_delete=models.CASCADE, related_name="properties"
    )
    promoter = models.ForeignKey(
        Promoter, on_delete=models.PROTECT, related_name="properties"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    # IANA name: "today", opening hours and notification times are read in it.
    timezone = models.CharField(max_length=64, default=default_time_zone)
    is_active = models.BooleanField(default=True)

    # SaaS plan gating — one switch per module.
    include_service_request = models.BooleanField(default=True)
    include_announcements = models.BooleanField(default=True)
    include_events = models.BooleanField(default=True)
    include_amenities = models.BooleanField(default=True)
    include_store = models.BooleanField(default=True)
    include_library = models.BooleanField(default=True)
    include_short_term_rental = models.BooleanField(default=True)
    include_surveys = models.BooleanField(default=True)
    include_marketplace = models.BooleanField(default=True)
    include_visitor = models.BooleanField(default=True)
    include_chat = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name_plural = "properties"
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                "syndicat",
                models.functions.Lower("name"),
                name="property_name_per_syndicat",
            ),
        ]
        indexes = [
            models.Index(fields=["syndicat", "is_active"]),
            models.Index(fields=["promoter"]),
        ]

    def __str__(self) -> str:
        return self.name


class Building(TimeStampedModel):
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="buildings"
    )
    name = models.CharField(max_length=120)
    address = models.TextField(blank=True)
    floors_count = models.PositiveSmallIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["property_id", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                "property",
                models.functions.Lower("name"),
                name="building_name_per_property",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class UnitType(models.TextChoices):
    APARTMENT = "apartment", "Apartment"
    HOUSE = "house", "House / villa"
    OFFICE = "office", "Office"
    COMMERCIAL = "commercial", "Commercial space"
    PARKING = "parking", "Parking space"
    STORAGE = "storage", "Storage"
    OTHER = "other", "Other"


class Unit(TimeStampedModel):
    """A lot inside a building. Ownership and occupancy are never stored here."""

    building = models.ForeignKey(
        Building, on_delete=models.CASCADE, related_name="units"
    )
    number = models.CharField(max_length=32)
    label = models.CharField(max_length=120, blank=True)
    # Signed on purpose: basements are negative floors.
    floor = models.SmallIntegerField(null=True, blank=True)
    unit_type = models.CharField(
        max_length=16, choices=UnitType.choices, default=UnitType.APARTMENT
    )
    area_sqm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    rooms_count = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["building_id", "number", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["building", "number"], name="unique_unit_number_per_building"
            ),
            models.CheckConstraint(
                condition=Q(area_sqm__isnull=True) | Q(area_sqm__gt=0),
                name="unit_area_positive",
            ),
        ]

    def __str__(self) -> str:
        return self.label or self.number


class OwnershipStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    TERMINATED = "TERMINATED", "Terminated"


class OwnershipEndReason(models.TextChoices):
    SALE = "SALE", "Sold to a new owner"
    DEPARTURE = "DEPARTURE", "Owner left (no registered acquirer)"
    PROMOTER_CHANGE = "PROMOTER_CHANGE", "Property promoter replaced"
    CORRECTION = "CORRECTION", "Administrative correction"


class UnitOwnership(TimeStampedModel):
    """Legal ownership fact. Never deleted: history is the ownership ledger."""

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="ownerships")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="unit_ownerships",
    )
    ownership_share = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=OwnershipStatus.choices, default=OwnershipStatus.ACTIVE
    )
    is_promoter_default = models.BooleanField(
        default=False, help_text="Automatic ownership held by the property's promoter."
    )
    end_reason = models.CharField(
        max_length=24, choices=OwnershipEndReason.choices, blank=True
    )
    acquisition_reference = models.CharField(max_length=120, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    ended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        ordering = ["-start_date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="ownership_end_after_start",
            ),
            models.CheckConstraint(
                condition=(Q(status=OwnershipStatus.ACTIVE) & Q(end_date__isnull=True))
                | (Q(status=OwnershipStatus.TERMINATED) & Q(end_date__isnull=False)),
                name="ownership_status_matches_end_date",
            ),
            models.CheckConstraint(
                condition=Q(ownership_share__isnull=True)
                | (Q(ownership_share__gt=0) & Q(ownership_share__lte=100)),
                name="ownership_share_percentage",
            ),
            models.UniqueConstraint(
                fields=["unit", "owner"],
                condition=Q(status=OwnershipStatus.ACTIVE),
                name="unique_active_ownership_per_user_unit",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "unit", "status"]),
            models.Index(fields=["unit", "status"]),
        ]

    def __str__(self) -> str:
        return f"Ownership #{self.pk} unit={self.unit_id} owner={self.owner_id}"
