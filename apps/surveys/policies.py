"""Who may do what with surveys.

Management writes, publishes, closes and deletes surveys and sees every
one of them, drafts included. The rest of the property sees the published
surveys addressed to one of their roles, answers them, and sees the
results once the survey is closed.
"""

from django.db.models import Q

from apps.accounts.enums import PropertyRole
from apps.accounts.services.authorization import AccessService
from apps.accounts.services.visibility import readable_property_records
from apps.properties.models import Property
from apps.surveys.models import Survey, SurveyStatus


class SurveyPolicy:
    @staticmethod
    def is_management(user, prop: Property) -> bool:
        return AccessService.manages_property(user, prop)

    @staticmethod
    def addressed_filter(user) -> Q:
        """Surveys addressed to one of the user's roles (drafts are filtered separately)."""
        return readable_property_records(user)

    @staticmethod
    def can_list(user, prop: Property) -> bool:
        return AccessService.is_staff_or_resident_of_property(user, prop)

    @staticmethod
    def can_view(user, survey: Survey) -> bool:
        if SurveyPolicy.is_management(user, survey.property):
            return True
        if survey.status == SurveyStatus.DRAFT:
            return False
        return (
            Survey.objects.filter(pk=survey.pk).filter(SurveyPolicy.addressed_filter(user)).exists()
        )

    @staticmethod
    def can_author(user, prop: Property) -> bool:
        """Create, edit, publish, close, attach files, delete."""
        return SurveyPolicy.is_management(user, prop)

    @staticmethod
    def can_respond(user, survey: Survey) -> bool:
        """Addressed to the user's role in a property they work in, or to the owners or tenants they are."""
        prop, targets = survey.property, set(survey.target_roles)
        if user.role in targets and AccessService.is_staff_of_property(user, prop):
            return True
        if PropertyRole.OWNER in targets and AccessService.is_owner_in_property(user, prop):
            return True
        return PropertyRole.TENANT in targets and AccessService.is_tenant_in_property(user, prop)

    @staticmethod
    def can_view_results(user, survey: Survey, *, is_closed: bool) -> bool:
        """Management anytime; the people it is addressed to once it is closed."""
        if SurveyPolicy.is_management(user, survey.property):
            return True
        return is_closed and SurveyPolicy.can_view(user, survey)
