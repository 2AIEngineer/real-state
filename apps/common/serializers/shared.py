"""Serializer building blocks shared by every module (shape only, no rules)."""

from rest_framework import serializers


class UserSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    email = serializers.EmailField(read_only=True)


class UploadFilesSerializer(serializers.Serializer):
    files = serializers.ListField(child=serializers.FileField(), allow_empty=False)


class UploadFileSerializer(serializers.Serializer):
    file = serializers.FileField()


class ActionReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=2000
    )


class ActionNoteSerializer(serializers.Serializer):
    note = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=4000
    )


class BulkActionResultSerializer(serializers.Serializer):
    """Outcome of a bulk action: how many records it changed (0 when nothing was due)."""

    count = serializers.IntegerField(min_value=0)
