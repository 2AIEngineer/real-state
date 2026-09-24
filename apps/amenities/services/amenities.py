"""Amenities of a property: the places residents can book."""

from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.db.models import QuerySet

from apps.amenities import errors
from apps.amenities.audit import AmenityAudit
from apps.amenities.models import (
    BLOCKING_BOOKING_STATUSES,
    Amenity,
    Booking,
)
from apps.amenities.policies import AmenityPolicy
from apps.common.db import apply_changes, deleting, translate_integrity_errors
from apps.common.exceptions import (
    InvalidInput,
    NotFound,
    PermissionDenied,
)
from apps.common.files.rules import EntityType
from apps.common.files.service import AttachmentService
from apps.common.services.audit import AuditService
from apps.properties.enums import Feature
from apps.properties.models import Building, Property
from apps.properties.services import FeatureGate

AMENITY_FIELDS = (
    "name",
    "description",
    "location",
    "rules",
    "booking_mode",
    "capacity",
    "requires_approval",
    "opening_time",
    "closing_time",
    "min_duration_minutes",
    "max_duration_minutes",
    "max_advance_days",
    "is_active",
    "fee",
    "security_fee",
    "hourly_price",
)
AMENITY_CONSTRAINTS = {"amenity_name_per_property": errors.amenity_name_taken}


class AmenityService:
    @staticmethod
    def list_visible(*, actor, prop: Property, include_inactive: bool = False) -> QuerySet[Amenity]:
        if not AmenityPolicy.can_list(actor, prop):
            raise PermissionDenied("You have no link with this property.")
        FeatureGate.require(prop, Feature.AMENITIES)
        qs = Amenity.objects.filter(property=prop).select_related("building")
        if not include_inactive or not AmenityPolicy.can_see_inactive(actor, prop):
            qs = qs.filter(is_active=True)
        return qs

    @staticmethod
    def get_visible(*, actor, amenity_id: int) -> Amenity:
        amenity = (
            Amenity.objects.select_related("property", "building").filter(pk=amenity_id).first()
        )
        if amenity is None or not AmenityPolicy.can_view(actor, amenity):
            raise NotFound("Amenity not found.")
        return amenity

    @staticmethod
    def _validate(amenity: Amenity) -> None:
        if amenity.capacity < 1:
            raise InvalidInput("Capacity must be at least 1.", field="capacity")
        if amenity.max_duration_minutes < amenity.min_duration_minutes:
            raise InvalidInput(
                "Maximum duration is shorter than the minimum.", field="max_duration_minutes"
            )
        if (amenity.opening_time is None) != (amenity.closing_time is None):
            raise InvalidInput("Opening and closing times go together.", field="opening_time")
        if amenity.opening_time and amenity.closing_time <= amenity.opening_time:
            raise InvalidInput("Closing time must follow opening time.", field="closing_time")
        for price in ("fee", "security_fee", "hourly_price"):
            if getattr(amenity, price) is None or getattr(amenity, price) < 0:
                raise InvalidInput(
                    "Prices cannot be negative (use 0 when there is nothing to pay).", field=price
                )

    @staticmethod
    @transaction.atomic
    def create(*, actor, prop: Property, data: dict, building: Building | None = None) -> Amenity:
        if not AmenityPolicy.can_create(actor, prop):
            raise PermissionDenied("Only the property management can create amenities.")
        FeatureGate.require(prop, Feature.AMENITIES)
        if building is not None and building.property_id != prop.pk:
            raise InvalidInput("The building belongs to another property.", field="building_id")
        amenity = Amenity(property=prop, building=building, created_by=actor)
        apply_changes(amenity, data, AMENITY_FIELDS)
        AmenityService._validate(amenity)
        with translate_integrity_errors(AMENITY_CONSTRAINTS):
            amenity.save()
        AuditService.record(
            actor=actor, action=AmenityAudit.CREATED, target=amenity, property_id=prop.pk
        )
        return amenity

    @staticmethod
    @transaction.atomic
    def update(*, actor, amenity: Amenity, changes: dict) -> Amenity:
        """Existing bookings keep the rules they were accepted under."""
        if not AmenityPolicy.can_update(actor, amenity):
            raise PermissionDenied("Only the property management can edit amenities.")
        amenity = Amenity.objects.select_for_update(of=("self",)).get(pk=amenity.pk)
        fields = apply_changes(amenity, changes, AMENITY_FIELDS)
        AmenityService._validate(amenity)
        if fields:
            with translate_integrity_errors(AMENITY_CONSTRAINTS):
                amenity.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=AmenityAudit.UPDATED,
                target=amenity,
                property_id=amenity.property_id,
                metadata={"fields": fields},
            )
        return amenity

    @staticmethod
    @transaction.atomic
    def add_images(*, actor, amenity: Amenity, files) -> list:
        if not AmenityPolicy.can_update(actor, amenity):
            raise PermissionDenied("Only the property management can edit amenities.")
        return AttachmentService.attach(
            entity_type=EntityType.AMENITY,
            entity_id=amenity.pk,
            files=list(files),
            uploaded_by=actor,
        )

    @staticmethod
    @transaction.atomic
    def remove_image(*, actor, amenity: Amenity, attachment_id: int) -> None:
        if not AmenityPolicy.can_update(actor, amenity):
            raise PermissionDenied("Only the property management can edit amenities.")
        AttachmentService.delete(
            attachment=AttachmentService.get(
                entity_type=EntityType.AMENITY, entity_id=amenity.pk, attachment_id=attachment_id
            )
        )

    @staticmethod
    @transaction.atomic
    def delete(*, actor, amenity: Amenity) -> None:
        """Removable while it was never booked; otherwise deactivate it."""
        if not AmenityPolicy.can_delete(actor, amenity):
            raise PermissionDenied("Only the property management can delete amenities.")
        AuditService.record(
            actor=actor,
            action=AmenityAudit.DELETED,
            target=amenity,
            property_id=amenity.property_id,
        )
        with deleting("amenity", hint="Set it inactive instead to keep past bookings."):
            AttachmentService.delete_for_entity(EntityType.AMENITY, amenity.pk)
            amenity.delete()

    @staticmethod
    def schedule(
        *, actor, amenity: Amenity, start: dt.datetime, end: dt.datetime
    ) -> QuerySet[Booking]:
        """Blocking bookings in a window (availability view, no personal data)."""
        if not AmenityPolicy.can_view(actor, amenity):
            raise NotFound("Amenity not found.")
        return Booking.objects.filter(
            amenity=amenity,
            status__in=BLOCKING_BOOKING_STATUSES,
            start_datetime__lt=end,
            end_datetime__gt=start,
        ).order_by("start_datetime")
