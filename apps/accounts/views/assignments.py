from drf_spectacular.utils import extend_schema
from rest_framework import status

from apps.accounts import serializers as s
from apps.accounts.services.accounts import AccountService
from apps.accounts.services.assignments import (
    BuildingAssignmentService,
    PropertyAssignmentService,
    SyndicatAssignmentService,
    assign_to_buildings_of_selected_property,
    assign_to_selected_property,
    assign_to_selected_syndicat,
)
from apps.accounts.views.mixins import AccountMixin
from apps.common.schema import property_header
from apps.common.views import BaseAPIView


@extend_schema(tags=["Roles & assignments"])
class UserRoleView(AccountMixin, BaseAPIView):
    """The role is granted where the actor works: the selected syndicat for a
    syndic, the selected property for the other roles."""

    @extend_schema(
        request=s.RoleChangeSerializer,
        responses=s.UserSerializer,
        parameters=[property_header()],
    )
    def post(self, request, user_id: str):
        user = self.account(user_id)
        data = self.parse(s.RoleChangeSerializer)
        user = AccountService.change_role(
            actor=request.user,
            user=user,
            role=data["role"],
            syndicat_id=self.require_selected_syndicat_id(),
            property_id=self.selected_property_id,
            building_ids=tuple(data["building_ids"]),
        )
        return self.render(s.UserSerializer, user)


@extend_schema(tags=["Roles & assignments"])
class UserSyndicatAssignmentsView(AccountMixin, BaseAPIView):
    """The syndicats a syndic account runs."""

    pagination_class = None  # a plain list of assignments

    @extend_schema(
        parameters=[s.AssignmentListQueryParamsSerializer],
        responses=s.UserSyndicatSerializer(many=True),
    )
    def get(self, request, user_id: str):
        query = self.parse_query_params(s.AssignmentListQueryParamsSerializer)
        rows = SyndicatAssignmentService.list_for_user(
            actor=request.user,
            user=self.account(user_id),
            include_revoked=query["include_revoked"],
        )
        return self.render(s.UserSyndicatSerializer, rows, many=True)

    @extend_schema(
        request=None,
        responses={201: s.UserSyndicatSerializer(many=True)},
        description="Assigns a syndic account to the selected syndicat.",
    )
    def post(self, request, user_id: str):
        created = assign_to_selected_syndicat(
            actor=request.user,
            user=self.account(user_id),
            syndicat_id=self.require_selected_syndicat_id(),
        )
        return self.render(
            s.UserSyndicatSerializer, created, many=True, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Roles & assignments"])
class UserPropertyAssignmentsView(AccountMixin, BaseAPIView):
    """The properties a manager or a maintenance account works on."""

    pagination_class = None

    @extend_schema(
        parameters=[s.AssignmentListQueryParamsSerializer],
        responses=s.UserPropertySerializer(many=True),
    )
    def get(self, request, user_id: str):
        query = self.parse_query_params(s.AssignmentListQueryParamsSerializer)
        rows = PropertyAssignmentService.list_for_user(
            actor=request.user,
            user=self.account(user_id),
            include_revoked=query["include_revoked"],
        )
        return self.render(s.UserPropertySerializer, rows, many=True)

    @extend_schema(
        request=None,
        responses={201: s.UserPropertySerializer(many=True)},
        parameters=[property_header()],
        description="Assigns a manager or a maintenance account to the selected property.",
    )
    def post(self, request, user_id: str):
        created = assign_to_selected_property(
            actor=request.user,
            user=self.account(user_id),
            syndicat_id=self.require_selected_syndicat_id(),
            property_id=self.selected_property_id,
        )
        return self.render(
            s.UserPropertySerializer, created, many=True, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Roles & assignments"])
class UserBuildingAssignmentsView(AccountMixin, BaseAPIView):
    """The buildings a security or cleaning account works in."""

    pagination_class = None

    @extend_schema(
        parameters=[s.AssignmentListQueryParamsSerializer],
        responses=s.UserBuildingSerializer(many=True),
    )
    def get(self, request, user_id: str):
        query = self.parse_query_params(s.AssignmentListQueryParamsSerializer)
        rows = BuildingAssignmentService.list_for_user(
            actor=request.user,
            user=self.account(user_id),
            include_revoked=query["include_revoked"],
        )
        return self.render(s.UserBuildingSerializer, rows, many=True)

    @extend_schema(
        request=s.BuildingAssignmentInputSerializer,
        responses={201: s.UserBuildingSerializer(many=True)},
        parameters=[property_header()],
        description="Assigns a security or cleaning account to buildings of the selected property.",
    )
    def post(self, request, user_id: str):
        data = self.parse(s.BuildingAssignmentInputSerializer)
        created = assign_to_buildings_of_selected_property(
            actor=request.user,
            user=self.account(user_id),
            syndicat_id=self.require_selected_syndicat_id(),
            property_id=self.selected_property_id,
            building_ids=tuple(data["building_ids"]),
        )
        return self.render(
            s.UserBuildingSerializer, created, many=True, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Roles & assignments"])
class SyndicatAssignmentRevokeView(BaseAPIView):
    @extend_schema(request=None, responses=s.UserSyndicatSerializer)
    def post(self, request, assignment_id: int):
        row = SyndicatAssignmentService.revoke(
            actor=request.user, assignment_id=assignment_id
        )
        return self.render(s.UserSyndicatSerializer, row)


@extend_schema(tags=["Roles & assignments"])
class PropertyAssignmentRevokeView(BaseAPIView):
    @extend_schema(request=None, responses=s.UserPropertySerializer)
    def post(self, request, assignment_id: int):
        row = PropertyAssignmentService.revoke(
            actor=request.user, assignment_id=assignment_id
        )
        return self.render(s.UserPropertySerializer, row)


@extend_schema(tags=["Roles & assignments"])
class BuildingAssignmentRevokeView(BaseAPIView):
    @extend_schema(request=None, responses=s.UserBuildingSerializer)
    def post(self, request, assignment_id: int):
        row = BuildingAssignmentService.revoke(
            actor=request.user, assignment_id=assignment_id
        )
        return self.render(s.UserBuildingSerializer, row)
