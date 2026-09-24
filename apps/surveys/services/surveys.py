"""Surveys: single-choice questionnaires addressed to target roles.

    DRAFT ──publish──▶ PUBLISHED ──close (or closes_at reached)──▶ CLOSED

Questions are editable in DRAFT only. Answering and results are in
`participation.py`.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Count, Prefetch, QuerySet
from django.utils import timezone

from apps.common.db import apply_changes, deleting
from apps.common.exceptions import (
    BusinessRuleViolation,
    InvalidInput,
    InvalidTransition,
    NotFound,
    PermissionDenied,
)
from apps.common.files.rules import EntityType
from apps.common.files.service import AttachmentService
from apps.common.services.audit import AuditService
from apps.notifications.services import SnapshotService, delete_notification_traces
from apps.properties.enums import Feature
from apps.properties.models import Property
from apps.properties.services import FeatureGate
from apps.surveys import notices
from apps.surveys.audit import SurveyAudit
from apps.surveys.models import (
    Survey,
    SurveyOption,
    SurveyQuestion,
    SurveyStatus,
)
from apps.surveys.policies import SurveyPolicy

MIN_OPTIONS = 2
DRAFT_FIELDS = ("title", "description", "closes_at")


@dataclass
class QuestionInput:
    text: str
    options: list[str] = field(default_factory=list)


def _write_questions(survey: Survey, questions: list[QuestionInput]) -> None:
    survey.questions.all().delete()
    for q_position, question in enumerate(questions):
        row = SurveyQuestion.objects.create(
            survey=survey, text=question.text.strip(), position=q_position
        )
        SurveyOption.objects.bulk_create(
            [
                SurveyOption(question=row, text=text.strip(), position=o_position)
                for o_position, text in enumerate(question.options)
            ]
        )


def _prefetched() -> QuerySet[Survey]:
    return Survey.objects.select_related("property", "created_by").prefetch_related(
        Prefetch("questions", queryset=SurveyQuestion.objects.prefetch_related("options"))
    )


def effective_status(survey: Survey, now: dt.datetime) -> str:
    if survey.status == SurveyStatus.PUBLISHED and survey.closes_at and survey.closes_at <= now:
        return SurveyStatus.CLOSED
    return survey.status


class SurveyService:
    # ---------------------------------------------------------------- queries
    @staticmethod
    def list_visible(*, actor, prop: Property, status: str | None = None) -> QuerySet[Survey]:
        if not SurveyPolicy.can_list(actor, prop):
            raise PermissionDenied("You have no link with this property.")
        FeatureGate.require(prop, Feature.SURVEYS)
        qs = _prefetched().filter(property=prop)
        if not SurveyPolicy.is_management(actor, prop):
            qs = qs.exclude(status=SurveyStatus.DRAFT).filter(SurveyPolicy.addressed_filter(actor))
        if status:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def get_visible(*, actor, prop: Property, survey_id: int) -> Survey:
        survey = _prefetched().filter(pk=survey_id, property=prop).first()
        if survey is None or not SurveyPolicy.can_view(actor, survey):
            raise NotFound("Survey not found.")
        return survey

    # -------------------------------------------------------------- authoring
    @staticmethod
    @transaction.atomic
    def create_draft(
        *,
        actor,
        prop: Property,
        title: str,
        target_roles: list[str],
        questions: list[QuestionInput],
        description: str = "",
        closes_at: dt.datetime | None = None,
    ) -> Survey:
        if not SurveyPolicy.can_author(actor, prop):
            raise PermissionDenied("Only the property management can manage surveys.")
        FeatureGate.require(prop, Feature.SURVEYS)
        survey = Survey.objects.create(
            property=prop,
            title=title.strip(),
            description=description,
            target_roles=SnapshotService.validate_target_roles(target_roles),
            closes_at=closes_at,
            created_by=actor,
        )
        _write_questions(survey, questions)
        AuditService.record(
            actor=actor, action=SurveyAudit.DRAFTED, target=survey, property_id=prop.pk
        )
        return survey

    @staticmethod
    def _lock_draft(survey: Survey) -> Survey:
        survey = (
            Survey.objects.select_for_update(of=("self",))
            .select_related("property")
            .get(pk=survey.pk)
        )
        if survey.status != SurveyStatus.DRAFT:
            raise InvalidTransition("A published survey can no longer be edited.")
        return survey

    @staticmethod
    @transaction.atomic
    def update_draft(
        *, actor, survey: Survey, changes: dict, questions: list[QuestionInput] | None = None
    ) -> Survey:
        if not SurveyPolicy.can_author(actor, survey.property):
            raise PermissionDenied("Only the property management can manage surveys.")
        survey = SurveyService._lock_draft(survey)
        fields = apply_changes(survey, changes, DRAFT_FIELDS)
        if "target_roles" in changes:
            survey.target_roles = SnapshotService.validate_target_roles(changes["target_roles"])
            fields.append("target_roles")
        if fields:
            survey.save(update_fields=[*fields, "updated_at"])
        if questions is not None:
            _write_questions(survey, questions)
        AuditService.record(
            actor=actor,
            action=SurveyAudit.DRAFT_UPDATED,
            target=survey,
            property_id=survey.property_id,
        )
        return survey

    @staticmethod
    @transaction.atomic
    def publish(*, actor, survey: Survey) -> Survey:
        if not SurveyPolicy.can_author(actor, survey.property):
            raise PermissionDenied("Only the property management can manage surveys.")
        FeatureGate.require(survey.property, Feature.SURVEYS)
        survey = SurveyService._lock_draft(survey)
        questions = list(survey.questions.annotate(options_count=Count("options")))
        if not questions:
            raise BusinessRuleViolation("A survey needs at least one question.", code="no_question")
        if any(q.options_count < MIN_OPTIONS for q in questions):
            raise BusinessRuleViolation(
                f"Every question needs at least {MIN_OPTIONS} options.", code="not_enough_options"
            )
        now = timezone.now()
        if survey.closes_at and survey.closes_at <= now:
            raise InvalidInput("The closing date is already past.", field="closes_at")
        survey.status = SurveyStatus.PUBLISHED
        survey.published_at = now
        survey.save(update_fields=["status", "published_at", "updated_at"])
        recipients = SnapshotService.freeze(
            target=survey, prop=survey.property, target_roles=survey.target_roles
        )
        AuditService.record(
            actor=actor, action=SurveyAudit.PUBLISHED, target=survey, property_id=survey.property_id
        )
        notices.published(survey, recipients=recipients, actor=actor)
        return survey

    @staticmethod
    @transaction.atomic
    def close(*, actor, survey: Survey) -> Survey:
        if not SurveyPolicy.can_author(actor, survey.property):
            raise PermissionDenied("Only the property management can manage surveys.")
        survey = Survey.objects.select_for_update(of=("self",)).get(pk=survey.pk)
        if survey.status != SurveyStatus.PUBLISHED:
            raise InvalidTransition("Only published surveys can be closed.")
        survey.status = SurveyStatus.CLOSED
        survey.closed_at = timezone.now()
        survey.save(update_fields=["status", "closed_at", "updated_at"])
        AuditService.record(
            actor=actor, action=SurveyAudit.CLOSED, target=survey, property_id=survey.property_id
        )
        notices.closed(survey, actor=actor)
        return survey

    @staticmethod
    def close_expired(*, now: dt.datetime | None = None) -> int:
        """Scheduled job: surveys past `closes_at` become CLOSED and their
        recipients are told the results are available."""
        now = now or timezone.now()
        due = Survey.objects.filter(status=SurveyStatus.PUBLISHED, closes_at__lte=now)
        closed = 0
        for survey_id in due.values_list("id", flat=True):
            with transaction.atomic():
                survey = (
                    Survey.objects.select_for_update(of=("self",), skip_locked=True)
                    .select_related("property")
                    .filter(pk=survey_id, status=SurveyStatus.PUBLISHED)
                    .first()
                )
                if survey is None:
                    continue  # closed meanwhile, or being handled by another run
                survey.status = SurveyStatus.CLOSED
                survey.closed_at = now
                survey.save(update_fields=["status", "closed_at", "updated_at"])
                notices.closed(survey, actor=None)
                closed += 1
        return closed

    @staticmethod
    @transaction.atomic
    def add_files(*, actor, survey: Survey, files) -> list:
        if not SurveyPolicy.can_author(actor, survey.property):
            raise PermissionDenied("Only the property management can manage surveys.")
        return AttachmentService.attach(
            entity_type=EntityType.SURVEY, entity_id=survey.pk, files=list(files), uploaded_by=actor
        )

    @staticmethod
    @transaction.atomic
    def delete(*, actor, survey: Survey) -> None:
        """Removable while nobody answered; a survey with answers is closed, not erased."""
        if not SurveyPolicy.can_author(actor, survey.property):
            raise PermissionDenied("Only the property management can manage surveys.")
        if survey.responses.exists():
            raise BusinessRuleViolation(
                "This survey already has answers: close it instead of deleting it.",
                code="survey_has_responses",
            )
        AuditService.record(
            actor=actor, action=SurveyAudit.DELETED, target=survey, property_id=survey.property_id
        )
        with deleting("survey"):
            AttachmentService.delete_for_entity(EntityType.SURVEY, survey.pk)
            delete_notification_traces(survey)
            survey.delete()
