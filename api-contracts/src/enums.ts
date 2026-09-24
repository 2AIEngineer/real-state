// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";

/**
 * * `admin` - Administrator
 * * `syndic` - Syndic
 * * `manager` - Manager
 * * `security` - Security
 * * `maintenance` - Maintenance
 * * `cleaning` - Cleaning
 * * `provider` - Service provider
 * * `standard` - Standard account
 */
export const accountRoleSchema = z.enum(["admin", "syndic", "manager", "security", "maintenance", "cleaning", "provider", "standard"]);
export type AccountRole = z.infer<typeof accountRoleSchema>;

/**
 * * `general` - General information
 * * `meeting` - Meetings & assemblies
 * * `maintenance` - Maintenance work
 * * `security` - Security
 * * `rules` - Rules & policies
 * * `financial` - Financial information
 * * `community` - Community life
 * * `emergency` - Emergency
 */
export const announcementCategorySchema = z.enum(["general", "meeting", "maintenance", "security", "rules", "financial", "community", "emergency"]);
export type AnnouncementCategory = z.infer<typeof announcementCategorySchema>;

/**
 * * `normal` - Normal
 * * `important` - Important
 * * `urgent` - Urgent
 */
export const announcementPrioritySchema = z.enum(["normal", "important", "urgent"]);
export type AnnouncementPriority = z.infer<typeof announcementPrioritySchema>;

/**
 * * `EXCLUSIVE` - Exclusive slot (one booking at a time)
 * * `SHARED` - Shared (concurrent bookings up to capacity)
 */
export const bookingModeSchema = z.enum(["EXCLUSIVE", "SHARED"]);
export type BookingMode = z.infer<typeof bookingModeSchema>;

/**
 * * `PENDING` - Pending approval
 * * `CONFIRMED` - Confirmed
 * * `REJECTED` - Rejected
 * * `CANCELLED` - Cancelled
 */
export const bookingStatusSchema = z.enum(["PENDING", "CONFIRMED", "REJECTED", "CANCELLED"]);
export type BookingStatus = z.infer<typeof bookingStatusSchema>;

/**
 * * `service_request` - service_request
 * * `booking` - booking
 * * `order` - order
 */
export const chatContextTypeSchema = z.enum(["service_request", "booking", "order"]);
export type ChatContextType = z.infer<typeof chatContextTypeSchema>;

/**
 * * `IN` - Move-in inspection
 * * `OUT` - Move-out inspection
 */
export const checkPhaseSchema = z.enum(["IN", "OUT"]);
export type CheckPhase = z.infer<typeof checkPhaseSchema>;

/**
 * * `GOOD` - Good
 * * `BAD` - Bad
 */
export const componentConditionSchema = z.enum(["GOOD", "BAD"]);
export type ComponentCondition = z.infer<typeof componentConditionSchema>;

/**
 * * `SALE` - Sold to a new owner
 * * `DEPARTURE` - Owner left (no registered acquirer)
 * * `PROMOTER_CHANGE` - Property promoter replaced
 * * `CORRECTION` - Administrative correction
 */
export const endReasonSchema = z.enum(["SALE", "DEPARTURE", "PROMOTER_CHANGE", "CORRECTION"]);
export type EndReason = z.infer<typeof endReasonSchema>;

/**
 * * `syndicat_logo` - Syndicat logo
 * * `property_logo` - Property logo
 * * `announcement` - Announcement files
 * * `event` - Event files
 * * `survey` - Survey files
 * * `library_document` - Library document file
 * * `amenity` - Amenity images
 * * `product` - Store product images
 * * `marketplace_listing` - Marketplace listing images
 * * `service_request` - Service request files
 * * `service_request_resolution` - Resolution evidence of a service request round
 * * `work_order` - Work order files
 * * `lease_component_state` - Inspection files
 * * `lease_member_identity` - Lease member proof of identity
 * * `lease_member_address` - Lease member proof of address
 * * `visitor_id_card` - Visitor identity card
 * * `short_term_rental_member_id_card` - Short-term rental member identity card
 * * `chat_message` - Chat message file
 */
