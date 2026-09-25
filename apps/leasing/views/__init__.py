"""HTTP endpoints, one module per resource. `urls.py` reads them from here."""

from apps.leasing.views.inspections import (  # noqa: F401
    LeaseComponentStateDetailView,
    LeaseComponentStateFilesView,
    LeaseComponentStateListView,
)
from apps.leasing.views.leases import (  # noqa: F401
    LeaseCancelView,
    LeaseDetailView,
    LeaseExpireDueView,
    LeaseListView,
    LeaseTerminateView,
)
from apps.leasing.views.members import (  # noqa: F401
    LeaseMemberDepartureView,
    LeaseMemberDetailView,
    LeaseMemberListView,
    LeaseMemberProofOfAddressView,
    LeaseMemberProofOfIdentityView,
)
