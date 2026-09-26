from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import serializers as s
from apps.accounts.services.accounts import AccountService
from apps.accounts.services.passwords import PasswordService
from apps.accounts.services.providers import ProviderProfileService
from apps.accounts.services.registration import OwnedUnit, RentedUnit
from apps.accounts.services.status import AccountStatusService
from apps.accounts.views.mixins import AccountMixin
from apps.common.schema import property_header, syndicat_header
from apps.common.views import ApiMixin


@extend_schema(tags=["Users"])
class UserListView(ApiMixin, APIView):
    @extend_schema(
        parameters=[s.UserSearchQueryParamsSerializer, property_header()],
        responses=s.UserSerializer(many=True),
        description="Accounts the actor may see, narrowed to the selected property when one is.",
    )
    def get(self, request):
        query = self.parse_query_params(s.UserSearchQueryParamsSerializer)
        users = AccountService.search(
            actor=request.user,
            query=query.get("q"),
            property_id=self.selected_property_id,
            include_inactive=query["include_inactive"],
        )
        return self.render_page(s.UserSerializer, users)

    @extend_schema(
        request=s.AccountCreateSerializer,
        responses={201: s.UserSerializer},
        parameters=[syndicat_header(required=True), property_header()],
    )
    def post(self, request):
        # Accounts are created from the dashboard: the selected syndicat and property
        # say where the role is exercised, and the body says which units a standard
        # account holds.
        data = dict(self.parse(s.AccountCreateSerializer))
        building_ids = tuple(data.pop("building_ids"))
        ownerships = [OwnedUnit(**owned) for owned in data.pop("ownerships")]
        rented = data.pop("tenancy")
        user = AccountService.create_account(
            actor=request.user,
            syndicat_id=self.require_selected_syndicat_id(),
            property_id=self.selected_property_id,
            building_ids=building_ids,
            ownerships=ownerships,
            tenancy=RentedUnit(**rented) if rented else None,
            **data,
        )
        return self.render(s.UserSerializer, user, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Users"])
class UserDetailView(AccountMixin, ApiMixin, APIView):
    """One account: its profile, and the closing of the account."""

    @extend_schema(responses=s.UserSerializer)
    def get(self, request, user_id: str):
        return self.render(s.UserSerializer, self.account(user_id))

    @extend_schema(request=s.UserProfileUpdateSerializer, responses=s.UserSerializer)
    def patch(self, request, user_id: str):
        user = self.account(user_id)
        data = self.parse(s.UserProfileUpdateSerializer)
        return self.render(
            s.UserSerializer,
            AccountService.update_profile(actor=request.user, user=user, changes=data),
        )

    @extend_schema(
        responses={204: None},
        description="Deletes the account for good, with everything that is theirs. "
        "Deactivating is the alternative that keeps it.",
    )
    def delete(self, request, user_id: str):
        AccountStatusService.delete(actor=request.user, user=self.account(user_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Users"])
class UserEmailView(AccountMixin, ApiMixin, APIView):
    """The login address of an account."""

    @extend_schema(
        request=s.EmailChangeSerializer,
        responses=s.UserSerializer,
        description="Changes the login address. Holders confirm with their current password.",
    )
    def post(self, request, user_id: str):
        user = self.account(user_id)
        data = self.parse(s.EmailChangeSerializer)
        return self.render(
            s.UserSerializer,
            AccountService.change_email(
                actor=request.user,
                user=user,
                new_email=data["email"],
                current_password=data.get("current_password"),
            ),
        )


@extend_schema(tags=["Users"])
class UserPasswordView(AccountMixin, ApiMixin, APIView):
    """The password of an account."""

    @extend_schema(
        request=s.PasswordChangeSerializer,
        responses={204: None},
        description="Only the holder changes their own password; someone else sends a new invitation.",
    )
    def post(self, request, user_id: str):
        user = self.account(user_id)
        data = self.parse(s.PasswordChangeSerializer)
        PasswordService.change_password(
            actor=request.user,
            user=user,
            current_password=data["current_password"],
            new_password=data["new_password"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Users"])
class UserInvitationView(AccountMixin, ApiMixin, APIView):
    """Sends the invitation again, to an account that has not set its password."""

    @extend_schema(request=None, responses={202: None})
    def post(self, request, user_id: str):
        AccountService.resend_invitation(actor=request.user, user=self.account(user_id))
        return Response(status=status.HTTP_202_ACCEPTED)


@extend_schema(tags=["Users"])
class UserDeactivateView(AccountMixin, ApiMixin, APIView):
    """Deactivates an account: it keeps its history but cannot sign in."""

    @extend_schema(request=s.AccountDeactivationSerializer, responses=s.UserSerializer)
    def post(self, request, user_id: str):
        user = self.account(user_id)
        data = self.parse(s.AccountDeactivationSerializer)
        return self.render(
            s.UserSerializer,
            AccountStatusService.deactivate(
                actor=request.user, user=user, reason=data["reason"]
            ),
        )


@extend_schema(tags=["Users"])
class UserReactivateView(AccountMixin, ApiMixin, APIView):
    """Puts a deactivated account back in service."""

    @extend_schema(request=None, responses=s.UserSerializer)
    def post(self, request, user_id: str):
        return self.render(
            s.UserSerializer,
            AccountStatusService.reactivate(
                actor=request.user, user=self.account(user_id)
            ),
        )


@extend_schema(tags=["Users"])
class ProviderProfileView(AccountMixin, ApiMixin, APIView):
    """The complementary profile of a service provider account."""

    @extend_schema(responses=s.ProviderProfileSerializer)
    def get(self, request, user_id: str):
        return self.render(
            s.ProviderProfileSerializer,
            ProviderProfileService.get(actor=request.user, user=self.account(user_id)),
        )

    @extend_schema(
        request=s.ProviderProfileUpdateSerializer, responses=s.ProviderProfileSerializer
    )
    def patch(self, request, user_id: str):
        user = self.account(user_id)
        data = self.parse(s.ProviderProfileUpdateSerializer)
        return self.render(
            s.ProviderProfileSerializer,
            ProviderProfileService.update(actor=request.user, user=user, changes=data),
        )
