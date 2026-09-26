from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.common.attachments.rules import EntityType
from apps.common.attachments.serializers import AttachmentsField
from apps.common.serializers import UserSummarySerializer
from apps.store.models import Order, OrderItem, OrderStatus, Product


class ProductSerializer(serializers.ModelSerializer):
    images = AttachmentsField(EntityType.PRODUCT)

    class Meta:
        model = Product
        fields = [
            "id",
            "property",
            "name",
            "description",
            "category",
            "sku",
            "price",
            "stock_quantity",
            "is_active",
            "images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "unit_price",
            "quantity",
            "line_total",
        ]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    orderer = UserSummarySerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "property",
            "unit",
            "orderer",
            "status",
            "total_amount",
            "delivery_instructions",
            "customer_note",
            "staff_note",
            "items",
            "confirmed_at",
            "delivered_at",
            "cancelled_at",
            "cancellation_reason",
            "created_at",
        ]
        read_only_fields = fields


class ProductFieldsSerializer(serializers.Serializer):
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(max_length=80, required=False, allow_blank=True)
    sku = serializers.CharField(max_length=64, required=False, allow_blank=True)
    stock_quantity = serializers.IntegerField(min_value=0, required=False)
    is_active = serializers.BooleanField(required=False)


class ProductCreateSerializer(ProductFieldsSerializer):
    name = serializers.CharField(max_length=160)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)


@extend_schema_serializer(component_name="Product")
class ProductUpdateSerializer(ProductFieldsSerializer):
    name = serializers.CharField(max_length=160, required=False)
    price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False
    )


class ProductsQueryParamsSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, max_length=80)
    include_inactive = serializers.BooleanField(required=False, default=False)


class OrderLineSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=1000)


class OrderCreateSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, default=None
    )
    items = OrderLineSerializer(many=True, allow_empty=False)
    delivery_instructions = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=1000
    )
    customer_note = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=1000
    )


class OrdersQueryParamsSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderStatus.choices, required=False)
    mine = serializers.BooleanField(required=False, default=False)
