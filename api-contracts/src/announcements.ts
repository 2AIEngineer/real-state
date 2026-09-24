// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { announcementCategorySchema, announcementPrioritySchema, propertyRoleSchema } from "./enums";
import { attachmentSchema, paginated, uploadFileSchema, userSummarySchema } from "./shared";

export const announcementSchema = z.object({
  id: z.number().int(),
  property: z.number().int(),
  /** Optional narrowing of the target roles to one building. */
  building: z.number().int().nullable(),
  title: z.string(),
  body: z.string(),
  category: announcementCategorySchema,
  priority: announcementPrioritySchema,
  target_roles: z.array(propertyRoleSchema),
  published_at: z.iso.datetime({ offset: true }),
  expires_at: z.iso.datetime({ offset: true }).nullable(),
  created_by: userSummarySchema,
  files: z.array(attachmentSchema),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type Announcement = z.infer<typeof announcementSchema>;

export const announcementCreateRequestSchema = z.object({
  building_id: z.number().int().min(1).nullable().optional(),
  title: z.string().min(1).max(200),
  body: z.string().min(1),
  category: announcementCategorySchema.optional(),
  priority: announcementPrioritySchema.optional(),
  target_roles: z.array(propertyRoleSchema),
  published_at: z.iso.datetime({ offset: true }).nullable().optional(),
  expires_at: z.iso.datetime({ offset: true }).nullable().optional(),
  files: z.array(uploadFileSchema).optional(),
});
export type AnnouncementCreateRequest = z.infer<typeof announcementCreateRequestSchema>;

export const paginatedAnnouncementListSchema = paginated(announcementSchema);
export type PaginatedAnnouncementList = z.infer<typeof paginatedAnnouncementListSchema>;

export const patchedAnnouncementRequestSchema = z.object({
  title: z.string().min(1).max(200).optional(),
  body: z.string().min(1).optional(),
  category: announcementCategorySchema.optional(),
  priority: announcementPrioritySchema.optional(),
  expires_at: z.iso.datetime({ offset: true }).nullable().optional(),
});
export type PatchedAnnouncementRequest = z.infer<typeof patchedAnnouncementRequestSchema>;

/** Query parameters of GET /api/v1/announcements/ */
export const announcementsListQueryParamsSchema = z.object({
  category: announcementCategorySchema.optional(),
  include_expired: z.boolean().optional(),
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
});
export type AnnouncementsListQueryParams = z.infer<typeof announcementsListQueryParamsSchema>;
