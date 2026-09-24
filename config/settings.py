"""Project settings, driven entirely by environment variables.

`ENVIRONMENT` selects the profile (development, test, production). Every value
that differs between environments is read from the process environment; the
`.env` files at the repository root and next to this project are loaded for
local development only when present.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

for candidate in (BASE_DIR / ".env", BASE_DIR.parent / ".env"):
    if candidate.exists():
        load_dotenv(candidate, override=False)


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


ENVIRONMENT = env("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"
IS_TEST = ENVIRONMENT == "test"

SECRET_KEY = env("SECRET_KEY") or ("insecure-development-key" if not IS_PRODUCTION else None)
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set in production.")

DEBUG = env_bool("DEBUG", default=not IS_PRODUCTION)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "*" if not IS_PRODUCTION else "")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# Front-end base URL used to build links in e-mails (password setup, deep links).
SITE_URL = (env("SITE_URL", "http://localhost:5173/") or "").rstrip("/")

# Branding of the e-mails: header logo, footer links and copyright.
BRAND = {
    "NAME": env("BRAND_NAME", "Urbis"),
    "LOGO_URL": env("BRAND_LOGO_URL", "https://urbisapp.com/logo.png"),
    "DASHBOARD_URL": env("BRAND_DASHBOARD_URL", "https://app-urbis.com/account/login"),
    "WEBSITE_URL": env("BRAND_WEBSITE_URL", "https://urbisapp.com/fr"),
}

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.postgres",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "corsheaders",
    # Shared kernel: base models, attachments, audit journal
    "apps.common",
    # Identity & authorization
    "apps.accounts",
    # Real-estate referential
    "apps.properties",
    "apps.leasing",
    # Cross-cutting infrastructure
    "apps.notifications",
    # Feature modules
    "apps.announcements",
    "apps.service_requests",
    "apps.work_orders",
    "apps.events",
    "apps.amenities",
    "apps.store",
    "apps.library",
    "apps.short_term_rental",
    "apps.surveys",
    "apps.marketplace",
    "apps.visitors",
    "apps.chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "residential"),
        "USER": env("POSTGRES_USER", "postgres"),
        "PASSWORD": env("POSTGRES_PASSWORD", ""),
        "HOST": env("POSTGRES_HOST", "localhost"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": int(env("POSTGRES_CONN_MAX_AGE", "60")),
        "ATOMIC_REQUESTS": False,
        "OPTIONS": {"sslmode": env("POSTGRES_SSLMODE", "require" if IS_PRODUCTION else "prefer")},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
# An invitation waits days for its first use; a reset of an account in use does not.
PASSWORD_RESET_TIMEOUT = int(env("PASSWORD_RESET_TIMEOUT", str(60 * 60 * 72)))
PASSWORD_RESET_LINK_TIMEOUT = int(env("PASSWORD_RESET_LINK_TIMEOUT", str(60 * 60 * 2)))

LANGUAGE_CODE = "fr"
LANGUAGES = [("fr", "Français"), ("en", "English")]
TIME_ZONE = env("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))

# Files. The container is private: every file is read through a signed link
# (`apps.common.files.links`). Production refuses to start without it, so
# personal documents can never end up on the server's disk.
AZURE_CONNECTION_STRING = env("AZURE_CONNECTION_STRING")
AZURE_CONTAINER = env("AZURE_CONTAINER")
if AZURE_CONNECTION_STRING and AZURE_CONTAINER:
    STORAGES = {
        "default": {
            "BACKEND": "apps.common.files.storage.AzureFileStorage",
            "OPTIONS": {
                "connection_string": AZURE_CONNECTION_STRING,
                "azure_container": AZURE_CONTAINER,
                "expiration_secs": None,
                "overwrite_files": False,
            },
        },
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
elif IS_PRODUCTION:
    raise RuntimeError("AZURE_CONNECTION_STRING and AZURE_CONTAINER must be set in production.")
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

FILES = {
    # A private link stays the same for a window, and is valid for one to two
    # windows: long enough for any page, short enough to leak little.
    "LINK_WINDOW_HOURS": int(env("FILES_LINK_WINDOW_HOURS", "12")),
}

# Hard ceiling for any upload; module-specific policies are stricter.
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.common.api.exception_handler",
    "DEFAULT_SCHEMA_CLASS": "apps.common.schema.UIConfigAwareAutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {"auth": env("AUTH_THROTTLE_RATE", "20/min")},
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}
if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append(
        "rest_framework.renderers.BrowsableAPIRenderer"
    )

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("JWT_ACCESS_MINUTES", "30"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("JWT_REFRESH_DAYS", "14"))),
    "ROTATE_REFRESH_TOKENS": True,
    # A rotated refresh token cannot be used twice (see apps.accounts.services.tokens).
    "BLACKLIST_AFTER_ROTATION": True,
    # Access tokens die with the password they were issued under.
    "CHECK_REVOKE_TOKEN": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "SIGNING_KEY": env("JWT_SIGNING_KEY", SECRET_KEY),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Residential Platform API",
    "DESCRIPTION": "Property management SaaS: referential, leasing, resident services.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    # Readable names for the enums that share a field name across modules
    # (otherwise suffixed with a hash: Category758Enum...).
    "ENUM_NAME_OVERRIDES": {
        "AnnouncementCategoryEnum": "apps.announcements.models.AnnouncementCategory",
        "AnnouncementPriorityEnum": "apps.announcements.models.AnnouncementPriority",
        "ListingCategoryEnum": "apps.marketplace.models.ListingCategory",
        "ServiceRequestCategoryEnum": "apps.service_requests.models.ServiceRequestCategory",
        "WorkOrderCategoryEnum": "apps.work_orders.models.WorkOrderCategory",
        # Same values for service requests and work orders.
        "PriorityEnum": "apps.service_requests.models.ServiceRequestPriority",
        "LeaseTerminationReasonEnum": "apps.leasing.models.LeaseTerminationReason",
        "BookingStatusEnum": "apps.amenities.models.BookingStatus",
        "RequesterNoticeEnum": "apps.service_requests.models.RequesterNotice",
        "ComponentConditionEnum": "apps.leasing.models.ComponentCondition",
        "CheckPhaseEnum": "apps.leasing.models.CheckPhase",
        "WorkOrderActionEnum": ["start", "hold", "complete", "cancel"],
        "PushPlatformEnum": [("ios", "iOS"), ("android", "Android"), ("web", "Web")],
        "ChatContextTypeEnum": ["service_request", "booking", "order"],
        "AccountRoleEnum": "apps.accounts.enums.StructuralRole",
        "PropertyRoleEnum": "apps.accounts.enums.PropertyRole",
        "SessionAppModeEnum": ["web", "mobile"],
        "UIConfigStepEnum": ["syndicat", "property", "dashboard"],
    },
}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# --- E-mail -----------------------------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    (
        "django.core.mail.backends.smtp.EmailBackend"
        if IS_PRODUCTION
        else "django.core.mail.backends.console.EmailBackend"
    ),
)
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_TIMEOUT = 20
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@localhost")

# --- Notifications ----------------------------------------------------------
NOTIFICATIONS = {
    "EMAIL_ENABLED": env_bool("ENABLED_EMAIL_NOTIFICATION", True),
    "PUSH_ENABLED": env_bool("ENABLED_PUSH_NOTIFICATION", True),
    "EXPO_PUSH_URL": env("EXPO_PUSH_URL", "https://exp.host/--/api/v2/push/send"),
    "EXPO_ACCESS_TOKEN": env("EXPO_ACCESS_TOKEN", ""),
    "OUTBOX_MAX_ATTEMPTS": int(env("OUTBOX_MAX_ATTEMPTS", "6")),
    "OUTBOX_BATCH_SIZE": int(env("OUTBOX_BATCH_SIZE", "50")),
    # When true, outbox messages are relayed right after the business
    # transaction commits (in-process). The `outbox_worker` command remains
    # the guaranteed delivery path (retries, crash recovery).
    "DELIVER_ON_COMMIT": env_bool("NOTIFICATIONS_DELIVER_ON_COMMIT", False),
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {"django.db.backends": {"level": "WARNING"}},
}

if IS_PRODUCTION:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = 31536000
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

if IS_TEST:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    MEDIA_ROOT = Path(env("TEST_MEDIA_ROOT", "/tmp/residential-test-media"))
    NOTIFICATIONS["DELIVER_ON_COMMIT"] = False
