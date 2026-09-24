"""Domain errors of the store module."""

from apps.common.exceptions import InvalidInput, PermissionDenied


def sku_taken() -> InvalidInput:
    return InvalidInput("This SKU is already used.", field="sku")


def store_admins_only() -> PermissionDenied:
    return PermissionDenied("The store is managed by platform administrators only.")
