"""Domain-level errors raised by services.

Services never raise DRF exceptions: they raise these, and the API layer
(`apps.common.api.exception_handler`) maps them to HTTP responses. This keeps the
service layer callable from management commands, workers and tests without
any dependency on the request/response cycle.
"""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    status_code = 400
    default_code = "domain_error"
    default_message = "The operation could not be completed."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.field = field
        self.details = details or {}
        super().__init__(self.message)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.field:
            payload["field"] = self.field
        if self.details:
            payload["details"] = self.details
        return payload


class InvalidInput(DomainError):
    """Input is well-formed but semantically invalid for the domain."""

    status_code = 400
    default_code = "invalid"
    default_message = "Invalid input."


class BusinessRuleViolation(DomainError):
    """The request conflicts with the current state of the domain."""

    status_code = 409
    default_code = "rule_violation"
    default_message = "This operation violates a business rule."


class InvalidTransition(BusinessRuleViolation):
    default_code = "invalid_transition"
    default_message = "This status transition is not allowed."


class NotFound(DomainError):
    status_code = 404
    default_code = "not_found"
    default_message = "Resource not found."


class PermissionDenied(DomainError):
    status_code = 403
    default_code = "permission_denied"
    default_message = "You are not allowed to perform this action."


class FeatureDisabled(PermissionDenied):
    default_code = "feature_disabled"
    default_message = "This feature is not enabled for this property."