export const entityTypeSchema = z.enum(["syndicat_logo", "property_logo", "announcement", "event", "survey", "library_document", "amenity", "product", "marketplace_listing", "service_request", "service_request_resolution", "work_order", "lease_component_state", "lease_member_identity", "lease_member_address", "visitor_id_card", "short_term_rental_member_id_card", "chat_message"]);
export type EntityType = z.infer<typeof entityTypeSchema>;

/**
 * * `SCHEDULED` - Scheduled
 * * `CANCELLED` - Cancelled
 * * `COMPLETED` - Completed
 */
export const eventStatusSchema = z.enum(["SCHEDULED", "CANCELLED", "COMPLETED"]);
export type EventStatus = z.infer<typeof eventStatusSchema>;

/**
 * * `FEMALE` - Female
 * * `MALE` - Male
 * * `OTHER` - Other
 * * `UNDISCLOSED` - Undisclosed
 */
export const genderSchema = z.enum(["FEMALE", "MALE", "OTHER", "UNDISCLOSED"]);
export type Gender = z.infer<typeof genderSchema>;

/**
 * * `account` - Account
 * * `property` - Property administration
 * * `leasing` - Leasing
 * * `service_request` - Service requests
 * * `work_order` - Work orders
 * * `announcement` - Announcements
 * * `event` - Events
 * * `booking` - Amenity bookings
 * * `store` - Store
 * * `library` - Library
 * * `short_term_rental` - Short-term rentals
 * * `survey` - Surveys
 * * `marketplace` - Marketplace
 * * `visitor` - Visitors
 * * `chat` - Chat
 */
export const inboxNotificationCategorySchema = z.enum(["account", "property", "leasing", "service_request", "work_order", "announcement", "event", "booking", "store", "library", "short_term_rental", "survey", "marketplace", "visitor", "chat"]);
export type InboxNotificationCategory = z.infer<typeof inboxNotificationCategorySchema>;

/**
 * * `TENANT` - Tenant of the unit
 * * `OWNER` - Owner of the unit
 * * `MANAGEMENT` - Property management
 */
export const initiatorCapacitySchema = z.enum(["TENANT", "OWNER", "MANAGEMENT"]);
export type InitiatorCapacity = z.infer<typeof initiatorCapacitySchema>;

/**
 * * `ACTIVE` - Active
 * * `TERMINATED` - Terminated
 * * `CANCELLED` - Cancelled
 */
export const leaseStatusSchema = z.enum(["ACTIVE", "TERMINATED", "CANCELLED"]);
export type LeaseStatus = z.infer<typeof leaseStatusSchema>;

/**
 * * `TERM_REACHED` - Contract term reached
 * * `TENANT_NOTICE` - Notice given by tenant
 * * `LANDLORD_NOTICE` - Notice given by landlord
 * * `MUTUAL_AGREEMENT` - Mutual agreement
 * * `BREACH` - Breach of contract
 * * `OTHER` - Other
 */
export const leaseTerminationReasonSchema = z.enum(["TERM_REACHED", "TENANT_NOTICE", "LANDLORD_NOTICE", "MUTUAL_AGREEMENT", "BREACH", "OTHER"]);
export type LeaseTerminationReason = z.infer<typeof leaseTerminationReasonSchema>;

/**
 * * `real_estate_rental` - Real estate for rent
 * * `real_estate_sale` - Real estate for sale
 * * `various_offer` - Various offers
 */
export const listingCategorySchema = z.enum(["real_estate_rental", "real_estate_sale", "various_offer"]);
export type ListingCategory = z.infer<typeof listingCategorySchema>;

/**
 * * `PUBLISHED` - Published
 * * `SOLD` - Sold / rented
 * * `ARCHIVED` - Archived by the seller
 * * `MODERATED` - Taken down by moderation
 */
export const marketplaceListingStatusSchema = z.enum(["PUBLISHED", "SOLD", "ARCHIVED", "MODERATED"]);
export type MarketplaceListingStatus = z.infer<typeof marketplaceListingStatusSchema>;

