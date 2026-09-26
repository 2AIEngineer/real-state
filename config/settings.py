"""Project settings, driven entirely by environment variables.

`ENVIRONMENT` selects the profile (development, test, production). Every value
that differs between environments is read from the process environment (see
`config/env.py`). Production refuses to start when a secret or a service it
cannot run safely without is missing.
"""

import base64
import json
from datetime import timedelta
from pathlib import Path

from corsheaders.defaults import default_headers

from config.env import (
    env,
    env_bool,
    env_int,
    env_list,
    environment,
    load_dotenv_files,
    required_secret,
)
from config.openapi import SPECTACULAR_SETTINGS  # noqa: F401

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv_files(BASE_DIR)

# --- Profile and core --------------------------------------------------------
ENVIRONMENT = environment()
IS_PRODUCTION = ENVIRONMENT == "production"
IS_TEST = ENVIRONMENT == "test"

SECRET_KEY = required_secret("SECRET_KEY", production=IS_PRODUCTION) or (
    "insecure-development-key-" + "x" * 32
)
DEBUG = not IS_PRODUCTION
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "" if IS_PRODUCTION else "*")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# --- Front-end and e-mail branding -------------------------------------------
# Front-end base URL used to build links in e-mails (password setup, deep links).
SITE_URL = (env("SITE_URL", "http://localhost:5173/") or "").rstrip("/")

# Branding of the e-mails: header logo, footer links and copyright.
BRAND = {
    "NAME": env("BRAND_NAME", "Urbis"),
    "LOGO_URL": env("BRAND_LOGO_URL", "https://urbisapp.com/logo.png"),
    "DASHBOARD_URL": env("BRAND_DASHBOARD_URL", "https://app-urbis.com/account/login"),
    "WEBSITE_URL": env("BRAND_WEBSITE_URL", "https://urbisapp.com/fr"),
}

# --- Applications ------------------------------------------------------------
INSTALLED_APPS = [
    # Django built-ins
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.postgres",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Django REST Framework
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    # Third-party
    "corsheaders",
    "storages",
    "django_extensions",
    "whitenoise.runserver_nostatic",
    # Domain apps
    "apps.common",
    "apps.accounts",
    "apps.properties",
    "apps.leasing",
    "apps.notifications",
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
if not IS_PRODUCTION:
    # `manage.py seed_demo`: development data only.
    INSTALLED_APPS.append("apps.demo")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
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
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

# --- Database ----------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "residential"),
        "USER": env("POSTGRES_USER", "postgres"),
        "PASSWORD": env("POSTGRES_PASSWORD", ""),
        "HOST": env("POSTGRES_HOST", "localhost"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": env_int("POSTGRES_CONN_MAX_AGE", 60),
        "CONN_HEALTH_CHECKS": True,
        "ATOMIC_REQUESTS": False,
        "OPTIONS": {"sslmode": env("POSTGRES_SSLMODE", "require" if IS_PRODUCTION else "prefer")},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
# --- Accounts and passwords --------------------------------------------------
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

PASSWORD_RESET_TIMEOUT = 60 * 60 * 72  # 3 days for new account
PASSWORD_RESET_LINK_TIMEOUT = 60 * 60 * 2  # 2 hours for reset of an existing account

# --- Language and time -------------------------------------------------------
LANGUAGE_CODE = "fr"
LANGUAGES = [("fr", "Français"), ("en", "English")]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Files -------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))

if IS_PRODUCTION:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.azure_storage.AzureStorage",
            "OPTIONS": {
                "connection_string": required_secret(
                    "AZURE_CONNECTION_STRING", production=True, min_length=1
                ),
                "azure_container": required_secret(
                    "AZURE_CONTAINER", production=True, min_length=1
                ),
                "expiration_secs": None,
                "overwrite_files": False,
            },
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

# A request body other than files (JSON, form fields) is read in memory: keep it
# small. Files have their own limits, per kind, in `apps.common.attachments.rules`.
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# --- API ---------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
CORS_ALLOW_HEADERS = (
    *default_headers,
    "x-syndicat-id",
    "x-property-id",
    "x-ui-config-step",
    "idempotency-key",
    "x-webhook-secret",
)
CORS_EXPOSE_HEADERS = ("idempotent-replayed",)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PARSER_CLASSES": [
        "drf_orjson_renderer.parsers.ORJSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_RENDERER_CLASSES": ["drf_orjson_renderer.renderers.ORJSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.common.api.exception_handler",
    "DEFAULT_SCHEMA_CLASS": "apps.common.schema.UIConfigAwareAutoSchema",
    # Only the authentication endpoints are rate-limited: they are the ones an
    # attacker hammers, and a counter on every request would cost a write each.
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        # Per client address, on every authentication endpoint.
        "auth": "20/min",
        # Per account, on login: slows password guessing spread over addresses.
        "login": "10/min",
    },
    # Proxies in front of the app that append to X-Forwarded-For (the platform
    # ingress). The client address is read that many hops from the right, so
    # a client cannot pick its own address by sending the header itself.
    "NUM_PROXIES": 1 if IS_PRODUCTION else 0,
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}
if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append(
        "rest_framework.renderers.BrowsableAPIRenderer"
    )

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("JWT_ACCESS_MINUTES", 30)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_DAYS", 14)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "CHECK_REVOKE_TOKEN": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "SIGNING_KEY": SECRET_KEY,
}

