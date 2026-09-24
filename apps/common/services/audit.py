from __future__ import annotations

from typing import Any

from django.contrib.contenttypes.models import ContentType

from apps.common.models import AuditLogEntry


class AuditService:
    @staticmethod
    def record(
        *,
        actor,
        action: str,
        target=None,
        property_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        """Append an entry. Called inside the business transaction so the
        journal and the change it describes commit (or roll back) together.
        """
        return AuditLogEntry.objects.create(
            actor=actor if getattr(actor, "pk", None) else None,
            action=action,
            content_type=ContentType.objects.get_for_model(target) if target is not None else None,
            object_id=target.pk if target is not None else None,
            object_repr=str(target)[:255] if target is not None else "",
            property_id=property_id,
            metadata=metadata or {},
        )
