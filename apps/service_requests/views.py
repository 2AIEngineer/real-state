from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.accounts.services.accounts import AccountService
from apps.common.serializers import ActionReasonSerializer, UploadFilesSerializer
from apps.common.views import BaseAPIView
from apps.properties.services import PropertyService, UnitService
from apps.service_requests import serializers as s
from apps.service_requests.services import Feedback, ServiceRequestService


@extend_schema(tags=["Service requests"])
class ServiceRequestListView(BaseAPIView):
    @extend_schema(
        parameters=[s.ServiceRequestsQueryParamsSerializer],
        responses=s.ServiceRequestSerializer(many=True),
    )
    def get(self, request):
        query = self.parse_query_params(s.ServiceRequestsQueryParamsSerializer)
        return self.render_page(
            s.ServiceRequestSerializer,
            ServiceRequestService.list_visible(
                actor=request.user, property_id=self.selected_property_id, **query
            ),
        )

    @extend_schema(
        request=s.ServiceRequestCreateSerializer, responses={201: s.ServiceRequestSerializer}
    )
    def post(self, request):
        data = dict(self.parse(s.ServiceRequestCreateSerializer))
        prop = PropertyService.get_visible(
            actor=request.user,
            property_id=self.selected_property_id,
            syndicat_id=self.selected_syndicat_id,
        )
        unit_id = data.pop("unit_id")
        unit = UnitService.get_visible(actor=request.user, unit_id=unit_id) if unit_id else None
        sr = ServiceRequestService.submit(actor=request.user, prop=prop, unit=unit, **data)
        return self.render(s.ServiceRequestSerializer, sr, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Service requests"])
class ServiceRequestDetailView(BaseAPIView):
    @extend_schema(responses=s.ServiceRequestSerializer)
    def get(self, request, request_id: int):
        return self.render(
            s.ServiceRequestSerializer,
            ServiceRequestService.get_visible(actor=request.user, request_id=request_id),
        )

    @extend_schema(
        responses={204: None},
        description="Permanently deletes the request, its rounds and its conversation.",
    )
    def delete(self, request, request_id: int):
        sr = ServiceRequestService.get_visible(actor=request.user, request_id=request_id)
        ServiceRequestService.delete(actor=request.user, sr=sr)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Service requests"])
class ServiceRequestFilesView(BaseAPIView):
    @extend_schema(request=UploadFilesSerializer, responses={201: s.ServiceRequestSerializer})
    def post(self, request, request_id: int):
        sr = ServiceRequestService.get_visible(actor=request.user, request_id=request_id)
        data = self.parse(UploadFilesSerializer)
        ServiceRequestService.add_files(actor=request.user, sr=sr, files=data["files"])
        return self.render(s.ServiceRequestSerializer, sr, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Service requests"])
class ServiceRequestFileDetailView(BaseAPIView):
    @extend_schema(responses={204: None})
    def delete(self, request, request_id: int, attachment_id: int):
        sr = ServiceRequestService.get_visible(actor=request.user, request_id=request_id)
        ServiceRequestService.remove_file(actor=request.user, sr=sr, attachment_id=attachment_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Service requests"])
class AssignmentListView(BaseAPIView):
    pagination_class = None  # a plain list of rounds

    @extend_schema(responses=s.ServiceRequestAssignmentSerializer(many=True))
    def get(self, request, request_id: int):
        sr = ServiceRequestService.get_visible(actor=request.user, request_id=request_id)
        return self.render(
            s.ServiceRequestAssignmentSerializer,
            ServiceRequestService.assignments(actor=request.user, sr=sr),
            many=True,
        )

    @extend_schema(
        request=s.ServiceRequestAssignSerializer,
        responses={201: s.ServiceRequestAssignmentSerializer(many=True)},
    )
    def post(self, request, request_id: int):
        sr = ServiceRequestService.get_visible(actor=request.user, request_id=request_id)
        data = self.parse(s.ServiceRequestAssignSerializer)
        resolvers = AccountService.resolve_many(user_ids=data["resolver_ids"], field="resolver_ids")
        created = ServiceRequestService.assign(actor=request.user, sr=sr, resolvers=resolvers)
        return self.render(
            s.ServiceRequestAssignmentSerializer, created, many=True, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Service requests"])
class ResolveView(BaseAPIView):
    @extend_schema(
        request=s.ServiceRequestResolveSerializer, responses=s.ServiceRequestAssignmentSerializer
    )
    def post(self, request, request_id: int):
        sr = ServiceRequestService.get_visible(actor=request.user, request_id=request_id)
        data = self.parse(s.ServiceRequestResolveSerializer)
        return self.render(
            s.ServiceRequestAssignmentSerializer,
            ServiceRequestService.resolve(actor=request.user, sr=sr, **data),
        )


@extend_schema(tags=["Service requests"])
class FeedbackView(BaseAPIView):
    @extend_schema(request=s.ServiceRequestFeedbackSerializer, responses=s.ServiceRequestSerializer)
    def post(self, request, request_id: int):
        sr = ServiceRequestService.get_visible(actor=request.user, request_id=request_id)
        data = self.parse(s.ServiceRequestFeedbackSerializer)
        return self.render(
            s.ServiceRequestSerializer,
            ServiceRequestService.give_feedback(
                actor=request.user, sr=sr, feedback=Feedback(**data)
            ),
        )


@extend_schema(tags=["Service requests"])
class CloseView(BaseAPIView):
    @extend_schema(request=None, responses=s.ServiceRequestSerializer)
    def post(self, request, request_id: int):
        sr = ServiceRequestService.get_visible(actor=request.user, request_id=request_id)
        return self.render(
            s.ServiceRequestSerializer, ServiceRequestService.close(actor=request.user, sr=sr)
        )


@extend_schema(tags=["Service requests"])
class CancelView(BaseAPIView):
    @extend_schema(request=ActionReasonSerializer, responses=s.ServiceRequestSerializer)
    def post(self, request, request_id: int):
        sr = ServiceRequestService.get_visible(actor=request.user, request_id=request_id)
        data = self.parse(ActionReasonSerializer)
        return self.render(
            s.ServiceRequestSerializer,
            ServiceRequestService.cancel(actor=request.user, sr=sr, reason=data["reason"]),
        )
