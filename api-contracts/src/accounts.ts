// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import {
  accountRoleSchema,
  genderSchema,
  preferredLanguageSchema,
  serviceTypeSchema,
  sessionAppModeSchema,
  uiConfigStepSchema,
} from "./enums";
import { decimalString, paginated } from "./shared";

export const accountDeactivationRequestSchema = z.object({
  reason: z.string().max(500).optional(),
});
export type AccountDeactivationRequest = z.infer<
  typeof accountDeactivationRequestSchema
>;

/** A unit the account owns from the day it is registered. */
export const accountOwnershipRequestSchema = z.object({
  unit_id: z.number().int().min(1),
  /** Percentage held; left out, a sole owner holds 100%. */
  share: decimalString(/^-?\d{0,3}(?:\.\d{0,2})?$/)
    .nullable()
    .optional(),
});
export type AccountOwnershipRequest = z.infer<
  typeof accountOwnershipRequestSchema
>;

/**
 * The unit the account rents.
 *
 * It joins the lease running on that unit; when the unit has none — the
 * ordinary case for its first tenant — a lease opens with the dates given
 * here and the account as its signatory.
 */
export const accountTenancyRequestSchema = z.object({
  unit_id: z.number().int().min(1),
  /** Ignored when the lease opens: its first tenant signs it. */
  is_signatory: z.boolean().optional(),
  /** Start of the lease to open; today by default. */
  start_date: z.iso.date().nullable().optional(),
  end_date: z.iso.date().nullable().optional(),
  contract_reference: z.string().max(120).optional(),
});
export type AccountTenancyRequest = z.infer<typeof accountTenancyRequestSchema>;

/**
 * The buildings a security or cleaning account is assigned to. They must
 * belong to the selected property, which is what places them.
 */
export const buildingAssignmentInputRequestSchema = z.object({
  /** Buildings of the selected property. */
  building_ids: z.array(z.number().int().min(1)),
});
export type BuildingAssignmentInputRequest = z.infer<
  typeof buildingAssignmentInputRequestSchema
>;

export const emailChangeRequestSchema = z.object({
  email: z.email().min(1),
  current_password: z.string().min(1).optional(),
});
export type EmailChangeRequest = z.infer<typeof emailChangeRequestSchema>;

/** Case-insensitive e-mail login. */
export const loginRequestSchema = z.object({
  email: z.string().min(1),
  password: z.string().min(1),
});
export type LoginRequest = z.infer<typeof loginRequestSchema>;

export const passwordChangeRequestSchema = z.object({
  current_password: z.string().min(1),
  new_password: z.string().min(1),
});
export type PasswordChangeRequest = z.infer<typeof passwordChangeRequestSchema>;

export const passwordResetRequestSchema = z.object({
  email: z.email().min(1),
});
export type PasswordResetRequest = z.infer<typeof passwordResetRequestSchema>;

export const passwordSetRequestSchema = z.object({
  uid: z.string().min(1),
  token: z.string().min(1),
  password: z.string().min(1),
});
export type PasswordSetRequest = z.infer<typeof passwordSetRequestSchema>;

export const patchedProviderProfileRequestSchema = z.object({
  company_name: z.string().max(200).optional(),
  service_type: serviceTypeSchema.optional(),
  service_description: z.string().optional(),
  address: z.string().optional(),
  business_phone: z.string().max(32).optional(),
  website: z.union([z.url(), z.literal("")]).optional(),
  registration_number: z.string().max(64).optional(),
});
export type PatchedProviderProfileRequest = z.infer<
  typeof patchedProviderProfileRequestSchema
>;

export const patchedUserProfileRequestSchema = z.object({
  first_name: z.string().min(1).max(150).optional(),
  last_name: z.string().min(1).max(150).optional(),
  phone: z.string().max(32).optional(),
  gender: genderSchema.optional(),
  preferred_language: preferredLanguageSchema.optional(),
});
export type PatchedUserProfileRequest = z.infer<
  typeof patchedUserProfileRequestSchema
>;

export const providerProfileSchema = z.object({
  company_name: z.string().max(200).optional(),
  service_type: serviceTypeSchema.optional(),
  service_description: z.string().optional(),
  address: z.string().optional(),
  business_phone: z.string().max(32).optional(),
  website: z
    .union([z.union([z.url(), z.literal("")]), z.literal("")])
    .optional(),
  registration_number: z.string().max(64).optional(),
  updated_at: z.iso.datetime({ offset: true }),
});
export type ProviderProfile = z.infer<typeof providerProfileSchema>;

/**
 * The new role, and — for a security or cleaning role — the buildings it
 * is exercised in. Every other role takes its place from the selected
 * syndicat or the selected property.
 */
