import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.enums import PropertyRole
from apps.common.exceptions import (
    BusinessRuleViolation,
    InvalidInput,
    InvalidTransition,
    NotFound,
    PermissionDenied,
)
from apps.notifications.models import InboxNotification
from apps.surveys.models import SurveyStatus
from apps.surveys.services import ParticipationService, QuestionInput, SurveyService

pytestmark = pytest.mark.django_db
QUESTIONS = [
    QuestionInput("Repaint the lobby?", ["Yes", "No"]),
    QuestionInput("Colour?", ["White", "Grey", "Blue"]),
]


def draft(world, questions=QUESTIONS, roles=(PropertyRole.OWNER,), **kwargs):
    return SurveyService.create_draft(
        actor=world.manager,
        prop=world.prop,
        title="Lobby",
        target_roles=list(roles),
        questions=questions,
        **kwargs,
    )


def answers_for(survey, pick=0):
    return {q.pk: list(q.options.all())[pick].pk for q in survey.questions.all()}


def test_drafts_are_invisible_to_owners_and_tenants(world):
    survey = draft(world)
    with pytest.raises(NotFound):
        SurveyService.get_visible(actor=world.owner, prop=world.prop, survey_id=survey.pk)


def test_publication_requires_complete_questions(world):
    with pytest.raises(BusinessRuleViolation):
        SurveyService.publish(actor=world.manager, survey=draft(world, questions=[]))
    with pytest.raises(BusinessRuleViolation):
        SurveyService.publish(
            actor=world.manager, survey=draft(world, questions=[QuestionInput("Q", ["Only one"])])
        )


def test_published_survey_is_frozen(world):
    survey = SurveyService.publish(actor=world.manager, survey=draft(world))
    with pytest.raises(InvalidTransition):
        SurveyService.update_draft(actor=world.manager, survey=survey, changes={"title": "x"})


def test_one_participation_answering_everything(world):
    survey = SurveyService.publish(actor=world.manager, survey=draft(world))
    first_question = survey.questions.first()
    with pytest.raises(InvalidInput):
        ParticipationService.respond(
            actor=world.owner,
            survey=survey,
            answers={first_question.pk: first_question.options.first().pk},
        )
    response = ParticipationService.respond(
        actor=world.owner, survey=survey, answers=answers_for(survey)
    )
    assert response.user == world.owner
    with pytest.raises(BusinessRuleViolation):
        ParticipationService.respond(
            actor=world.owner, survey=survey, answers=answers_for(survey, pick=1)
        )


def test_option_must_belong_to_question(world):
    survey = SurveyService.publish(actor=world.manager, survey=draft(world))
    q1, q2 = survey.questions.all()
    with pytest.raises(InvalidInput):
        ParticipationService.respond(
            actor=world.owner,
            survey=survey,
            answers={q1.pk: q2.options.first().pk, q2.pk: q2.options.first().pk},
        )


def test_only_the_targeted_roles_answer(world):
    survey = SurveyService.publish(actor=world.manager, survey=draft(world))
    with pytest.raises(PermissionDenied):
        ParticipationService.respond(actor=world.tenant, survey=survey, answers=answers_for(survey))


def test_closing_date_stops_answers(world):
    survey = SurveyService.publish(
        actor=world.manager, survey=draft(world, closes_at=timezone.now() + dt.timedelta(hours=1))
    )
    survey.closes_at = timezone.now() - dt.timedelta(seconds=1)
    survey.save(update_fields=["closes_at"])
    with pytest.raises(InvalidTransition):
        ParticipationService.respond(actor=world.owner, survey=survey, answers=answers_for(survey))
    assert SurveyService.close_expired() == 1
    assert InboxNotification.objects.filter(
        notification_type="survey.closed", user=world.owner
    ).exists()
    assert SurveyService.close_expired() == 0  # idempotent


def test_results_are_for_managers_until_closed(world):
    survey = SurveyService.publish(actor=world.manager, survey=draft(world))
    ParticipationService.respond(actor=world.owner, survey=survey, answers=answers_for(survey))
    results = ParticipationService.results(actor=world.manager, survey=survey)
    assert results["participants"] == 1 and results["questions"][0]["options"][0]["votes"] == 1
    with pytest.raises(PermissionDenied):
        ParticipationService.results(actor=world.owner, survey=survey)
    survey = SurveyService.close(actor=world.manager, survey=survey)
    assert survey.status == SurveyStatus.CLOSED
    assert ParticipationService.results(actor=world.owner, survey=survey)["participants"] == 1
