"""OpenAPI generation: the selection headers of each endpoint and the shape of attached files."""

import inspect

from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

from apps.common.serializers.attachments import AttachmentSerializer
from apps.common.views import (
    PROPERTY_HEADER,
    STEP_HEADER,
    SYNDICAT_HEADER,
    ApiMixin,
    BaseAPIView,
    UIConfigStepView,
)


def _header(name: str, description: str, *, required: bool, **extra) -> OpenApiParameter:
    return OpenApiParameter(
        name,
        extra.pop("type", OpenApiTypes.INT),
        OpenApiParameter.HEADER,
        required=required,
        description=description,
        **extra,
    )


def syndicat_header(*, required: bool) -> OpenApiParameter:
    return _header(SYNDICAT_HEADER, "Selected syndicat.", required=required)


def property_header(*, required: bool = False) -> OpenApiParameter:
    return _header(PROPERTY_HEADER, "Selected property.", required=required)


def ui_config_step_header(step: str) -> OpenApiParameter:
    return _header(
        STEP_HEADER,
        f"Step of the UI configuration: this endpoint answers at `{step}` only.",
        required=True,
        type=OpenApiTypes.STR,
        enum=[step],
    )


_BASE_VIEWS = (ApiMixin, UIConfigStepView, BaseAPIView)


class UIConfigAwareAutoSchema(AutoSchema):
    def get_description(self):
        """Never describe an endpoint with the docstring of a base view class."""
        description = super().get_description()
        inherited = {inspect.cleandoc(cls.__doc__ or "") for cls in _BASE_VIEWS}
        return "" if inspect.cleandoc(description or "") in inherited else description

    def get_override_parameters(self):
        parameters = super().get_override_parameters()
        if isinstance(self.view, BaseAPIView):
            parameters = [
                *parameters,
                syndicat_header(required=True),
                property_header(required=True),
            ]
        return parameters


class AttachmentsFieldExtension(OpenApiSerializerFieldExtension):
    """OpenAPI description of `AttachmentsField`."""

    target_class = "apps.common.serializers.attachments.AttachmentsField"

    def map_serializer_field(self, auto_schema, direction):
        reference = auto_schema.resolve_serializer(AttachmentSerializer, direction).ref
        if self.target.single:
            return {"allOf": [reference], "nullable": True, "readOnly": True}
        return {"type": "array", "items": reference, "readOnly": True}