export const roleChangeRequestSchema = z.object({
  role: accountRoleSchema,
  /** Security, cleaning: buildings of the selected property. */
  building_ids: z.array(z.number().int().min(1)).optional(),
});
export type RoleChangeRequest = z.infer<typeof roleChangeRequestSchema>;

export const tokenRefreshSchema = z.object({
  access: z.string(),
  refresh: z.string(),
});
export type TokenRefresh = z.infer<typeof tokenRefreshSchema>;

export const tokenRefreshRequestSchema = z.object({
  refresh: z.string().min(1),
});
export type TokenRefreshRequest = z.infer<typeof tokenRefreshRequestSchema>;

export const userSchema = z.object({
  id: z.number().int(),
  email: z.union([z.email(), z.literal("")]),
  first_name: z.string(),
  last_name: z.string(),
  full_name: z.string(),
  phone: z.string(),
  gender: genderSchema,
  preferred_language: preferredLanguageSchema,
  role: accountRoleSchema,
  is_active: z.boolean(),
  /** Whether the invitation was accepted (a password was set). */
  is_activated: z.boolean(),
  date_joined: z.iso.datetime({ offset: true }),
  last_login: z.iso.datetime({ offset: true }).nullable(),
  deactivated_at: z.iso.datetime({ offset: true }).nullable(),
});
export type User = z.infer<typeof userSchema>;

/** A security or cleaning agent, and a building they work in. */
export const userBuildingSchema = z.object({
  id: z.number().int(),
  is_active: z.boolean(),
  granted_by: z.number().int().nullable(),
  created_at: z.iso.datetime({ offset: true }),
  revoked_at: z.iso.datetime({ offset: true }).nullable(),
  revoked_by: z.number().int().nullable(),
  building: z.number().int(),
  building_name: z.string(),
});
export type UserBuilding = z.infer<typeof userBuildingSchema>;

/** A manager or a maintenance agent, and a property they work on. */
export const userPropertySchema = z.object({
  id: z.number().int(),
  is_active: z.boolean(),
  granted_by: z.number().int().nullable(),
  created_at: z.iso.datetime({ offset: true }),
  revoked_at: z.iso.datetime({ offset: true }).nullable(),
  revoked_by: z.number().int().nullable(),
  property: z.number().int(),
  property_name: z.string(),
});
export type UserProperty = z.infer<typeof userPropertySchema>;

/** A syndic and a syndicat they run (its properties, present and future). */
export const userSyndicatSchema = z.object({
  id: z.number().int(),
  is_active: z.boolean(),
  granted_by: z.number().int().nullable(),
  created_at: z.iso.datetime({ offset: true }),
  revoked_at: z.iso.datetime({ offset: true }).nullable(),
  revoked_by: z.number().int().nullable(),
  syndicat: z.number().int(),
  syndicat_name: z.string(),
});
export type UserSyndicat = z.infer<typeof userSyndicatSchema>;

export const accountCreateRequestSchema = z.object({
  email: z.email().min(1),
  first_name: z.string().min(1).max(150),
  last_name: z.string().min(1).max(150),
  phone: z.string().max(32).optional(),
  gender: genderSchema.optional(),
  preferred_language: preferredLanguageSchema.optional(),
  role: accountRoleSchema.optional(),
  /** Security, cleaning: buildings of the selected property. */
  building_ids: z.array(z.number().int().min(1)).optional(),
  /** Standard account: the units it owns. Required unless it rents one. */
  ownerships: z.array(accountOwnershipRequestSchema).optional(),
  /** Standard account: the unit it rents. Required unless it owns one. */
  tenancy: accountTenancyRequestSchema.nullable().optional(),
});
export type AccountCreateRequest = z.infer<typeof accountCreateRequestSchema>;

export const paginatedUserListSchema = paginated(userSchema);
export type PaginatedUserList = z.infer<typeof paginatedUserListSchema>;

/** Query parameters of GET /api/v1/users/ */
export const usersListQueryParamsSchema = z.object({
  include_inactive: z.boolean().optional(),
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
  q: z.string().max(120).optional(),
});
export type UsersListQueryParams = z.infer<typeof usersListQueryParamsSchema>;

/** Query parameters of GET /api/v1/users/{user_id}/building-assignments/ */
export const usersBuildingAssignmentsListQueryParamsSchema = z.object({
  include_revoked: z.boolean().optional(),
});
export type UsersBuildingAssignmentsListQueryParams = z.infer<
  typeof usersBuildingAssignmentsListQueryParamsSchema
>;

