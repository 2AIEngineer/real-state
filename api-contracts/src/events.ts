// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { eventStatusSchema, propertyRoleSchema } from "./enums";
import { attachmentSchema, paginated, uploadFileSchema, userSummarySchema } from "./shared";

export const eventSchema = z.object({
  id: z.number().int(),
  property: z.number().int(),
  building: z.number().int().nullable(),
  title: z.string(),
  description: z.string(),
  location: z.string(),
  start_at: z.iso.datetime({ offset: true }),
  end_at: z.iso.datetime({ offset: true }),
  status: eventStatusSchema,
  target_roles: z.array(propertyRoleSchema),
  cancelled_at: z.iso.datetime({ offset: true }).nullable(),
  cancellation_reason: z.string(),
  completed_at: z.iso.datetime({ offset: true }).nullable(),
  created_by: userSummarySchema,
  files: z.array(attachmentSchema),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type Event = z.infer<typeof eventSchema>;

export const eventCreateRequestSchema = z.object({
  building_id: z.number().int().min(1).nullable().optional(),
  title: z.string().min(1).max(200),
  description: z.string().optional(),
  location: z.string().max(200).optional(),
  start_at: z.iso.datetime({ offset: true }),
  end_at: z.iso.datetime({ offset: true }),
  target_roles: z.array(propertyRoleSchema),
  files: z.array(uploadFileSchema).optional(),
});
export type EventCreateRequest = z.infer<typeof eventCreateRequestSchema>;

export const paginatedEventListSchema = paginated(eventSchema);
export type PaginatedEventList = z.infer<typeof paginatedEventListSchema>;

export const patchedEventRequestSchema = z.object({
  title: z.string().min(1).max(200).optional(),
  description: z.string().optional(),
  location: z.string().max(200).optional(),
  start_at: z.iso.datetime({ offset: true }).optional(),
  end_at: z.iso.datetime({ offset: true }).optional(),
});
export type PatchedEventRequest = z.infer<typeof patchedEventRequestSchema>;

/** Query parameters of GET /api/v1/events/ */
export const eventsListQueryParamsSchema = z.object({
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
  starts_after: z.iso.datetime({ offset: true }).optional(),
  starts_before: z.iso.datetime({ offset: true }).optional(),
  status: eventStatusSchema.optional(),
});
export type EventsListQueryParams = z.infer<typeof eventsListQueryParamsSchema>;
