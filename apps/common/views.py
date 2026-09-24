"""Base views.

A client selects a syndicat and a property in three steps after login (see
`apps.common.enums.UIConfigStep`), and carries the result on every later call:
`X-Syndicat-Id`, `X-Property-Id`.

| Base view              | Requires                                                    |
|------------------------|-------------------------------------------------------------|
| `ApiMixin` + `APIView` | nothing (auth flows, `/me/`, notifications, admin console)   |
| `UIConfigStepView`     | `X-UI-Config-Step` equal to the step the view declares      |
| `BaseAPIView`          | `X-Syndicat-Id`, `X-Property-Id`, `X-UI-Config-Step: dashboard` |

`BaseAPIView` resolves the selection once, before the handler runs: the
property must exist, be visible to the account and belong to the selected
syndicat. The handler then works with `self.property` and hands it to the
services, which look records up *inside* that property only: a record of
another property answers 404, even to an account that manages both.
"""

from __future__ import annotations

from typing import Any, ClassVar

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.enums import UIConfigStep
from apps.common.exceptions import InvalidInput, NotFound
from apps.common.pagination import StandardPagination

SYNDICAT_HEADER = "X-Syndicat-Id"
PROPERTY_HEADER = "X-Property-Id"
STEP_HEADER = "X-UI-Config-Step"


class ApiMixin:
    """Validating input, reading the selection headers, rendering output."""

    pagination_class = StandardPagination

    # ------------------------------------------------------------ input / output
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

    # ------------------------------------------------------------ selection headers
    def _header_id(self, header: str) -> int | None:
        raw = self.request.headers.get(header)
        if raw in (None, ""):
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            raise InvalidInput(f"{header} must be an integer.", field=header) from None

    def _required_header_id(self, header: str, what: str) -> int:
        value = self._header_id(header)
        if value is None:
            raise InvalidInput(
                f"Select a {what} first: this endpoint requires the {header} header.",
                field=header,
                code="selection_required",
            )
        return value

    @property
    def selected_syndicat_id(self) -> int | None:
        return self._header_id(SYNDICAT_HEADER)

    @property
    def selected_property_id(self) -> int | None:
        """The raw header, for the few views outside the dashboard that read it
        (the account console). Dashboard views use `self.property` instead."""
        return self._header_id(PROPERTY_HEADER)

    def require_selected_syndicat_id(self) -> int:
        return self._required_header_id(SYNDICAT_HEADER, "syndicat")

    def require_selected_property_id(self) -> int:
        return self._required_header_id(PROPERTY_HEADER, "property")

    @property
    def ui_config_step(self) -> str | None:
        raw = self.request.headers.get(STEP_HEADER)
        if raw in (None, ""):
            return None
        if raw not in UIConfigStep.values:
            raise InvalidInput(f"Unknown UI configuration step '{raw}'.", field=STEP_HEADER)
        return raw

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
    """Base of every dashboard endpoint: `self.property` is the selected property."""

    def initial(self, request, *args, **kwargs) -> None:
        super().initial(request, *args, **kwargs)  # authentication first
        self.require_ui_config_step(UIConfigStep.DASHBOARD)
        syndicat_id = self.require_selected_syndicat_id()
        property_id = self.require_selected_property_id()
        # Local import: the shared kernel sits below the property referential.
        from apps.properties.services import PropertyService

        self.property = PropertyService.get_visible(
            actor=request.user, property_id=property_id, syndicat_id=syndicat_id
        )

    def selected_property(self, property_id: int):
        """The property named in the URL, which must be the selected one."""
        if property_id != self.property.pk:
            raise NotFound("Property not found.")
        return self.property
