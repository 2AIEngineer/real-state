from __future__ import annotations

from collections import defaultdict

from rest_framework import serializers

from apps.common.files import links
from apps.common.files.service import AttachmentService
from apps.common.models import Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    """A stored file with a ready-to-use URL: no extra call, no header to read it.

    `url` is a signed link (see `links.py`): permanent for public files,
    personal and renewed on every response for private ones.
    """

    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            "id",
            "entity_type",
            "entity_id",
            "url",
            "original_filename",
            "mime_type",
            "size",
            "checksum_sha256",
            "position",
            "uploaded_by",
            "created_at",
        ]
        read_only_fields = fields

    def get_url(self, obj: Attachment) -> str:
        request = self.context.get("request")
        path = links.path_of(obj, getattr(request, "user", None))
        return request.build_absolute_uri(path) if request else path


class AttachmentsField(serializers.Field):
    """Read-only list (or single item) of the files of one entity type,
    for the serialized object (`entity_id` = its primary key).

    Loads the files of every object of the page in one query instead of one
    query per row.
    """

    def __init__(self, entity_type: str, single: bool = False, **kwargs):
        self.entity_type = entity_type
        self.single = single
        kwargs.update(read_only=True, source="*")
        super().__init__(**kwargs)

    def _siblings(self, obj) -> list:
        instance = getattr(self.root, "instance", None)
        if isinstance(instance, (list, tuple)):
            candidates = list(instance)
        elif hasattr(instance, "__iter__") and not isinstance(instance, dict):
            candidates = list(instance)
        else:
            candidates = [obj]
        same_type = [o for o in candidates if type(o) is type(obj)]
        return same_type or [obj]

    def to_representation(self, obj):
        cache = self.context.setdefault("_attachments_cache", {})
        key = self.entity_type
        bucket = cache.setdefault(key, {"loaded": set(), "rows": defaultdict(list)})
        if obj.pk not in bucket["loaded"]:
            entities = [o for o in self._siblings(obj) if o.pk not in bucket["loaded"]] or [obj]
            ids = {o.pk for o in entities} | {obj.pk}
            for row in AttachmentService.list_for_entities(self.entity_type, ids):
                bucket["rows"][row.entity_id].append(row)
            bucket["loaded"] |= ids
        rows = bucket["rows"].get(obj.pk, [])
        serializer = AttachmentSerializer(context=self.context)
        if self.single:
            return serializer.to_representation(rows[0]) if rows else None
        return [serializer.to_representation(row) for row in rows]
