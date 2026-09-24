"""What the people a survey is addressed to are told about it."""

from __future__ import annotations

from apps.notifications.models import NotificationCategory
from apps.notifications.services import NotificationIntent, NotificationService, SnapshotService
from apps.surveys.models import Survey


def _tell(survey: Survey, *, kind: str, title: str, body: str, recipients, actor, path: str):
    NotificationService.notify(
        NotificationIntent(
            event_type=f"survey.{kind}",
            category=NotificationCategory.SURVEY,
            title=f"[{survey.property.name}] {title}",
            body=body,
            bcc=recipients,
            target=survey,
            exclude=[actor] if actor else [],
            data={"survey_id": survey.pk, "property_id": survey.property_id},
            action_path=path,
        )
    )


def published(survey: Survey, *, recipients, actor) -> None:
    _tell(
        survey,
        kind="published",
        title="Nouveau sondage",
        body=f"« {survey.title} » — votre avis compte.",
        recipients=recipients,
        actor=actor,
        path=f"/surveys/{survey.pk}",
    )


def closed(survey: Survey, *, actor) -> None:
    """The people the survey was addressed to can now see its results."""
    _tell(
        survey,
        kind="closed",
        title="Sondage clos",
        body=f"« {survey.title} » est clos : les résultats sont disponibles.",
        recipients=SnapshotService.recipients(survey),
        actor=actor,
        path=f"/surveys/{survey.pk}/results",
    )
