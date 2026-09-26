"""Domain errors of the accounts module."""

from apps.common.exceptions import BusinessRuleViolation, InvalidInput


def email_taken() -> InvalidInput:
    return InvalidInput(
        "An account already uses this e-mail address.",
        field="email",
        code="email_taken",
    )


def already_assigned() -> BusinessRuleViolation:
    return BusinessRuleViolation(
        "This assignment already exists.", code="already_assigned"
    )
