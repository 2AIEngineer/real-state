from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.common.serializers import BulkActionResultSerializer, UploadFilesSerializer
from apps.common.views import BaseAPIView
from apps.surveys import serializers as s
from apps.surveys.services import ParticipationService, QuestionInput, SurveyService


def _questions(raw) -> list[QuestionInput] | None:
    return (
        None if raw is None else [QuestionInput(text=q["text"], options=q["options"]) for q in raw]
    )


class _AnsweredSurveys:
    """Tells the serializer which surveys the reader already answered."""

    def get_serializer_context(self) -> dict:
        context = super().get_serializer_context()
        context["answered_survey_ids"] = ParticipationService.answered_ids(user=self.request.user)
        return context


class _SurveyView(_AnsweredSurveys, BaseAPIView):
    pass


@extend_schema(tags=["Surveys"])
class SurveyListView(_AnsweredSurveys, BaseAPIView):
    @extend_schema(
        parameters=[s.SurveysQueryParamsSerializer], responses=s.SurveySerializer(many=True)
    )
    def get(self, request):
        query = self.parse_query_params(s.SurveysQueryParamsSerializer)
        return self.render_page(
            s.SurveySerializer,
            SurveyService.list_visible(
                actor=request.user, prop=self.property, status=query.get("status")
            ),
        )

    @extend_schema(request=s.SurveyCreateSerializer, responses={201: s.SurveySerializer})
    def post(self, request):
        data = dict(self.parse(s.SurveyCreateSerializer))
        questions = _questions(data.pop("questions"))
        survey = SurveyService.create_draft(
            actor=request.user, prop=self.property, questions=questions, **data
        )
        return self.render(
            s.SurveySerializer,
            SurveyService.get_visible(actor=request.user, prop=self.property, survey_id=survey.pk),
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Surveys"])
class SurveyDetailView(_SurveyView):
    @extend_schema(responses=s.SurveySerializer)
    def get(self, request, survey_id: int):
        return self.render(
            s.SurveySerializer,
            SurveyService.get_visible(actor=request.user, prop=self.property, survey_id=survey_id),
        )

    @extend_schema(request=s.SurveyUpdateSerializer, responses=s.SurveySerializer)
    def patch(self, request, survey_id: int):
        survey = SurveyService.get_visible(
            actor=request.user, prop=self.property, survey_id=survey_id
        )
        data = dict(self.parse(s.SurveyUpdateSerializer))
        questions = _questions(data.pop("questions", None))
        SurveyService.update_draft(
            actor=request.user, survey=survey, changes=data, questions=questions
        )
        return self.render(
            s.SurveySerializer,
            SurveyService.get_visible(actor=request.user, prop=self.property, survey_id=survey_id),
        )

    @extend_schema(responses={204: None}, description="Deletes a survey nobody answered.")
    def delete(self, request, survey_id: int):
        survey = SurveyService.get_visible(
            actor=request.user, prop=self.property, survey_id=survey_id
        )
        SurveyService.delete(actor=request.user, survey=survey)
        return Response(status=status.HTTP_204_NO_CONTENT)


class _SurveyTransitionView(_SurveyView):
    transition = ""

    @extend_schema(tags=["Surveys"], request=None, responses=s.SurveySerializer)
    def post(self, request, survey_id: int):
        survey = SurveyService.get_visible(
            actor=request.user, prop=self.property, survey_id=survey_id
        )
        getattr(SurveyService, self.transition)(actor=request.user, survey=survey)
        return self.render(
            s.SurveySerializer,
            SurveyService.get_visible(actor=request.user, prop=self.property, survey_id=survey_id),
        )


class SurveyPublishView(_SurveyTransitionView):
    transition = "publish"


class SurveyCloseView(_SurveyTransitionView):
    transition = "close"


@extend_schema(tags=["Surveys"])
class SurveyResponseView(BaseAPIView):
    @extend_schema(
        request=s.SurveyResponseSerializer, responses={201: s.SurveyParticipationSerializer}
    )
    def post(self, request, survey_id: int):
        survey = SurveyService.get_visible(
            actor=request.user, prop=self.property, survey_id=survey_id
        )
        data = self.parse(s.SurveyResponseSerializer)
        answers = {a["question_id"]: a["option_id"] for a in data["answers"]}
        response = ParticipationService.respond(actor=request.user, survey=survey, answers=answers)
        return self.render(
            s.SurveyParticipationSerializer, response, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Surveys"])
class SurveyResultsView(BaseAPIView):
    @extend_schema(responses=s.SurveyResultsSerializer)
    def get(self, request, survey_id: int):
        survey = SurveyService.get_visible(
            actor=request.user, prop=self.property, survey_id=survey_id
        )
        return self.render(
            s.SurveyResultsSerializer,
            ParticipationService.results(actor=request.user, survey=survey),
        )


@extend_schema(tags=["Surveys"])
class SurveyFilesView(_SurveyView):
    @extend_schema(request=UploadFilesSerializer, responses={201: s.SurveySerializer})
    def post(self, request, survey_id: int):
        survey = SurveyService.get_visible(
            actor=request.user, prop=self.property, survey_id=survey_id
        )
        data = self.parse(UploadFilesSerializer)
        SurveyService.add_files(actor=request.user, survey=survey, files=data["files"])
        return self.render(s.SurveySerializer, survey, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Surveys"])
class SurveyCloseExpiredView(BaseAPIView):
    @extend_schema(
        request=None,
        responses=BulkActionResultSerializer,
        description="Bulk action (admin, syndic, manager): closes every published survey of the selected property past its closing date.",
    )
    def post(self, request):
        count = SurveyService.close_expired_in(actor=request.user, prop=self.property)
        return self.render(BulkActionResultSerializer, {"count": count})
