"""Domain errors of the leasing module."""

from apps.common.exceptions import BusinessRuleViolation, InvalidInput


def lease_overlap() -> BusinessRuleViolation:
    return BusinessRuleViolation(
        "Another active lease already covers this unit for (part of) this period.",
        code="lease_overlap",
    )


def contract_reference_taken() -> InvalidInput:
    return InvalidInput(
        "This contract reference is already used.",
        field="contract_reference",
        code="reference_taken",
    )


def component_already_recorded() -> InvalidInput:
    return InvalidInput("This component is already recorded for this inspection.", field="name")


def already_member() -> InvalidInput:
    return InvalidInput(
        "This user is already recorded on this lease.",
        field="user_id",
        code="already_member",
    )
