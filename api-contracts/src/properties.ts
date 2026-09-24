// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { endReasonSchema, ownershipEndReasonSchema, ownershipStatusSchema, unitTypeSchema } from "./enums";
import { attachmentSchema, decimalString, paginated, userSummarySchema } from "./shared";

export const buildingSchema = z.object({
  id: z.number().int(),
  property: z.number().int(),
  name: z.string(),
  address: z.string(),
  floors_count: z.number().int().nullable(),
  description: z.string(),
  units_count: z.number().int(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type Building = z.infer<typeof buildingSchema>;

export const buildingInputRequestSchema = z.object({
  name: z.string().min(1).max(120),
  address: z.string().optional(),
  floors_count: z.number().int().min(0).nullable().optional(),
  description: z.string().optional(),
});
export type BuildingInputRequest = z.infer<typeof buildingInputRequestSchema>;

export const ownershipSchema = z.object({
  id: z.number().int(),
  unit: z.number().int(),
  owner: userSummarySchema,
  ownership_share: decimalString(/^-?\d{0,3}(?:\.\d{0,2})?$/).nullable(),
  start_date: z.iso.date(),
  end_date: z.iso.date().nullable(),
  status: ownershipStatusSchema,
  /** Automatic ownership held by the property's promoter. */
  is_promoter_default: z.boolean(),
  end_reason: z.union([endReasonSchema, z.literal("")]),
  acquisition_reference: z.string(),
  created_at: z.iso.datetime({ offset: true }),
});
export type Ownership = z.infer<typeof ownershipSchema>;

export const ownershipAcquirerRequestSchema = z.object({
  user_id: z.number().int().min(1),
  share: decimalString(/^-?\d{0,3}(?:\.\d{0,2})?$/).nullable().optional(),
});
export type OwnershipAcquirerRequest = z.infer<typeof ownershipAcquirerRequestSchema>;

export const ownershipCoOwnerRequestSchema = z.object({
  user_id: z.number().int().min(1),
  share: decimalString(/^-?\d{0,3}(?:\.\d{0,2})?$/).nullable().optional(),
  start_date: z.iso.date(),
});
export type OwnershipCoOwnerRequest = z.infer<typeof ownershipCoOwnerRequestSchema>;

export const ownershipEndRequestSchema = z.object({
  end_date: z.iso.date(),
  reason: ownershipEndReasonSchema.optional(),
});
export type OwnershipEndRequest = z.infer<typeof ownershipEndRequestSchema>;

export const ownershipTransferRequestSchema = z.object({
  acquirers: z.array(ownershipAcquirerRequestSchema),
  effective_date: z.iso.date(),
  reference: z.string().max(120).optional(),
});
export type OwnershipTransferRequest = z.infer<typeof ownershipTransferRequestSchema>;

export const paginatedBuildingListSchema = paginated(buildingSchema);
export type PaginatedBuildingList = z.infer<typeof paginatedBuildingListSchema>;

export const paginatedOwnershipListSchema = paginated(ownershipSchema);
export type PaginatedOwnershipList = z.infer<typeof paginatedOwnershipListSchema>;

export const patchedBuildingRequestSchema = z.object({
  name: z.string().min(1).max(120).optional(),
  address: z.string().optional(),
  floors_count: z.number().int().min(0).nullable().optional(),
  description: z.string().optional(),
});
export type PatchedBuildingRequest = z.infer<typeof patchedBuildingRequestSchema>;

export const patchedPromoterRequestSchema = z.object({
  name: z.string().min(1).max(200).optional(),
  legal_name: z.string().max(255).optional(),
  registration_number: z.string().max(64).optional(),
  contact_email: z.union([z.email(), z.literal("")]).optional(),
  contact_phone: z.string().max(32).optional(),
  address: z.string().optional(),
});
export type PatchedPromoterRequest = z.infer<typeof patchedPromoterRequestSchema>;

export const patchedPropertyFeaturesRequestSchema = z.object({
  service_request: z.boolean().optional(),
  announcements: z.boolean().optional(),
  events: z.boolean().optional(),
  amenities: z.boolean().optional(),
  store: z.boolean().optional(),
  library: z.boolean().optional(),
  short_term_rental: z.boolean().optional(),
  surveys: z.boolean().optional(),
  marketplace: z.boolean().optional(),
  visitor: z.boolean().optional(),
  chat: z.boolean().optional(),
});
export type PatchedPropertyFeaturesRequest = z.infer<typeof patchedPropertyFeaturesRequestSchema>;

export const patchedPropertyRequestSchema = z.object({
  name: z.string().min(1).max(200).optional(),
  description: z.string().optional(),
  address: z.string().optional(),
  city: z.string().max(120).optional(),
  country: z.string().max(120).optional(),
  contact_email: z.union([z.email(), z.literal("")]).optional(),
  contact_phone: z.string().max(32).optional(),
  /** IANA time zone ("Africa/Casablanca", "America/Montreal"): dates and clock times of the property are read in it. */
  timezone: z.string().max(64).optional(),
  is_active: z.boolean().optional(),
});
export type PatchedPropertyRequest = z.infer<typeof patchedPropertyRequestSchema>;

export const patchedSyndicatRequestSchema = z.object({
  name: z.string().min(1).max(200).optional(),
  legal_name: z.string().max(255).optional(),
  registration_number: z.string().max(64).optional(),
  contact_email: z.union([z.email(), z.literal("")]).optional(),
  contact_phone: z.string().max(32).optional(),
  address: z.string().optional(),
  city: z.string().max(120).optional(),
  country: z.string().max(120).optional(),
  is_active: z.boolean().optional(),
});
export type PatchedSyndicatRequest = z.infer<typeof patchedSyndicatRequestSchema>;

export const patchedUnitRequestSchema = z.object({
  number: z.string().min(1).max(32).optional(),
  label: z.string().max(120).optional(),
  floor: z.number().int().min(-20).max(300).nullable().optional(),
  unit_type: unitTypeSchema.optional(),
  area_sqm: decimalString(/^-?\d{0,6}(?:\.\d{0,2})?$/).nullable().optional(),
  rooms_count: z.number().int().min(0).nullable().optional(),
  notes: z.string().optional(),
});
export type PatchedUnitRequest = z.infer<typeof patchedUnitRequestSchema>;

export const promoterSchema = z.object({
  id: z.number().int(),
  name: z.string(),
  legal_name: z.string(),
  registration_number: z.string(),
  contact_email: z.union([z.email(), z.literal("")]),
  contact_phone: z.string(),
  address: z.string(),
  representative_user: userSummarySchema,
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type Promoter = z.infer<typeof promoterSchema>;

export const promoterChangeRequestSchema = z.object({
  promoter_id: z.number().int().min(1),
  effective_date: z.iso.date(),
});
export type PromoterChangeRequest = z.infer<typeof promoterChangeRequestSchema>;

export const promoterInputRequestSchema = z.object({
  name: z.string().min(1).max(200),
  representative_email: z.email().min(1),
  legal_name: z.string().max(255).optional(),
  registration_number: z.string().max(64).optional(),
  contact_email: z.union([z.email(), z.literal("")]).optional(),
  contact_phone: z.string().max(32).optional(),
  address: z.string().optional(),
});
export type PromoterInputRequest = z.infer<typeof promoterInputRequestSchema>;

export const propertySchema = z.object({
  id: z.number().int(),
  syndicat: z.number().int(),
  promoter: z.number().int(),
  name: z.string(),
  description: z.string(),
  address: z.string(),
  city: z.string(),
  country: z.string(),
  contact_email: z.union([z.email(), z.literal("")]),
  contact_phone: z.string(),
  /** IANA time zone ("Africa/Casablanca", "America/Montreal"): dates and clock times of the property are read in it. */
  timezone: z.string(),
  is_active: z.boolean(),
  features: z.record(z.string(), z.boolean()),
  logo: attachmentSchema.nullable(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type Property = z.infer<typeof propertySchema>;

export const propertyFeaturesRequestSchema = z.object({
  service_request: z.boolean().optional(),
  announcements: z.boolean().optional(),
  events: z.boolean().optional(),
  amenities: z.boolean().optional(),
  store: z.boolean().optional(),
  library: z.boolean().optional(),
  short_term_rental: z.boolean().optional(),
  surveys: z.boolean().optional(),
  marketplace: z.boolean().optional(),
  visitor: z.boolean().optional(),
  chat: z.boolean().optional(),
});
export type PropertyFeaturesRequest = z.infer<typeof propertyFeaturesRequestSchema>;

export const propertyInputRequestSchema = z.object({
  syndicat_id: z.number().int().min(1),
  promoter_id: z.number().int().min(1),
  name: z.string().min(1).max(200),
  description: z.string().optional(),
  address: z.string().optional(),
  city: z.string().max(120).optional(),
  country: z.string().max(120).optional(),
  contact_email: z.union([z.email(), z.literal("")]).optional(),
  contact_phone: z.string().max(32).optional(),
  /** IANA time zone ("Africa/Casablanca", "America/Montreal"): dates and clock times of the property are read in it. */
  timezone: z.string().max(64).optional(),
  features: propertyFeaturesRequestSchema.optional(),
});
export type PropertyInputRequest = z.infer<typeof propertyInputRequestSchema>;

export const propertyStatisticsSchema = z.object({
  buildings: z.number().int(),
  units: z.number().int(),
  units_leased: z.number().int(),
  units_held_by_promoter: z.number().int(),
});
export type PropertyStatistics = z.infer<typeof propertyStatisticsSchema>;

export const syndicatSchema = z.object({
  id: z.number().int(),
  name: z.string(),
  legal_name: z.string(),
  registration_number: z.string(),
  contact_email: z.union([z.email(), z.literal("")]),
  contact_phone: z.string(),
  address: z.string(),
  city: z.string(),
  country: z.string(),
  is_active: z.boolean(),
  logo: attachmentSchema.nullable(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type Syndicat = z.infer<typeof syndicatSchema>;

export const syndicatInputRequestSchema = z.object({
  name: z.string().min(1).max(200),
  legal_name: z.string().max(255).optional(),
  registration_number: z.string().max(64).optional(),
  contact_email: z.union([z.email(), z.literal("")]).optional(),
  contact_phone: z.string().max(32).optional(),
  address: z.string().optional(),
  city: z.string().max(120).optional(),
  country: z.string().max(120).optional(),
});
export type SyndicatInputRequest = z.infer<typeof syndicatInputRequestSchema>;

export const unitSchema = z.object({
  id: z.number().int(),
  building: z.number().int(),
  property: z.number().int(),
  number: z.string(),
  label: z.string(),
  floor: z.number().int().nullable(),
  unit_type: unitTypeSchema,
  area_sqm: decimalString(/^-?\d{0,6}(?:\.\d{0,2})?$/).nullable(),
  rooms_count: z.number().int().nullable(),
  notes: z.string(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type Unit = z.infer<typeof unitSchema>;

export const unitInputRequestSchema = z.object({
  number: z.string().min(1).max(32),
  label: z.string().max(120).optional(),
  floor: z.number().int().min(-20).max(300).nullable().optional(),
  unit_type: unitTypeSchema.optional(),
  area_sqm: decimalString(/^-?\d{0,6}(?:\.\d{0,2})?$/).nullable().optional(),
  rooms_count: z.number().int().min(0).nullable().optional(),
  notes: z.string().optional(),
});
export type UnitInputRequest = z.infer<typeof unitInputRequestSchema>;

export const paginatedPromoterListSchema = paginated(promoterSchema);
export type PaginatedPromoterList = z.infer<typeof paginatedPromoterListSchema>;

export const paginatedPropertyListSchema = paginated(propertySchema);
export type PaginatedPropertyList = z.infer<typeof paginatedPropertyListSchema>;

export const paginatedSyndicatListSchema = paginated(syndicatSchema);
export type PaginatedSyndicatList = z.infer<typeof paginatedSyndicatListSchema>;

export const paginatedUnitListSchema = paginated(unitSchema);
export type PaginatedUnitList = z.infer<typeof paginatedUnitListSchema>;

/** Query parameters of GET /api/v1/buildings/{building_id}/units/ */
export const buildingsUnitsListQueryParamsSchema = z.object({
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
});
export type BuildingsUnitsListQueryParams = z.infer<typeof buildingsUnitsListQueryParamsSchema>;

/** Query parameters of GET /api/v1/promoters/ */
export const promotersListQueryParamsSchema = z.object({
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
});
export type PromotersListQueryParams = z.infer<typeof promotersListQueryParamsSchema>;

/** Query parameters of GET /api/v1/properties/ */
export const propertiesListQueryParamsSchema = z.object({
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
});
export type PropertiesListQueryParams = z.infer<typeof propertiesListQueryParamsSchema>;

/** Query parameters of GET /api/v1/properties/{property_id}/buildings/ */
export const propertiesBuildingsListQueryParamsSchema = z.object({
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
});
export type PropertiesBuildingsListQueryParams = z.infer<typeof propertiesBuildingsListQueryParamsSchema>;

/** Query parameters of GET /api/v1/syndicats/ */
export const syndicatsListQueryParamsSchema = z.object({
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
});
export type SyndicatsListQueryParams = z.infer<typeof syndicatsListQueryParamsSchema>;

/** Query parameters of GET /api/v1/units/{unit_id}/ownerships/ */
export const unitsOwnershipsListQueryParamsSchema = z.object({
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
});
export type UnitsOwnershipsListQueryParams = z.infer<typeof unitsOwnershipsListQueryParamsSchema>;

/** Query parameters of GET /api/v1/units/mine/ */
export const unitsMineListQueryParamsSchema = z.object({
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
});
export type UnitsMineListQueryParams = z.infer<typeof unitsMineListQueryParamsSchema>;

/** Step `syndicat`: the syndicats the signed-in user may open. */
export const uiConfigSyndicatSchema = z.object({
  id: z.number().int(),
  name: z.string(),
  city: z.string(),
  country: z.string(),
  logo: attachmentSchema.nullable(),
  accessible_properties_count: z.number().int(),
});
export type UIConfigSyndicat = z.infer<typeof uiConfigSyndicatSchema>;

/** Step `property`: the properties reachable inside the chosen syndicat. */
export const uiConfigPropertySchema = z.object({
  id: z.number().int(),
  syndicat: z.number().int(),
  name: z.string(),
  city: z.string(),
  country: z.string(),
  logo: attachmentSchema.nullable(),
  features: z.record(z.string(), z.boolean()),
});
export type UIConfigProperty = z.infer<typeof uiConfigPropertySchema>;

/** Query parameters of GET /api/v1/ui-config/properties/ */
export const uiConfigPropertiesListQueryParamsSchema = z.object({
  search: z.string().max(120).optional(),
});
export type UIConfigPropertiesListQueryParams = z.infer<typeof uiConfigPropertiesListQueryParamsSchema>;

/** Query parameters of GET /api/v1/ui-config/syndicats/ */
export const uiConfigSyndicatsListQueryParamsSchema = z.object({
  search: z.string().max(120).optional(),
});
export type UIConfigSyndicatsListQueryParams = z.infer<typeof uiConfigSyndicatsListQueryParamsSchema>;
