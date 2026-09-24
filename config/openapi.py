"""Settings of the OpenAPI schema (drf-spectacular)."""

SPECTACULAR_SETTINGS = {
    "TITLE": "Residential Platform API",
    "DESCRIPTION": "Property management SaaS: referential, leasing, resident services.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    # Readable names for the enums that share a field name across modules
    # (otherwise suffixed with a hash: Category758Enum...).
    "ENUM_NAME_OVERRIDES": {
        "AnnouncementCategoryEnum": "apps.announcements.models.AnnouncementCategory",
        "AnnouncementPriorityEnum": "apps.announcements.models.AnnouncementPriority",
        "ListingCategoryEnum": "apps.marketplace.models.ListingCategory",
        "ServiceRequestCategoryEnum": "apps.service_requests.models.ServiceRequestCategory",
        "WorkOrderCategoryEnum": "apps.work_orders.models.WorkOrderCategory",
        # Same values for service requests and work orders.
        "PriorityEnum": "apps.service_requests.models.ServiceRequestPriority",
        "LeaseTerminationReasonEnum": "apps.leasing.models.LeaseTerminationReason",
        "BookingStatusEnum": "apps.amenities.models.BookingStatus",
        "RequesterNoticeEnum": "apps.service_requests.models.RequesterNotice",
        "ComponentConditionEnum": "apps.leasing.models.ComponentCondition",
        "CheckPhaseEnum": "apps.leasing.models.CheckPhase",
        "WorkOrderActionEnum": ["start", "hold", "complete", "cancel"],
        "PushPlatformEnum": [("ios", "iOS"), ("android", "Android"), ("web", "Web")],
        "ChatContextTypeEnum": ["service_request", "booking", "order"],
        "AccountRoleEnum": "apps.accounts.enums.StructuralRole",
        "PropertyRoleEnum": "apps.accounts.enums.PropertyRole",
        "SessionAppModeEnum": ["web", "mobile"],
        "UIConfigStepEnum": ["syndicat", "property", "dashboard"],
    },
}