/**
 * * `PENDING` - Pending
 * * `CONFIRMED` - Confirmed
 * * `DELIVERED` - Delivered
 * * `CANCELLED` - Cancelled
 */
export const orderStatusSchema = z.enum(["PENDING", "CONFIRMED", "DELIVERED", "CANCELLED"]);
export type OrderStatus = z.infer<typeof orderStatusSchema>;

/**
 * * `DEPARTURE` - DEPARTURE
 * * `CORRECTION` - CORRECTION
 */
export const ownershipEndReasonSchema = z.enum(["DEPARTURE", "CORRECTION"]);
export type OwnershipEndReason = z.infer<typeof ownershipEndReasonSchema>;

/**
 * * `ACTIVE` - Active
 * * `TERMINATED` - Terminated
 */
export const ownershipStatusSchema = z.enum(["ACTIVE", "TERMINATED"]);
export type OwnershipStatus = z.infer<typeof ownershipStatusSchema>;

/**
 * * `fr` - Français
 * * `en` - English
 */
export const preferredLanguageSchema = z.enum(["fr", "en"]);
export type PreferredLanguage = z.infer<typeof preferredLanguageSchema>;

/**
 * * `LOW` - Low
 * * `MEDIUM` - Medium
 * * `HIGH` - High
 * * `URGENT` - Urgent
 */
export const prioritySchema = z.enum(["LOW", "MEDIUM", "HIGH", "URGENT"]);
export type Priority = z.infer<typeof prioritySchema>;

/**
 * * `admin` - Administrators
 * * `syndic` - Syndics
 * * `manager` - Managers
 * * `security` - Security
 * * `maintenance` - Maintenance
 * * `cleaning` - Cleaning
 * * `provider` - Service providers
 * * `owner` - Owners
 * * `tenant` - Tenants
 */
export const propertyRoleSchema = z.enum(["admin", "syndic", "manager", "security", "maintenance", "cleaning", "provider", "owner", "tenant"]);
export type PropertyRole = z.infer<typeof propertyRoleSchema>;

/**
 * * `ios` - iOS
 * * `android` - Android
 * * `web` - Web
 */
export const pushPlatformSchema = z.enum(["ios", "android", "web"]);
export type PushPlatform = z.infer<typeof pushPlatformSchema>;

/**
 * * `DONE` - Done
 * * `NOT_DONE` - Not done
 */
export const requesterNoticeSchema = z.enum(["DONE", "NOT_DONE"]);
export type RequesterNotice = z.infer<typeof requesterNoticeSchema>;

/**
 * * `plumbing` - Plumbing
 * * `electricity` - Electricity
 * * `hvac` - Heating / air conditioning
 * * `elevator` - Elevator
 * * `cleaning` - Cleaning
 * * `security` - Security
 * * `common_areas` - Common areas
 * * `noise` - Noise / neighbourhood
 * * `information` - Information request
 * * `suggestion` - Comment or suggestion
 * * `other` - Other
 */
export const serviceRequestCategorySchema = z.enum(["plumbing", "electricity", "hvac", "elevator", "cleaning", "security", "common_areas", "noise", "information", "suggestion", "other"]);
export type ServiceRequestCategory = z.infer<typeof serviceRequestCategorySchema>;

/**
 * * `OPEN` - Open (awaiting assignment)
 * * `IN_PROGRESS` - In progress
 * * `RESOLVED` - Resolved (awaiting requester confirmation)
 * * `CLOSED` - Closed
 * * `CANCELLED` - Cancelled
 */
export const serviceStatusSchema = z.enum(["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", "CANCELLED"]);
export type ServiceStatus = z.infer<typeof serviceStatusSchema>;

/**
 * * `plumbing` - Plumbing
 * * `electricity` - Electricity
 * * `hvac` - Heating / air conditioning
 * * `carpentry` - Carpentry
 * * `painting` - Painting
 * * `locksmith` - Locksmith
 * * `elevator` - Elevator maintenance
 * * `cleaning` - Cleaning
 * * `gardening` - Gardening / landscaping
 * * `pest_control` - Pest control
 * * `security` - Security services
 * * `it_network` - IT / network
 * * `moving` - Moving
 * * `other` - Other
 */
