from django.urls import path

from apps.store import views

urlpatterns = [
    path("store/products/", views.ProductListView.as_view(), name="product-list"),
    path(
        "store/products/<int:product_id>/",
        views.ProductDetailView.as_view(),
        name="product-detail",
    ),
    path(
        "store/products/<int:product_id>/images/",
        views.ProductImagesView.as_view(),
        name="product-images",
    ),
    path(
        "store/products/<int:product_id>/images/<int:attachment_id>/",
        views.ProductImageDetailView.as_view(),
        name="product-image-detail",
    ),
    path("store/orders/", views.OrderListView.as_view(), name="order-list"),
    path(
        "store/orders/<int:order_id>/",
        views.OrderDetailView.as_view(),
        name="order-detail",
    ),
    path(
        "store/orders/<int:order_id>/confirm/",
        views.OrderConfirmView.as_view(),
        name="order-confirm",
    ),
    path(
        "store/orders/<int:order_id>/deliver/",
        views.OrderDeliverView.as_view(),
        name="order-deliver",
    ),
    path(
        "store/orders/<int:order_id>/cancel/",
        views.OrderCancelView.as_view(),
        name="order-cancel",
    ),
]
