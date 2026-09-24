from django.urls import path, register_converter

from apps.accounts.views import assignments, auth, users


class AccountRefConverter:
    """How a request names an account: its id, or `me` for the signed-in one.

    The signed-in account is a user like any other, so it uses the same
    endpoints; `me` only spares the client from knowing its own id.
    """

    regex = "(?:me|[0-9]+)"

    def to_python(self, value: str) -> str:
        return value

    def to_url(self, value) -> str:
        return str(value)


register_converter(AccountRefConverter, "account")

urlpatterns = [
    path("auth/token/", auth.LoginView.as_view(), name="auth-token"),
    path("auth/token/refresh/", auth.RefreshView.as_view(), name="auth-token-refresh"),
    path(
        "auth/password/reset/", auth.PasswordResetRequestView.as_view(), name="auth-password-reset"
    ),
    path("auth/password/set/", auth.PasswordSetView.as_view(), name="auth-password-set"),
    path("users/", users.UserListView.as_view(), name="user-list"),
    path("users/<account:user_id>/", users.UserDetailView.as_view(), name="user-detail"),
    path("users/<account:user_id>/email/", users.UserEmailView.as_view(), name="user-email"),
    path(
        "users/<account:user_id>/password/", users.UserPasswordView.as_view(), name="user-password"
    ),
    path(
        "users/<account:user_id>/invitation/",
        users.UserInvitationView.as_view(),
        name="user-invitation",
    ),
    path(
        "users/<account:user_id>/deactivate/",
        users.UserDeactivateView.as_view(),
        name="user-deactivate",
    ),
    path(
        "users/<account:user_id>/reactivate/",
        users.UserReactivateView.as_view(),
        name="user-reactivate",
    ),
    path(
        "users/<account:user_id>/provider-profile/",
        users.ProviderProfileView.as_view(),
        name="user-provider-profile",
    ),
    # Roles, and one endpoint per assignment table
    path("users/<account:user_id>/role/", assignments.UserRoleView.as_view(), name="user-role"),
    path(
        "users/<account:user_id>/syndicat-assignments/",
        assignments.UserSyndicatAssignmentsView.as_view(),
        name="user-syndicat-assignments",
    ),
    path(
        "users/<account:user_id>/property-assignments/",
        assignments.UserPropertyAssignmentsView.as_view(),
        name="user-property-assignments",
    ),
    path(
        "users/<account:user_id>/building-assignments/",
        assignments.UserBuildingAssignmentsView.as_view(),
        name="user-building-assignments",
    ),
    path(
        "syndicat-assignments/<int:assignment_id>/revoke/",
        assignments.SyndicatAssignmentRevokeView.as_view(),
        name="syndicat-assignment-revoke",
    ),
    path(
        "property-assignments/<int:assignment_id>/revoke/",
        assignments.PropertyAssignmentRevokeView.as_view(),
        name="property-assignment-revoke",
    ),
    path(
        "building-assignments/<int:assignment_id>/revoke/",
        assignments.BuildingAssignmentRevokeView.as_view(),
        name="building-assignment-revoke",
    ),
]
