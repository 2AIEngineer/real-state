"""Domain errors of the short-term rental module."""

from apps.common.exceptions import BusinessRuleViolation


def rental_overlap() -> BusinessRuleViolation:
    return BusinessRuleViolation(
        "Another short rental already occupies this unit on these dates.",
        code="short_term_rental_overlap",
    )
