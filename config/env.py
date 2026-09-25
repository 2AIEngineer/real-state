"""Reading settings from the process environment.

The `.env` file at the repository root (or next to it) is loaded for local
development only when present; a value already in the environment wins.

The test suite reads nothing from it but the database connection: whatever a
developer's `.env` says (a storage account, a time zone, token lifetimes…),
tests run on the same settings everywhere.
"""

import os
from pathlib import Path

from dotenv import dotenv_values

ENVIRONMENTS = ("development", "test", "production")


# What the test profile takes from a local `.env`: how to reach the database.
TEST_KEYS_PREFIX = "POSTGRES_"


def load_dotenv_files(base_dir: Path) -> None:
    only_database = os.environ.get("ENVIRONMENT") == "test"
    for candidate in (base_dir / ".env", base_dir.parent / ".env"):
        if not candidate.exists():
            continue
        for name, value in dotenv_values(candidate).items():
            if value is None or name in os.environ:
                continue
            if only_database and not name.startswith(TEST_KEYS_PREFIX):
                continue
            os.environ[name] = value


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


def env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in (env(name, default) or "").split(",") if item.strip()]


def environment() -> str:
    """The profile; an unknown value stops the start-up instead of guessing."""
    value = env("ENVIRONMENT", "development")
    if value not in ENVIRONMENTS:
        raise RuntimeError(f"ENVIRONMENT must be one of {', '.join(ENVIRONMENTS)}, not {value!r}.")
    return value


def required_secret(name: str, *, production: bool, min_length: int = 32) -> str | None:
    """A secret that production must provide, long enough to sign with."""
    value = env(name)
    if production and not value:
        raise RuntimeError(f"{name} must be set in production.")
    if production and len(value) < min_length:
        raise RuntimeError(f"{name} must be at least {min_length} characters long in production.")
    return value
