from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.accounts.enums import PropertyRole
from apps.common.attachments.rules import EntityType
from apps.common.attachments.serializers import AttachmentsField
from apps.surveys.models import Survey, SurveyOption, SurveyQuestion, SurveyStatus


class SurveyOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyOption
        fields = ["id", "text", "position"]
        read_only_fields = fields


class SurveyQuestionSerializer(serializers.ModelSerializer):
    options = SurveyOptionSerializer(many=True, read_only=True)

    class Meta:
        model = SurveyQuestion
        fields = ["id", "text", "position", "options"]
        read_only_fields = fields


class SurveySerializer(serializers.ModelSerializer):
    questions = SurveyQuestionSerializer(many=True, read_only=True)
    files = AttachmentsField(EntityType.SURVEY)
    has_answered = serializers.SerializerMethodField()

    class Meta:
        model = Survey
        fields = [
            "id",
            "property",
            "title",
            "description",
            "target_roles",
            "status",
            "closes_at",
            "published_at",
            "closed_at",
            "questions",
            "files",
            "has_answered",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_has_answered(self, obj) -> bool | None:
        answered = self.context.get("answered_survey_ids")
        return None if answered is None else obj.pk in answered


class SurveyQuestionInputSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=1000)
    options = serializers.ListField(
        child=serializers.CharField(max_length=200), allow_empty=False, max_length=20
    )


class SurveyCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    target_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=PropertyRole.choices), allow_empty=False
    )
    closes_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
    questions = SurveyQuestionInputSerializer(many=True, allow_empty=True, max_length=100)


@extend_schema_serializer(component_name="Survey")
class SurveyUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    target_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=PropertyRole.choices),
        allow_empty=False,
        required=False,
    )
    closes_at = serializers.DateTimeField(required=False, allow_null=True)
    questions = SurveyQuestionInputSerializer(many=True, required=False, max_length=100)


class SurveysQueryParamsSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SurveyStatus.choices, required=False)


class SurveyAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(min_value=1)
    option_id = serializers.IntegerField(min_value=1)


class SurveyResponseSerializer(serializers.Serializer):
    answers = SurveyAnswerSerializer(many=True, allow_empty=False)

    def validate_answers(self, value):
        if len({a["question_id"] for a in value}) != len(value):
            raise serializers.ValidationError("A question is answered twice.")
        return value


class SurveyParticipationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    submitted_at = serializers.DateTimeField()


class SurveyOptionResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    text = serializers.CharField()
    votes = serializers.IntegerField()


class SurveyQuestionResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    text = serializers.CharField()
    options = SurveyOptionResultSerializer(many=True)


class SurveyResultsSerializer(serializers.Serializer):
    survey_id = serializers.IntegerField()
    participants = serializers.IntegerField()
    recipients = serializers.IntegerField(
        help_text="People the survey was addressed to when published."
    )
    questions = SurveyQuestionResultSerializer(many=True)
