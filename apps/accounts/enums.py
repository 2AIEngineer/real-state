"""Vocabularies of accounts and roles."""

from django.db import models


class StructuralRole(models.TextChoices):
    """The single, platform-wide role of an account (`User.role`).

    Where a role is exercised is a separate concern, held by the assignment
    tables of the `accounts` module. Owner and tenant are not account roles:
    they are derived from UnitOwnership / LeaseMember (see `PropertyRole`).
    """

    ADMIN = "admin", "Administrator"
    SYNDIC = "syndic", "Syndic"
    MANAGER = "manager", "Manager"
    SECURITY = "security", "Security"
    MAINTENANCE = "maintenance", "Maintenance"
    CLEANING = "cleaning", "Cleaning"
    PROVIDER = "provider", "Service provider"
    # Default role: pure owners/tenants, no operational function, no authority.
    STANDARD = "standard", "Standard account"


class Gender(models.TextChoices):
    """Gender of a person: an account holder or a short-term rental member."""

    FEMALE = "FEMALE", "Female"
    MALE = "MALE", "Male"
    OTHER = "OTHER", "Other"
    UNDISCLOSED = "UNDISCLOSED", "Undisclosed"


class PropertyRole(models.TextChoices):
    """The roles an announcement, event, document or survey can be addressed to.

    Staff roles are account roles (`User.role`), the same in every property;
    they reach a user only in the properties where that role applies. Owner
    and tenant are never stored: they are derived, property by property,
    from UnitOwnership / LeaseMember.
    """

    ADMIN = "admin", "Administrators"
    SYNDIC = "syndic", "Syndics"
    MANAGER = "manager", "Managers"
    SECURITY = "security", "Security"
    MAINTENANCE = "maintenance", "Maintenance"
    CLEANING = "cleaning", "Cleaning"
    PROVIDER = "provider", "Service providers"
    OWNER = "owner", "Owners"
    TENANT = "tenant", "Tenants"


# Full authority over the *content* of a property (buildings, units, leases,
# feature modules) on the properties they are assigned to.
MANAGEMENT_ROLES: tuple[str, ...] = (
    StructuralRole.ADMIN,
    StructuralRole.SYNDIC,
    StructuralRole.MANAGER,
)

# Authority over the property / syndicat records themselves and over the
# assignments of syndics and managers. Managers are deliberately excluded.
RECORD_MANAGEMENT_ROLES: tuple[str, ...] = (
    StructuralRole.ADMIN,
    StructuralRole.SYNDIC,
)

# Roles exercised on site, attached to buildings or properties.
FIELD_ROLES: tuple[str, ...] = (
    StructuralRole.SECURITY,
    StructuralRole.CLEANING,
    StructuralRole.MAINTENANCE,
)

# Roles that exist somewhere in the property tree (i.e. can be property members).
STAFF_ROLES: tuple[str, ...] = MANAGEMENT_ROLES + FIELD_ROLES

# Roles an announcement, event, document or survey can be addressed to.
# Providers are platform-wide and attached to no property, so they are excluded.
TARGETABLE_ROLES: frozenset[str] = frozenset(
    role for role in PropertyRole.values if role != PropertyRole.PROVIDER
)
