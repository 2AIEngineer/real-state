"""Domain errors of the library module."""

from apps.common.exceptions import InvalidInput


def folder_name_taken() -> InvalidInput:
    return InvalidInput(
        "A folder with this name already exists here.",
        field="en_name",
        code="name_taken",
    )
