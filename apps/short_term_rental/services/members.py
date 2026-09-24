"""Members of a short rental: the people who stay in the unit."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import QuerySet

from apps.common.db import apply_changes
from apps.common.exceptions import (
    BusinessRuleViolation,
    NotFound,
)
from apps.common.files.rules import EntityType
from apps.common.files.service import AttachmentService
from apps.common.services.audit import AuditService
from apps.short_term_rental.audit import ShortTermRentalAudit
from apps.short_term_rental.models import (
    ShortTermRental,
    ShortTermRentalMember,
)
from apps.short_term_rental.policies import ShortTermRentalPolicy
from apps.short_term_rental.services.rules import (
    lock_rental,
    require_editable,
)

MEMBER_FIELDS = (
    "first_name",
    "last_name",
    "gender",
    "date_of_birth",
    "nationality",
    "id_document_number",
    "phone",
    "email",
)


@dataclass
class ShortTermRentalMemberInput:
    first_name: str
    last_name: str
    data: dict = field(default_factory=dict)

    def create_for(self, rental: ShortTermRental) -> ShortTermRentalMember:
        """Record this person as a member of the rental."""
        return ShortTermRentalMember.objects.create(
            short_term_rental=rental,
            first_name=self.first_name.strip(),
            last_name=self.last_name.strip(),
            **{name: value for name, value in self.data.items() if name in MEMBER_FIELDS},
        )


class ShortTermRentalMemberService:
    @staticmethod
    def list_for_rental(*, actor, rental: ShortTermRental) -> QuerySet[ShortTermRentalMember]:
        if not ShortTermRentalPolicy.can_view(actor, rental):
            raise NotFound("Short rental not found.")
        return rental.members.all()

    @staticmethod
    @transaction.atomic
    def add(
        *,
        actor,
        rental: ShortTermRental,
        new_member: ShortTermRentalMemberInput,
        make_primary: bool = False,
    ) -> ShortTermRentalMember:
        rental = lock_rental(rental)
        require_editable(actor, rental)
        member = new_member.create_for(rental)
        if make_primary:
            rental.primary_member = member
            rental.save(update_fields=["primary_member", "updated_at"])
        AuditService.record(
            actor=actor,
            action=ShortTermRentalAudit.MEMBER_ADDED,
            target=member,
            property_id=rental.property_id,
        )
        return member

    @staticmethod
    @transaction.atomic
    def update(
        *, actor, member: ShortTermRentalMember, changes: dict, make_primary: bool = False
    ) -> ShortTermRentalMember:
        rental = lock_rental(member.short_term_rental)
        require_editable(actor, rental)
        fields = apply_changes(member, changes, MEMBER_FIELDS)
        if fields:
            member.save(update_fields=[*fields, "updated_at"])
        if make_primary and rental.primary_member_id != member.pk:
            rental.primary_member = member
            rental.save(update_fields=["primary_member", "updated_at"])
        AuditService.record(
            actor=actor,
            action=ShortTermRentalAudit.MEMBER_UPDATED,
            target=member,
            property_id=rental.property_id,
        )
        return member

    @staticmethod
    @transaction.atomic
    def remove(*, actor, member: ShortTermRentalMember) -> None:
        rental = lock_rental(member.short_term_rental)
        require_editable(actor, rental)
        if rental.members.count() == 1:
            raise BusinessRuleViolation("A rental needs at least one member.", code="last_member")
        if rental.primary_member_id == member.pk:
            raise BusinessRuleViolation(
                "Designate another primary member before removing this one.", code="primary_member"
            )
        AuditService.record(
            actor=actor,
            action=ShortTermRentalAudit.MEMBER_REMOVED,
            target=member,
            property_id=rental.property_id,
        )
        AttachmentService.delete_for_entity(EntityType.SHORT_TERM_RENTAL_MEMBER_ID_CARD, member.pk)
        member.delete()

    @staticmethod
    @transaction.atomic
    def set_id_card(*, actor, member: ShortTermRentalMember, upload) -> None:
        require_editable(actor, member.short_term_rental)
        AttachmentService.attach_one(
            entity_type=EntityType.SHORT_TERM_RENTAL_MEMBER_ID_CARD,
            entity_id=member.pk,
            upload=upload,
            uploaded_by=actor,
        )

    @staticmethod
    def get_visible(*, actor, member_id: int) -> ShortTermRentalMember:
        member = (
            ShortTermRentalMember.objects.select_related(
                "short_term_rental__unit__building__property"
            )
            .filter(pk=member_id)
            .first()
        )
        if member is None or not ShortTermRentalPolicy.can_view_member(actor, member):
            raise NotFound("Member not found.")
        return member
