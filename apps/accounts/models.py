from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

from apps.accounts.enums import Gender, StructuralRole
from apps.common.models import TimeStampedModel


class Language(models.TextChoices):
    FRENCH = "fr", "Français"
    ENGLISH = "en", "English"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email: str, password: str | None, **extra):
        if not email:
            raise ValueError("An e-mail address is required.")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email: str, password: str | None = None, **extra):
        extra["is_staff"] = True
        extra["is_superuser"] = True
        return self._create(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Application account.

    `role` is the single platform-wide function of the account; where it is
    exercised lives in the assignment tables at the bottom of this module.
    Owner/tenant statuses are derived from `properties.UnitOwnership` and
    `leasing.LeaseMember`. Role changes go through `RoleService` (audited),
    never direct writes.
    """

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=32, blank=True)
    gender = models.CharField(max_length=12, choices=Gender.choices, default=Gender.UNDISCLOSED)
    preferred_language = models.CharField(
        max_length=5, choices=Language.choices, default=Language.FRENCH
    )
    role = models.CharField(
        max_length=16, choices=StructuralRole.choices, default=StructuralRole.STANDARD
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False, help_text="Technical back-office access only.")
    is_technical_account = models.BooleanField(
        default=False,
        help_text="Non-human account (e.g. a promoter's legal representative). Never logs in.",
    )

    date_joined = models.DateTimeField(default=timezone.now)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        ordering = ["last_name", "first_name", "id"]
        constraints = [
            models.UniqueConstraint(Lower("email"), name="user_email_ci_unique"),
            models.CheckConstraint(
                condition=models.Q(is_active=True) | models.Q(deactivated_at__isnull=False),
                name="user_inactive_has_deactivation_date",
            ),
        ]
        indexes = [
            models.Index(fields=["is_active", "last_name"]),
            models.Index(fields=["role", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_full_name()} <{self.email}>"

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self) -> str:
        return self.first_name


class ProviderServiceType(models.TextChoices):
    PLUMBING = "plumbing", "Plumbing"
    ELECTRICITY = "electricity", "Electricity"
    HVAC = "hvac", "Heating / air conditioning"
    CARPENTRY = "carpentry", "Carpentry"
    PAINTING = "painting", "Painting"
    LOCKSMITH = "locksmith", "Locksmith"
    ELEVATOR = "elevator", "Elevator maintenance"
    CLEANING = "cleaning", "Cleaning"
    GARDENING = "gardening", "Gardening / landscaping"
    PEST_CONTROL = "pest_control", "Pest control"
    SECURITY = "security", "Security services"
    IT_NETWORK = "it_network", "IT / network"
    MOVING = "moving", "Moving"
    OTHER = "other", "Other"


class ProviderProfile(TimeStampedModel):
    """Complementary profile for accounts holding the `provider` role."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="provider_profile")
    company_name = models.CharField(max_length=200, blank=True)
    service_type = models.CharField(
        max_length=32,
        choices=ProviderServiceType.choices,
        default=ProviderServiceType.OTHER,
    )
    service_description = models.TextField(blank=True)
    address = models.TextField(blank=True)
    business_phone = models.CharField(max_length=32, blank=True)
    website = models.URLField(blank=True)
    registration_number = models.CharField(max_length=64, blank=True)

    class Meta:
        indexes = [models.Index(fields=["service_type"])]

    def __str__(self) -> str:
        return f"Provider profile of {self.user_id}"


# ---------------------------------------------------------------------------
# Where a user's role is exercised.
#
# The role itself is `User.role` (one per account, platform-wide). The three
# tables below only answer *where*: a syndicat as a whole, a property, or a
# building. They never carry a role: an assignment means "the user's role
# applies here".
# ---------------------------------------------------------------------------

REVOCATION_CONSISTENT = Q(is_active=True, revoked_at__isnull=True) | Q(
    is_active=False, revoked_at__isnull=False
)


class UserAssignmentBase(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    is_active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        abstract = True


class UserSyndicat(UserAssignmentBase):
    """Covers a whole syndicat, including properties added to it later."""

    syndicat = models.ForeignKey(
        "properties.Syndicat", on_delete=models.PROTECT, related_name="user_assignments"
    )

    class Meta:
        ordering = ["user_id", "syndicat_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "syndicat"],
                condition=Q(is_active=True),
                name="unique_active_user_syndicat",
            ),
            models.CheckConstraint(
                condition=REVOCATION_CONSISTENT, name="user_syndicat_revoked_consistent"
            ),
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["syndicat", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"user {self.user_id} → syndicat {self.syndicat_id}"


class UserProperty(UserAssignmentBase):
    """Covers one property (fixed list: never extends to other properties)."""

    property = models.ForeignKey(
        "properties.Property", on_delete=models.PROTECT, related_name="user_assignments"
    )

    class Meta:
        verbose_name_plural = "user properties"
        ordering = ["user_id", "property_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "property"],
                condition=Q(is_active=True),
                name="unique_active_user_property",
            ),
            models.CheckConstraint(
                condition=REVOCATION_CONSISTENT, name="user_property_revoked_consistent"
            ),
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["property", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"user {self.user_id} → property {self.property_id}"


class UserBuilding(UserAssignmentBase):
    """Covers one building and its units."""

    building = models.ForeignKey(
        "properties.Building", on_delete=models.PROTECT, related_name="user_assignments"
    )

    class Meta:
        ordering = ["user_id", "building_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "building"],
                condition=Q(is_active=True),
                name="unique_active_user_building",
            ),
            models.CheckConstraint(
                condition=REVOCATION_CONSISTENT, name="user_building_revoked_consistent"
            ),
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["building", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"user {self.user_id} → building {self.building_id}"


# Where each role is exercised. Admins need no assignment (they cover
# everything); standard accounts and providers are attached to nothing.
ROLES_ASSIGNED_TO_SYNDICATS: tuple[str, ...] = (StructuralRole.SYNDIC,)
ROLES_ASSIGNED_TO_PROPERTIES: tuple[str, ...] = (
    StructuralRole.MANAGER,
    StructuralRole.MAINTENANCE,
)
ROLES_ASSIGNED_TO_BUILDINGS: tuple[str, ...] = (
    StructuralRole.SECURITY,
    StructuralRole.CLEANING,
)
