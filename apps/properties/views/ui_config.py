"""The UI configuration path followed after every login.

The client announces where it stands in `X-UI-Config-Step`, and the two pages
of the path only answer at their own step: pick a syndicat, then pick one of
its properties. `PropertyStatisticsView` lives here too: it is read by the
dashboard, right after the property is selected.
"""

from drf_spectacular.utils import extend_schema

from apps.common.enums import UIConfigStep
from apps.common.schema import syndicat_header, ui_config_step_header
from apps.common.views import BaseAPIView, UIConfigStepView
from apps.properties import serializers as s
from apps.properties.services import (
    PropertyService,
    PropertyStatistics,
    SyndicatService,
)


@extend_schema(tags=["UI configuration"])
class UIConfigSyndicatsView(UIConfigStepView):
    """First configuration page: the syndicats the account may open.

    Resolved from assignments, so a syndicat without any property yet is listed.
    """

    step = UIConfigStep.SYNDICAT
    pagination_class = None  # the whole list: an account reaches few syndicats

    @extend_schema(
        parameters=[s.UIConfigSearchQueryParamsSerializer, ui_config_step_header(step)],
        responses=s.UIConfigSyndicatSerializer(many=True),
    )
    def get(self, request):
        query = self.parse_query_params(s.UIConfigSearchQueryParamsSerializer)
        syndicats = SyndicatService.list_reachable(actor=request.user, **query)
        return self.render(s.UIConfigSyndicatSerializer, syndicats, many=True)


@extend_schema(tags=["UI configuration"])
class UIConfigPropertiesView(UIConfigStepView):
    """Second configuration page: the properties of the syndicat just chosen,
    which the client carries in `X-Syndicat-Id`."""

    step = UIConfigStep.PROPERTY
    pagination_class = None  # the whole list: an account reaches few properties

    @extend_schema(
        parameters=[
            s.UIConfigSearchQueryParamsSerializer,
            ui_config_step_header(step),
            syndicat_header(required=True),
        ],
        responses=s.UIConfigPropertySerializer(many=True),
    )
    def get(self, request):
        query = self.parse_query_params(s.UIConfigSearchQueryParamsSerializer)
        syndicat = SyndicatService.get_reachable(
            actor=request.user, syndicat_id=self.require_selected_syndicat_id()
        )
        properties = PropertyService.list_reachable_in(
            actor=request.user, syndicat=syndicat, **query
        )
        return self.render(s.UIConfigPropertySerializer, properties, many=True)


@extend_schema(tags=["Properties"])
class PropertyStatisticsView(BaseAPIView):
    @extend_schema(responses=s.PropertyStatisticsSerializer)
    def get(self, request, property_id: int):
        statistics = PropertyStatistics.of(
            actor=request.user, prop=self.selected_property(property_id)
        )
        return self.render(s.PropertyStatisticsSerializer, statistics)
