// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { listingCategorySchema, marketplaceListingStatusSchema } from "./enums";
import { attachmentSchema, decimalString, paginated, uploadFileSchema, userSummarySchema } from "./shared";

export const marketplaceListingSchema = z.object({
  id: z.number().int(),
  seller: userSummarySchema,
  property: z.number().int().nullable(),
  category: listingCategorySchema,
  title: z.string(),
  description: z.string(),
  price: decimalString(/^-?\d{0,12}(?:\.\d{0,2})?$/).nullable(),
  currency: z.string(),
  is_negotiable: z.boolean(),
  location: z.string(),
  contact_phone: z.string(),
  contact_email: z.union([z.email(), z.literal("")]),
  status: marketplaceListingStatusSchema,
  published_at: z.iso.datetime({ offset: true }),
  closed_at: z.iso.datetime({ offset: true }).nullable(),
  images: z.array(attachmentSchema),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type MarketplaceListing = z.infer<typeof marketplaceListingSchema>;

export const marketplaceListingCreateRequestSchema = z.object({
  price: decimalString(/^-?\d{0,12}(?:\.\d{0,2})?$/).nullable().optional(),
  currency: z.string().min(3).max(3).optional(),
  is_negotiable: z.boolean().optional(),
  location: z.string().max(200).optional(),
  contact_phone: z.string().max(32).optional(),
  contact_email: z.union([z.email(), z.literal("")]).optional(),
  category: listingCategorySchema,
  title: z.string().min(1).max(200),
  description: z.string().min(1),
  images: z.array(uploadFileSchema),
});
export type MarketplaceListingCreateRequest = z.infer<typeof marketplaceListingCreateRequestSchema>;

export const marketplaceListingImagesRequestSchema = z.object({
  images: z.array(uploadFileSchema),
});
export type MarketplaceListingImagesRequest = z.infer<typeof marketplaceListingImagesRequestSchema>;

export const marketplaceListingModerationRequestSchema = z.object({
  reason: z.string().min(1).max(2000),
});
export type MarketplaceListingModerationRequest = z.infer<typeof marketplaceListingModerationRequestSchema>;

export const paginatedMarketplaceListingListSchema = paginated(marketplaceListingSchema);
export type PaginatedMarketplaceListingList = z.infer<typeof paginatedMarketplaceListingListSchema>;

export const patchedMarketplaceListingRequestSchema = z.object({
  price: decimalString(/^-?\d{0,12}(?:\.\d{0,2})?$/).nullable().optional(),
  currency: z.string().min(3).max(3).optional(),
  is_negotiable: z.boolean().optional(),
  location: z.string().max(200).optional(),
  contact_phone: z.string().max(32).optional(),
  contact_email: z.union([z.email(), z.literal("")]).optional(),
  category: listingCategorySchema.optional(),
  title: z.string().min(1).max(200).optional(),
  description: z.string().min(1).optional(),
});
export type PatchedMarketplaceListingRequest = z.infer<typeof patchedMarketplaceListingRequestSchema>;

/** Query parameters of GET /api/v1/marketplace/listings/ */
export const marketplaceListingsListQueryParamsSchema = z.object({
  category: listingCategorySchema.optional(),
  max_price: decimalString(/^-?\d{0,12}(?:\.\d{0,2})?$/).optional(),
  mine: z.boolean().optional(),
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
  search: z.string().max(120).optional(),
  status: marketplaceListingStatusSchema.optional(),
});
export type MarketplaceListingsListQueryParams = z.infer<typeof marketplaceListingsListQueryParamsSchema>;