/** Query parameters of GET /api/v1/users/{user_id}/property-assignments/ */
export const usersPropertyAssignmentsListQueryParamsSchema = z.object({
  include_revoked: z.boolean().optional(),
});
export type UsersPropertyAssignmentsListQueryParams = z.infer<
  typeof usersPropertyAssignmentsListQueryParamsSchema
>;

/** Query parameters of GET /api/v1/users/{user_id}/syndicat-assignments/ */
export const usersSyndicatAssignmentsListQueryParamsSchema = z.object({
  include_revoked: z.boolean().optional(),
});
export type UsersSyndicatAssignmentsListQueryParams = z.infer<
  typeof usersSyndicatAssignmentsListQueryParamsSchema
>;

export const sessionCredentialsSchema = z.object({
  access_token: z.string().nullable(),
  refresh_token: z.string().nullable(),
});
export type SessionCredentials = z.infer<typeof sessionCredentialsSchema>;

/** The syndicat the client has selected. */
export const sessionSelectionSchema = z.object({
  id: z.number().int().nullable(),
  name: z.string().nullable(),
  logo_url: z.string().nullable(),
});
export type SessionSelection = z.infer<typeof sessionSelectionSchema>;

export const sessionFeaturesSchema = z.object({
  include_service_request: z.boolean(),
  include_announcements: z.boolean(),
  include_events: z.boolean(),
  include_amenities: z.boolean(),
  include_store: z.boolean(),
  include_library: z.boolean(),
  include_short_term_rental: z.boolean(),
  include_surveys: z.boolean(),
  include_marketplace: z.boolean(),
  include_visitor: z.boolean(),
  include_chat: z.boolean(),
});
export type SessionFeatures = z.infer<typeof sessionFeaturesSchema>;

/** The property the client has selected, with the modules enabled there. */
export const sessionPropertySchema = z.object({
  id: z.number().int().nullable(),
  name: z.string().nullable(),
  logo_url: z.string().nullable(),
  features: sessionFeaturesSchema,
});
export type SessionProperty = z.infer<typeof sessionPropertySchema>;

export const sessionUIConfigSchema = z.object({
  app_mode: sessionAppModeSchema.nullable(),
  step: uiConfigStepSchema.nullable(),
  syndicat: sessionSelectionSchema,
  property: sessionPropertySchema,
});
export type SessionUIConfig = z.infer<typeof sessionUIConfigSchema>;

/** The label of the account role, and one flag per role: only one is true. */
export const sessionRoleSchema = z.object({
  label: z.string().nullable(),
  is_admin: z.boolean(),
  is_syndic: z.boolean(),
  is_manager: z.boolean(),
  is_provider: z.boolean(),
  is_security: z.boolean(),
  is_cleaning: z.boolean(),
  is_standard: z.boolean(),
  is_maintenance: z.boolean(),
});
export type SessionRole = z.infer<typeof sessionRoleSchema>;

export const sessionUserStatusSchema = z.object({
  is_owner: z.boolean(),
  is_tenant: z.boolean(),
});
export type SessionUserStatus = z.infer<typeof sessionUserStatusSchema>;

export const sessionOwnershipSchema = z.object({
  unit_id: z.number().int().nullable(),
  unit_number: z.string().nullable(),
  ownership_share: z.string().nullable(),
});
export type SessionOwnership = z.infer<typeof sessionOwnershipSchema>;

export const sessionTenancySchema = z.object({
  lease_id: z.number().int().nullable(),
  unit_id: z.number().int().nullable(),
  unit_number: z.string().nullable(),
  is_signatory: z.boolean(),
});
export type SessionTenancy = z.infer<typeof sessionTenancySchema>;

export const sessionAssetsSchema = z.object({
  user_status: sessionUserStatusSchema,
  ownerships: z.array(sessionOwnershipSchema),
  tenancies: z.array(sessionTenancySchema),
});
export type SessionAssets = z.infer<typeof sessionAssetsSchema>;

export const sessionUserSchema = z.object({
  id: z.number().int().nullable(),
  email: z.string().nullable(),
  first_name: z.string().nullable(),
  last_name: z.string().nullable(),
  full_name: z.string().nullable(),
  phone: z.string().nullable(),
  gender: z.string().nullable(),
  preferred_language: z.string().nullable(),
  role: sessionRoleSchema,
  assets: sessionAssetsSchema,
});
export type SessionUser = z.infer<typeof sessionUserSchema>;

/**
 * What the client receives once logged in: credentials, UI configuration, user.
 * Values only the client can decide (app mode, step, selected syndicat and
 * property) are null, lists are empty.
 */
export const sessionContextSchema = z.object({
  credentials: sessionCredentialsSchema,
  ui_config: sessionUIConfigSchema,
  user: sessionUserSchema,
});
export type SessionContext = z.infer<typeof sessionContextSchema>;
