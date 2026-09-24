"""Serializers: the shape of inputs and outputs, one module per area.

Views import the package (`from apps.X import serializers as s`) and use `s.Name`.
"""

from apps.accounts.serializers.assignments import (  # noqa: F401
    AssignmentListQueryParamsSerializer,
    AssignmentSerializer,
    BuildingAssignmentInputSerializer,
    RoleChangeSerializer,
    UserBuildingSerializer,
    UserPropertySerializer,
    UserSyndicatSerializer,
)
from apps.accounts.serializers.auth import (  # noqa: F401
    LoginSerializer,
    LogoutSerializer,
    PasswordResetSerializer,
    PasswordSetSerializer,
)
from apps.accounts.serializers.session import (  # noqa: F401
    SessionAssetsSerializer,
    SessionContextSerializer,
    SessionCredentialsSerializer,
    SessionFeaturesSerializer,
    SessionOwnershipSerializer,
    SessionPropertySerializer,
    SessionRoleSerializer,
    SessionSelectionSerializer,
    SessionTenancySerializer,
    SessionUIConfigSerializer,
    SessionUserSerializer,
    SessionUserStatusSerializer,
)
from apps.accounts.serializers.users import (  # noqa: F401
    AccountCreateSerializer,
    AccountDeactivationSerializer,
    AccountOwnershipSerializer,
    AccountTenancySerializer,
    EmailChangeSerializer,
    PasswordChangeSerializer,
    ProviderProfileSerializer,
    ProviderProfileUpdateSerializer,
    UserProfileUpdateSerializer,
    UserSearchQueryParamsSerializer,
    UserSerializer,
)
