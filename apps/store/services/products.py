"""Store catalogue: products (managed by platform administrators only) and their images."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Q, QuerySet

from apps.common.db import apply_changes, deleting, translate_integrity_errors
from apps.common.exceptions import (
    InvalidInput,
    NotFound,
    PermissionDenied,
)
from apps.common.models import EntityType
from apps.common.services.attachments import AttachmentService
from apps.common.services.audit import AuditService
from apps.properties.enums import Feature
from apps.properties.models import Property
from apps.properties.services import FeatureGate
from apps.store import errors
from apps.store.audit import StoreAudit
from apps.store.models import Product
from apps.store.policies import ProductPolicy

PRODUCT_CONSTRAINTS = {"product_sku_per_property": errors.sku_taken}
PRODUCT_FIELDS = ("name", "description", "category", "sku", "price", "stock_quantity", "is_active")


class ProductService:
    @staticmethod
    def list_visible(
        *, actor, prop: Property, include_inactive: bool = False, search: str | None = None
    ) -> QuerySet[Product]:
        FeatureGate.require(prop, Feature.STORE)
        if not ProductPolicy.can_list(actor, prop):
            raise PermissionDenied("You have no link with this property.")
        qs = Product.objects.filter(property=prop)
        if not (include_inactive and ProductPolicy.can_see_inactive(actor)):
            qs = qs.filter(is_active=True)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(category__icontains=search))
        return qs

    @staticmethod
    def get_visible(*, actor, product_id: int) -> Product:
        product = Product.objects.select_related("property").filter(pk=product_id).first()
        if product is None or not ProductPolicy.can_view(actor, product):
            raise NotFound("Product not found.")
        return product

    @staticmethod
    def _validate(product: Product) -> None:
        if product.price is None or product.price < 0:
            raise InvalidInput("The price must be positive.", field="price")

    @staticmethod
    @transaction.atomic
    def create(*, actor, prop: Property, data: dict) -> Product:
        if not ProductPolicy.can_manage(actor):
            raise errors.store_admins_only()
        FeatureGate.require(prop, Feature.STORE)
        product = Product(property=prop, created_by=actor)
        apply_changes(product, data, PRODUCT_FIELDS)
        ProductService._validate(product)
        with translate_integrity_errors(PRODUCT_CONSTRAINTS):
            product.save()
        AuditService.record(
            actor=actor, action=StoreAudit.PRODUCT_CREATED, target=product, property_id=prop.pk
        )
        return product

    @staticmethod
    @transaction.atomic
    def update(*, actor, product: Product, changes: dict) -> Product:
        if not ProductPolicy.can_manage(actor):
            raise errors.store_admins_only()
        product = Product.objects.select_for_update(of=("self",)).get(pk=product.pk)
        fields = apply_changes(product, changes, PRODUCT_FIELDS)
        ProductService._validate(product)
        if fields:
            with translate_integrity_errors(PRODUCT_CONSTRAINTS):
                product.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=StoreAudit.PRODUCT_UPDATED,
                target=product,
                property_id=product.property_id,
                metadata={"fields": fields},
            )
        return product

    @staticmethod
    @transaction.atomic
    def delete(*, actor, product: Product) -> None:
        """Removable while it was never ordered; otherwise deactivate it."""
        if not ProductPolicy.can_manage(actor):
            raise errors.store_admins_only()
        AuditService.record(
            actor=actor,
            action=StoreAudit.PRODUCT_DELETED,
            target=product,
            property_id=product.property_id,
        )
        with deleting("product", hint="Set it inactive instead to keep past orders."):
            AttachmentService.delete_for_entity(EntityType.PRODUCT, product.pk)
            product.delete()

    @staticmethod
    @transaction.atomic
    def add_images(*, actor, product: Product, files) -> list:
        if not ProductPolicy.can_manage(actor):
            raise errors.store_admins_only()
        return AttachmentService.attach(
            entity_type=EntityType.PRODUCT,
            entity_id=product.pk,
            files=list(files),
            uploaded_by=actor,
        )

    @staticmethod
    @transaction.atomic
    def remove_image(*, actor, product: Product, attachment_id: int) -> None:
        if not ProductPolicy.can_manage(actor):
            raise errors.store_admins_only()
        AttachmentService.delete(
            attachment=AttachmentService.get(
                entity_type=EntityType.PRODUCT, entity_id=product.pk, attachment_id=attachment_id
            )
        )
