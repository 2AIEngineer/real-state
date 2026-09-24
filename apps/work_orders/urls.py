from django.urls import path

from apps.work_orders import views

urlpatterns = [
    path("work-orders/", views.WorkOrderListView.as_view(), name="work-order-list"),
    path(
        "work-orders/<int:work_order_id>/",
        views.WorkOrderDetailView.as_view(),
        name="work-order-detail",
    ),
    path(
        "work-orders/<int:work_order_id>/transitions/",
        views.WorkOrderTransitionView.as_view(),
        name="work-order-transition",
    ),
    path(
        "work-orders/<int:work_order_id>/files/",
        views.WorkOrderFilesView.as_view(),
        name="work-order-files",
    ),
]
