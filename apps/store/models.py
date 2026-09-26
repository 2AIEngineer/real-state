from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class Product(TimeStampedModel):
    property = models.ForeignKey(
        "properties.Property", on_delete=models.CASCADE, related_name="products"
    )
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=80, blank=True)
    sku = models.CharField(max_length=64, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gte=0), name="product_price_non_negative"
            ),
            models.UniqueConstraint(
                fields=["property", "sku"],
                condition=~Q(sku=""),
                name="product_sku_per_property",
            ),
        ]
        indexes = [models.Index(fields=["property", "is_active"])]

    def __str__(self) -> str:
        return self.name


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    CONFIRMED = "CONFIRMED", "Confirmed"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"


class Order(TimeStampedModel):
    property = models.ForeignKey(
        "properties.Property", on_delete=models.CASCADE, related_name="orders"
    )
    orderer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )
    unit = models.ForeignKey(
        "properties.Unit",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    status = models.CharField(
        max_length=10, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_instructions = models.TextField(blank=True)
    customer_note = models.TextField(blank=True)
    staff_note = models.TextField(blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(total_amount__gte=0), name="order_total_non_negative"
            )
        ]
        indexes = [
            models.Index(fields=["property", "status"]),
            models.Index(fields=["orderer", "status"]),
        ]

    def __str__(self) -> str:
        return f"Order #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    # A deleted product leaves past orders intact: each line keeps its name and price.
    product = models.ForeignKey(
        Product,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_items",
    )
    # Frozen at order time: later catalogue edits never rewrite history.
    product_name = models.CharField(max_length=160)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["order_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"], name="unique_product_per_order"
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=1), name="order_item_quantity_positive"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} x {self.product_name}"
