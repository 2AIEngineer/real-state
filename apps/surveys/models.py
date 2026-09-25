from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q

from apps.accounts.enums import PropertyRole
from apps.common.models import TimeStampedModel


class SurveyStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Open for answers"
    CLOSED = "CLOSED", "Closed"


class Survey(TimeStampedModel):
    property = models.ForeignKey(
        "properties.Property", on_delete=models.CASCADE, related_name="surveys"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_roles = ArrayField(models.CharField(max_length=16, choices=PropertyRole.choices))
    status = models.CharField(
        max_length=10, choices=SurveyStatus.choices, default=SurveyStatus.DRAFT
    )
    closes_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(target_roles__len__gt=0), name="survey_has_target_roles"
            ),
            models.CheckConstraint(
                condition=Q(status=SurveyStatus.DRAFT) | Q(published_at__isnull=False),
                name="survey_published_has_timestamp",
            ),
        ]
        indexes = [models.Index(fields=["property", "status"])]

    def __str__(self) -> str:
        return self.title


class SurveyQuestion(models.Model):
    """Single-choice (radio) question."""

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["survey_id", "position", "id"]

    def __str__(self) -> str:
        return self.text[:60]


class SurveyOption(models.Model):
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=200)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["question_id", "position", "id"]

    def __str__(self) -> str:
        return self.text


class SurveyResponse(models.Model):
    """One user's participation in a survey (all answers submitted at once)."""

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="responses")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="survey_responses"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["survey", "user"], name="unique_survey_participation")
        ]


class SurveyAnswer(models.Model):
    response = models.ForeignKey(SurveyResponse, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, related_name="answers")
    selected_option = models.ForeignKey(
        SurveyOption, on_delete=models.CASCADE, related_name="answers"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["response", "question"], name="unique_answer_per_question"
            )
        ]
