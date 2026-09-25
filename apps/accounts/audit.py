"""Actions this module writes in the audit journal."""

from enum import StrEnum


class AccountAudit(StrEnum):
    CREATED = "account.created"
    DEACTIVATED = "account.deactivated"
    DELETED = "account.deleted"
    EMAIL_CHANGED = "account.email_changed"
    INVITATION_RESENT = "account.invitation_resent"
    PASSWORD_CHANGED = "account.password_changed"
    PASSWORD_SET = "account.password_set"
    PROFILE_UPDATED = "account.profile_updated"
    REACTIVATED = "account.reactivated"


class AssignmentAudit(StrEnum):
    DELETED = "assignment.deleted"
    GRANTED = "assignment.granted"
    REVOKED = "assignment.revoked"


class RoleAudit(StrEnum):
    CHANGED = "role.changed"
