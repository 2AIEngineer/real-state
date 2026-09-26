from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.accounts.services.accounts import AccountService
from apps.common.views import BaseAPIView
from apps.properties import serializers as s
from apps.properties.services import (
    Acquirer,
    OwnershipService,
    UnitService,
)


def _user(user_id: int, field: str = "user_id"):
    return AccountService.resolve(user_id=user_id, field=field)


@extend_schema(tags=["Ownership"])
class OwnershipListView(BaseAPIView):
    @extend_schema(responses=s.OwnershipSerializer(many=True))
    def get(self, request, unit_id: int):
        unit = UnitService.get_visible(
            actor=request.user, prop=self.property, unit_id=unit_id
        )
        return self.render_page(
            s.OwnershipSerializer,
            OwnershipService.history(actor=request.user, unit=unit),
        )


@extend_schema(tags=["Ownership"])
class OwnershipTransferView(BaseAPIView):
    pagination_class = None  # a plain list of the new owners

    @extend_schema(
        request=s.OwnershipTransferSerializer,
        responses={201: s.OwnershipSerializer(many=True)},
    )
    def post(self, request, unit_id: int):
        unit = UnitService.get_visible(
            actor=request.user, prop=self.property, unit_id=unit_id
        )
        data = self.parse(s.OwnershipTransferSerializer)
        acquirers = [
            Acquirer(user=_user(a["user_id"], "acquirers"), share=a["share"])
            for a in data["acquirers"]
        ]
        created = OwnershipService.transfer(
            actor=request.user,
            unit=unit,
            acquirers=acquirers,
            effective_date=data["effective_date"],
            reference=data["reference"],
        )
        return self.render(
            s.OwnershipSerializer, created, many=True, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Ownership"])
class CoOwnerView(BaseAPIView):
    @extend_schema(
        request=s.OwnershipCoOwnerSerializer, responses={201: s.OwnershipSerializer}
    )
    def post(self, request, unit_id: int):
        unit = UnitService.get_visible(
            actor=request.user, prop=self.property, unit_id=unit_id
        )
        data = self.parse(s.OwnershipCoOwnerSerializer)
        ownership = OwnershipService.add_co_owner(
            actor=request.user,
            unit=unit,
            user=_user(data["user_id"]),
            share=data["share"],
            start_date=data["start_date"],
        )
        return self.render(
            s.OwnershipSerializer, ownership, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Ownership"])
class OwnershipEndView(BaseAPIView):
    @extend_schema(request=s.OwnershipEndSerializer, responses=s.OwnershipSerializer)
    def post(self, request, ownership_id: int):
        ownership = OwnershipService.get(ownership_id=ownership_id)
        data = self.parse(s.OwnershipEndSerializer)
        ownership = OwnershipService.end(
            actor=request.user,
            ownership=ownership,
            end_date=data["end_date"],
            reason=data["reason"],
        )
        return self.render(s.OwnershipSerializer, ownership)


@extend_schema(tags=["Ownership"])
class OwnershipDetailView(BaseAPIView):
    @extend_schema(
        responses={204: None},
        description="Erases a ledger line recorded by mistake; the unit never stays without an owner.",
    )
    def delete(self, request, ownership_id: int):
        ownership = OwnershipService.get(ownership_id=ownership_id)
        OwnershipService.delete(actor=request.user, ownership=ownership)
        return Response(status=status.HTTP_204_NO_CONTENT)
