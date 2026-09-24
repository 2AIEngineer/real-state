"""Domain errors of the properties module."""

from apps.common.exceptions import InvalidInput, PermissionDenied


def syndicat_name_taken() -> InvalidInput:
    return InvalidInput(
        "A syndicat with this name already exists.", field="name", code="name_taken"
    )


def promoter_name_taken() -> InvalidInput:
    return InvalidInput(
        "A promoter with this name already exists.", field="name", code="name_taken"
    )


def property_name_taken() -> InvalidInput:
    return InvalidInput(
        "A property with this name already exists in this syndicat.",
        field="name",
        code="name_taken",
    )


def building_name_taken() -> InvalidInput:
    return InvalidInput(
        "A building with this name already exists in this property.",
        field="name",
        code="name_taken",
    )


def unit_number_taken() -> InvalidInput:
    return InvalidInput(
        "A unit with this number already exists in this building.",
        field="number",
        code="number_taken",
    )


def admins_only() -> PermissionDenied:
    return PermissionDenied("Only platform administrators can perform this action.")


def record_managers_only() -> PermissionDenied:
    return PermissionDenied("Only administrators and syndics can modify this record.")


def no_link_with_property() -> PermissionDenied:
    return PermissionDenied("You have no link with this property.")
