"""Base views.

A client selects a syndicat and a property in three steps after login (see
`apps.common.enums.UIConfigStep`), and carries the result on every later call:
`X-Syndicat-Id`, `X-Property-Id`. The property never travels as a URL
parameter or in a body, so a client can never read or write in a property
other than the one it selected.

| Base view          | Requires                                                |
|---------------------|---------------------------------------------------------|
| `ApiMixin` + `APIView` | nothing (auth flows, `/me/`, notifications, admin console) |
| `UIConfigStepView`  | `X-UI-Config-Step` equal to the step the view declares  |
| `BaseAPIView`       | `X-Syndicat-Id`, `X-Property-Id`, `X-UI-Config-Step: dashboard` |

Every request once inside the dashboard carries all three: nothing is ever
guessed, and a client cannot act on a syndicat or a property it has not
selected.
"""

from __future__ import annotations

from typing import Any, ClassVar

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.enums import UIConfigStep
from apps.common.exceptions import InvalidInput
from apps.common.pagination import StandardPagination

SYNDICAT_HEADER = "X-Syndicat-Id"
PROPERTY_HEADER = "X-Property-Id"
STEP_HEADER = "X-UI-Config-Step"


class ApiMixin:
    """Helpers to validate input, read the selection headers and render output."""

    pagination_class = StandardPagination

    def parse(
        self, serializer_class: type[serializers.Serializer], data: Any = None, **kwargs
    ) -> dict:
        serializer = serializer_class(data=self.request.data if data is None else data, **kwargs)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def parse_query_params(self, serializer_class: type[serializers.Serializer]) -> dict:
        serializer = serializer_class(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def render(
        self, serializer_class, instance, *, status: int = 200, many: bool = False
    ) -> Response:
        data = serializer_class(instance, many=many, context=self.get_serializer_context()).data
        return Response(data, status=status)

    def render_page(self, serializer_class, queryset) -> Response:
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, self.request, view=self)
        data = serializer_class(page, many=True, context=self.get_serializer_context()).data
        return paginator.get_paginated_response(data)

    def get_serializer_context(self) -> dict:
        return {"request": self.request, "view": self}

    # -- selection headers, always readable, required only where a base view says so --
    def _header_id(self, header: str) -> int | None:
        raw = self.request.headers.get(header)
        if raw in (None, ""):
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            raise InvalidInput(f"{header} must be an integer.", field=header) from None

    @property
    def selected_syndicat_id(self) -> int | None:
        return self._header_id(SYNDICAT_HEADER)

    @property
    def selected_property_id(self) -> int | None:
        return self._header_id(PROPERTY_HEADER)

    @property
    def ui_config_step(self) -> str | None:
        raw = self.request.headers.get(STEP_HEADER)
        if raw in (None, ""):
            return None
        if raw not in UIConfigStep.values:
            raise InvalidInput(f"Unknown UI configuration step '{raw}'.", field=STEP_HEADER)
        return raw

    def require_selected_syndicat_id(self) -> int:
        syndicat_id = self.selected_syndicat_id
        if syndicat_id is None:
            raise InvalidInput(
                f"Select a syndicat first: this endpoint requires the {SYNDICAT_HEADER} header.",
                field=SYNDICAT_HEADER,
                code="selection_required",
            )
        return syndicat_id

    def require_selected_property_id(self) -> int:
        property_id = self.selected_property_id
        if property_id is None:
            raise InvalidInput(
                f"Select a property first: this endpoint requires the {PROPERTY_HEADER} header.",
                field=PROPERTY_HEADER,
                code="selection_required",
            )
        return property_id

    def require_ui_config_step(self, expected: str) -> None:
        if self.ui_config_step != expected:
            raise InvalidInput(
                f"This endpoint belongs to the '{expected}' step of the UI configuration.",
                field=STEP_HEADER,
                code="wrong_ui_config_step",
            )


class UIConfigStepView(ApiMixin, APIView):
    """One page of the configuration path (`syndicat` or `property`): it answers
    at its own step only, declared by the subclass as `step`."""

    step: ClassVar[str]

    def initial(self, request, *args, **kwargs) -> None:
        super().initial(request, *args, **kwargs)
        self.require_ui_config_step(self.step)


class BaseAPIView(ApiMixin, APIView):
    """Base of every dashboard endpoint.

    The client has finished configuring its session and carries the selection
    on every call: `X-Syndicat-Id`, `X-Property-Id`, and `X-UI-Config-Step:
    dashboard`. Nothing here is optional, so no dashboard endpoint can run on
    a guessed or partial selection.
    """

    def initial(self, request, *args, **kwargs) -> None:
        super().initial(request, *args, **kwargs)  # authentication first
        self.require_ui_config_step(UIConfigStep.DASHBOARD)
        self.require_selected_syndicat_id()
        self.require_selected_property_id()
