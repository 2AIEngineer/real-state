"""Domain errors of the surveys module."""

from apps.common.exceptions import BusinessRuleViolation


def already_answered() -> BusinessRuleViolation:
    return BusinessRuleViolation("You have already answered this survey.", code="already_answered")
