"""Actions this module writes in the audit journal."""

from enum import StrEnum


class SurveyAudit(StrEnum):
    CLOSED = "survey.closed"
    DELETED = "survey.deleted"
    DRAFT_UPDATED = "survey.draft_updated"
    DRAFTED = "survey.drafted"
    PUBLISHED = "survey.published"