export const serviceTypeSchema = z.enum(["plumbing", "electricity", "hvac", "carpentry", "painting", "locksmith", "elevator", "cleaning", "gardening", "pest_control", "security", "it_network", "moving", "other"]);
export type ServiceType = z.infer<typeof serviceTypeSchema>;

/**
 * * `INFO` - Information
 * * `SUCCESS` - Success
 * * `WARNING` - Warning
 * * `CRITICAL` - Critical
 */
export const severitySchema = z.enum(["INFO", "SUCCESS", "WARNING", "CRITICAL"]);
export type Severity = z.infer<typeof severitySchema>;

/**
 * * `SCHEDULED` - Scheduled
 * * `CHECKED_IN` - Members on site
 * * `COMPLETED` - Completed
 * * `CANCELLED` - Cancelled
 */
export const shortTermRentalStatusSchema = z.enum(["SCHEDULED", "CHECKED_IN", "COMPLETED", "CANCELLED"]);
export type ShortTermRentalStatus = z.infer<typeof shortTermRentalStatusSchema>;

/**
 * * `DRAFT` - Draft
 * * `PUBLISHED` - Open for answers
 * * `CLOSED` - Closed
 */
export const surveyStatusSchema = z.enum(["DRAFT", "PUBLISHED", "CLOSED"]);
export type SurveyStatus = z.infer<typeof surveyStatusSchema>;

/**
 * * `apartment` - Apartment
 * * `house` - House / villa
 * * `office` - Office
 * * `commercial` - Commercial space
 * * `parking` - Parking space
 * * `storage` - Storage
 * * `other` - Other
 */
export const unitTypeSchema = z.enum(["apartment", "house", "office", "commercial", "parking", "storage", "other"]);
export type UnitType = z.infer<typeof unitTypeSchema>;

/**
 * * `ARRIVED` - On site
 * * `LEFT` - Left
 * * `DENIED` - Entry denied
 */
export const visitorStatusSchema = z.enum(["ARRIVED", "LEFT", "DENIED"]);
export type VisitorStatus = z.infer<typeof visitorStatusSchema>;

/**
 * * `start` - start
 * * `hold` - hold
 * * `complete` - complete
 * * `cancel` - cancel
 */
export const workOrderActionSchema = z.enum(["start", "hold", "complete", "cancel"]);
export type WorkOrderAction = z.infer<typeof workOrderActionSchema>;

/**
 * * `preventive` - Preventive maintenance
 * * `corrective` - Corrective maintenance
 * * `inspection` - Inspection
 * * `cleaning` - Cleaning
 * * `renovation` - Renovation
 * * `other` - Other
 */
export const workOrderCategorySchema = z.enum(["preventive", "corrective", "inspection", "cleaning", "renovation", "other"]);
export type WorkOrderCategory = z.infer<typeof workOrderCategorySchema>;

/**
 * * `OPEN` - Open
 * * `IN_PROGRESS` - In progress
 * * `ON_HOLD` - On hold
 * * `COMPLETED` - Completed
 * * `CANCELLED` - Cancelled
 */
export const workOrderStatusSchema = z.enum(["OPEN", "IN_PROGRESS", "ON_HOLD", "COMPLETED", "CANCELLED"]);
export type WorkOrderStatus = z.infer<typeof workOrderStatusSchema>;

/**
 * * `web` - web
 * * `mobile` - mobile
 */
export const sessionAppModeSchema = z.enum(["web", "mobile"]);
export type SessionAppMode = z.infer<typeof sessionAppModeSchema>;

/**
 * * `syndicat` - syndicat
 * * `property` - property
 * * `dashboard` - dashboard
 */
export const uiConfigStepSchema = z.enum(["syndicat", "property", "dashboard"]);
export type UIConfigStep = z.infer<typeof uiConfigStepSchema>;
