"""Database helpers shared by services."""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterable, Mapping
from contextlib import contextmanager
from typing import Any

from django.contrib.postgres.fields import DateRangeField, DateTimeRangeField
from django.db import IntegrityError, transaction
from django.db.models import Func, Model, ProtectedError

from apps.common.exceptions import BusinessRuleViolation, DomainError


class DateRange(Func):
    """`daterange(lower, upper, bounds)` — used by exclusion constraints."""

    function = "daterange"
    output_field = DateRangeField()


class DateTimeRange(Func):
    """`tstzrange(lower, upper, bounds)` — used by exclusion constraints."""

    function = "tstzrange"
    output_field = DateTimeRangeField()


def apply_changes(
    instance: Model, changes: Mapping[str, Any], allowed: Iterable[str]
) -> list[str]:
    """Set on `instance` the `allowed` fields present in `changes`; return their names.

    The whitelist is what makes a partial update safe: a field outside `allowed`
    is ignored whatever the client sent. Text is stripped. The caller saves with
    `update_fields=[*fields, "updated_at"]`, so only what changed is written.
    """
    fields = [name for name in allowed if name in changes]
    for name in fields:
        value = changes[name]
        setattr(instance, name, value.strip() if isinstance(value, str) else value)
    return fields


def constraint_name_of(exc: IntegrityError) -> str | None:
    cause = exc.__cause__
    diag = getattr(cause, "diag", None)
    return getattr(diag, "constraint_name", None)


ErrorFactory = Callable[[], DomainError]


@contextmanager
def translate_integrity_errors(
    mapping: Mapping[str, ErrorFactory | str],
) -> Generator[None, None, None]:
    """Turn known constraint violations into domain errors.

    Runs the block inside a savepoint so the surrounding transaction stays
    usable after a violation. `mapping` keys are constraint names; values are
    either a factory building the DomainError (a fresh one per violation, never
    a shared instance) or a message for BusinessRuleViolation.
    """
    for target in mapping.values():
        if isinstance(target, DomainError):
            raise TypeError(
                "Map constraints to error factories, not to exception instances."
            )
    try:
        with transaction.atomic():
            yield
    except IntegrityError as exc:
        name = constraint_name_of(exc)
        if name and name in mapping:
            target = mapping[name]
            if isinstance(target, str):
                raise BusinessRuleViolation(target, code=name) from exc
            raise target() from exc
        raise


def describe_protected(exc: ProtectedError) -> dict[str, int]:
    """What still references the row, as {label: count}."""
    blockers: dict[str, int] = {}
    for obj in exc.protected_objects:
        label = obj._meta.verbose_name_plural.title()
        blockers[label] = blockers.get(label, 0) + 1
    return blockers


@contextmanager
def deleting(what: str, *, hint: str = "") -> Generator[None]:
    """Run a delete, turning `PROTECT` violations into a domain error.

    Deletion is refused as soon as business history points at the row; the
    caller gets the list of blockers and, when relevant, the alternative.
    """
    try:
        with transaction.atomic():
            yield
    except ProtectedError as exc:
        blockers = describe_protected(exc)
        detail = ", ".join(
            f"{label} ({count})" for label, count in sorted(blockers.items())
        )
        raise BusinessRuleViolation(
            f"This {what} is still used by: {detail}." + (f" {hint}" if hint else ""),
            code="resource_in_use",
            details=blockers,
        ) from exc
