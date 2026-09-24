"""Serializer building blocks shared by every module (shape only, no rules)."""

from apps.common.serializers.shared import (
    ActionNoteSerializer,
    ActionReasonSerializer,
    UploadFileSerializer,
    UploadFilesSerializer,
    UserSummarySerializer,
)

__all__ = [
    "ActionNoteSerializer",
    "ActionReasonSerializer",
    "UploadFileSerializer",
    "UploadFilesSerializer",
    "UserSummarySerializer",
]
