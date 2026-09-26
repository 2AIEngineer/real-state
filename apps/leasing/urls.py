from django.urls import path

from apps.leasing import views

urlpatterns = [
    path("leases/", views.LeaseListView.as_view(), name="lease-list"),
    path(
        "leases/expire-due/",
        views.LeaseExpireDueView.as_view(),
        name="lease-expire-due",
    ),
    path(
        "leases/<int:lease_id>/", views.LeaseDetailView.as_view(), name="lease-detail"
    ),
    path(
        "leases/<int:lease_id>/terminate/",
        views.LeaseTerminateView.as_view(),
        name="lease-terminate",
    ),
    path(
        "leases/<int:lease_id>/cancel/",
        views.LeaseCancelView.as_view(),
        name="lease-cancel",
    ),
    path(
        "leases/<int:lease_id>/members/",
        views.LeaseMemberListView.as_view(),
        name="lease-member-list",
    ),
    path(
        "leases/<int:lease_id>/lease-component-states/",
        views.LeaseComponentStateListView.as_view(),
        name="lease-component-state-list",
    ),
    path(
        "lease-members/<int:member_id>/",
        views.LeaseMemberDetailView.as_view(),
        name="lease-member-detail",
    ),
    path(
        "lease-members/<int:member_id>/departure/",
        views.LeaseMemberDepartureView.as_view(),
        name="lease-member-departure",
    ),
    path(
        "lease-members/<int:member_id>/proof-of-identity/",
        views.LeaseMemberProofOfIdentityView.as_view(),
        name="lease-member-proof-of-identity",
    ),
    path(
        "lease-members/<int:member_id>/proof-of-address/",
        views.LeaseMemberProofOfAddressView.as_view(),
        name="lease-member-proof-of-address",
    ),
    path(
        "leases/<int:lease_id>/lease-component-states/<int:lease_component_state_id>/",
        views.LeaseComponentStateDetailView.as_view(),
        name="lease-component-state-detail",
    ),
    path(
        "leases/<int:lease_id>/lease-component-states/<int:lease_component_state_id>/files/",
        views.LeaseComponentStateFilesView.as_view(),
        name="lease-component-state-files",
    ),
]