# --- Cache -------------------------------------------------------------------
# authentication endpoints write to it (see REST_FRAMEWORK below).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_entries",
        "OPTIONS": {"MAX_ENTRIES": 50_000},
    }
}

# --- E-mail ------------------------------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    (
        "django.core.mail.backends.smtp.EmailBackend"
        if IS_PRODUCTION
        else "django.core.mail.backends.console.EmailBackend"
    ),
)
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_TIMEOUT = 20
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@localhost")

# --- Notifications -----------------------------------------------------------
NOTIFICATIONS = {
    "EMAIL_ENABLED": env_bool("ENABLED_EMAIL_NOTIFICATION", True),
    "PUSH_ENABLED": env_bool("ENABLED_PUSH_NOTIFICATION", True),
    "EXPO_PUSH_URL": env("EXPO_PUSH_URL", "https://exp.host/--/api/v2/push/send"),
    "OUTBOX_MAX_ATTEMPTS": env_int("OUTBOX_MAX_ATTEMPTS", 6),
    "OUTBOX_BATCH_SIZE": env_int("OUTBOX_BATCH_SIZE", 50),
    # How long delivered and abandoned messages are kept before being purged.
    "OUTBOX_RETENTION_DAYS": env_int("OUTBOX_RETENTION_DAYS", 30),
    "DELIVER_ON_COMMIT": env_bool("NOTIFICATIONS_DELIVER_ON_COMMIT", False),
}

# --- Logging -----------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {"django.db.backends": {"level": "WARNING"}},
}

# --- HTTPS behind the platform proxy -----------------------------------------
if IS_PRODUCTION:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_REDIRECT_EXEMPT = [r"^healthz/$", r"^readyz/$"]
    SECURE_HSTS_SECONDS = 31536000
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# --- Test profile ------------------------------------------------------------
if IS_TEST:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    MEDIA_ROOT = Path(env("TEST_MEDIA_ROOT", "/tmp/urbis-test-media"))
    NOTIFICATIONS["DELIVER_ON_COMMIT"] = False


# ---------------------------------------------------------------------------
# Firebase
# ---------------------------------------------------------------------------
FIREBASE_SERVICE_ACCOUNT_BASE64 = env("FIREBASE_SERVICE_ACCOUNT_BASE64", "")
FIREBASE_WEB_CONFIG_BASE64 = env("FIREBASE_WEB_CONFIG_BASE64", "")
if FIREBASE_SERVICE_ACCOUNT_BASE64 and FIREBASE_WEB_CONFIG_BASE64:
    _sa_raw: dict = json.loads(base64.b64decode(FIREBASE_SERVICE_ACCOUNT_BASE64).decode("utf-8"))
    _wc_raw: dict = json.loads(base64.b64decode(FIREBASE_WEB_CONFIG_BASE64).decode("utf-8"))

    FIREBASE_SERVICE_ACCOUNT_KEY = {
        "type": _sa_raw["type"],
        "project_id": _sa_raw["project_id"],
        "private_key_id": _sa_raw["private_key_id"],
        "private_key": _sa_raw["private_key"],
        "client_email": _sa_raw["client_email"],
        "client_id": _sa_raw["client_id"],
        "auth_uri": _sa_raw["auth_uri"],
        "token_uri": _sa_raw["token_uri"],
        "auth_provider_x509_cert_url": _sa_raw["auth_provider_x509_cert_url"],
        "client_x509_cert_url": _sa_raw["client_x509_cert_url"],
        "universe_domain": _sa_raw["universe_domain"],
    }
    FIREBASE_WEB_CONFIG = {
        "apiKey": _wc_raw["apiKey"],
        "authDomain": _wc_raw["authDomain"],
        "projectId": _wc_raw["projectId"],
        "storageBucket": _wc_raw["storageBucket"],
        "messagingSenderId": _wc_raw["messagingSenderId"],
        "appId": _wc_raw["appId"],
        "measurementId": _wc_raw["measurementId"],
    }

    FIREBASE_API_KEY = FIREBASE_WEB_CONFIG["apiKey"]
    FIREBASE_STORAGE_BUCKET = FIREBASE_WEB_CONFIG["storageBucket"]
    FIREBASE_PROJECT_ID = FIREBASE_WEB_CONFIG["projectId"]
    FIREBASE_ENV_PREFIX = "prod" if IS_PRODUCTION else "dev"
