"""Taking part in a survey, and reading its results.

Each user participates once, answering every question in one submission.
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.common.db import translate_integrity_errors
from apps.common.exceptions import (
    InvalidInput,
    InvalidTransition,
    PermissionDenied,
)
from apps.notifications.services import SnapshotService
from apps.surveys import errors
from apps.surveys.models import (
    Survey,
    SurveyAnswer,
    SurveyResponse,
    SurveyStatus,
)
from apps.surveys.policies import SurveyPolicy
from apps.surveys.services.surveys import effective_status


class ParticipationService:
    @staticmethod
    def answered_ids(*, user) -> set[int]:
        return set(SurveyResponse.objects.filter(user=user).values_list("survey_id", flat=True))

    @staticmethod
    def has_answered(user, survey: Survey) -> bool:
        return SurveyResponse.objects.filter(survey=survey, user=user).exists()

    @staticmethod
    @transaction.atomic
    def respond(*, actor, survey: Survey, answers: dict[int, int]) -> SurveyResponse:
        """`answers` maps question id -> selected option id; all questions are required."""
        survey = Survey.objects.select_related("property").get(pk=survey.pk)
        if effective_status(survey, timezone.now()) != SurveyStatus.PUBLISHED:
            raise InvalidTransition("This survey is not open for answers.")
        if not SurveyPolicy.can_respond(actor, survey):
            raise PermissionDenied("This survey is not addressed to you.")
        questions = {q.pk: q for q in survey.questions.prefetch_related("options")}
        if set(answers) != set(questions):
            raise InvalidInput("Every question must be answered exactly once.", field="answers")
        for question_id, option_id in answers.items():
            if option_id not in {o.pk for o in questions[question_id].options.all()}:
                raise InvalidInput(
                    f"Option {option_id} does not belong to question {question_id}.",
                    field="answers",
                )
        with translate_integrity_errors({"unique_survey_participation": errors.already_answered}):
            response = SurveyResponse.objects.create(survey=survey, user=actor)
        SurveyAnswer.objects.bulk_create(
            [
                SurveyAnswer(response=response, question_id=qid, selected_option_id=oid)
                for qid, oid in answers.items()
            ]
        )
        return response

    @staticmethod
    def results(*, actor, survey: Survey) -> dict:
        """Aggregated counts. Managers anytime; the people it is addressed to once it is closed."""
        closed = effective_status(survey, timezone.now()) == SurveyStatus.CLOSED
        if not SurveyPolicy.can_view_results(actor, survey, is_closed=closed):
            raise PermissionDenied("Results are available once the survey is closed.")
        counts = dict(
            SurveyAnswer.objects.filter(response__survey=survey)
            .values_list("selected_option_id")
            .annotate(n=Count("id"))
            .values_list("selected_option_id", "n")
        )
        return {
            "survey_id": survey.pk,
            "participants": survey.responses.count(),
            "recipients": SnapshotService.count(survey),
            "questions": [
                {
                    "id": q.pk,
                    "text": q.text,
                    "options": [
                        {"id": o.pk, "text": o.text, "votes": counts.get(o.pk, 0)}
                        for o in q.options.all()
                    ],
                }
                for q in survey.questions.prefetch_related("options")
            ],
        }
