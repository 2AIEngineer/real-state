from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts import serializers as s
from apps.accounts.services.passwords import PasswordService
from apps.accounts.services.session import SessionService
from apps.accounts.services.tokens import TokenService
from apps.accounts.throttles import AuthThrottleMixin, LoginThrottleMixin
from apps.common.views import ApiMixin


@extend_schema(tags=["Auth"])
class LoginView(LoginThrottleMixin, TokenObtainPairView):
    """Logs in and configures the session: the response is the `SessionContext`."""

    serializer_class = s.LoginSerializer

    @extend_schema(responses=s.SessionContextSerializer)
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc
        tokens = serializer.validated_data
        session = SessionService.configure(
            user=serializer.user,
            access_token=tokens["access"],
            refresh_token=tokens["refresh"],
        )
        return Response(s.SessionContextSerializer(session).data)


@extend_schema(tags=["Auth"])
class RefreshView(AuthThrottleMixin, TokenRefreshView):
    pass


@extend_schema(tags=["Auth"])
class LogoutView(AuthThrottleMixin, ApiMixin, APIView):
    """Ends the session: the refresh token can no longer be used.

    Open to an expired access token: signing out must always work.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(request=s.LogoutSerializer, responses={204: None})
    def post(self, request):
        data = self.parse(s.LogoutSerializer)
        TokenService.sign_out(refresh_token=data["refresh"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Auth"])
class PasswordResetRequestView(AuthThrottleMixin, ApiMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        request=s.PasswordResetSerializer,
        responses={202: OpenApiResponse(description="Accepted")},
    )
    def post(self, request):
        data = self.parse(s.PasswordResetSerializer)
        PasswordService.request_reset(email=data["email"])
        return Response(status=status.HTTP_202_ACCEPTED)


@extend_schema(tags=["Auth"])
class PasswordSetView(AuthThrottleMixin, ApiMixin, APIView):
    """Completes an invitation or a reset (uid + token from the e-mail link)."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(request=s.PasswordSetSerializer, responses={204: None})
    def post(self, request):
        data = self.parse(s.PasswordSetSerializer)
        PasswordService.set_password_with_token(
            uid=data["uid"], token=data["token"], password=data["password"]
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
