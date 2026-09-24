"""Domain errors of the amenities module."""

from apps.common.exceptions import BusinessRuleViolation, InvalidInput


def amenity_name_taken() -> InvalidInput:
    return InvalidInput("An amenity with this name already exists.", field="name")


def slot_taken() -> BusinessRuleViolation:
    return BusinessRuleViolation("This time slot is already booked.", code="slot_unavailable")
