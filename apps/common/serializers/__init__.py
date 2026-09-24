"""Serializer building blocks shared by every module (shape only, no rules)."""

from apps.common.serializers.attachments import AttachmentSerializer, AttachmentsField
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
    "AttachmentSerializer",
    "AttachmentsField",
    "UploadFileSerializer",
    "UploadFilesSerializer",
    "UserSummarySerializer",
]
