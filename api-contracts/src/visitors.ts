// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { visitorStatusSchema } from "./enums";
import { attachmentSchema, paginated, uploadFileSchema, userSummarySchema } from "./shared";

export const patchedVisitorRequestSchema = z.object({
  phone: z.string().max(32).optional(),
  visit_reason: z.string().max(200).optional(),
  vehicle_plate: z.string().max(32).optional(),
  notes: z.string().optional(),
});
export type PatchedVisitorRequest = z.infer<typeof patchedVisitorRequestSchema>;

export const visitorSchema = z.object({
  id: z.number().int(),
  property: z.number().int(),
  unit: z.number().int(),
  first_name: z.string(),
  last_name: z.string(),
  phone: z.string(),
  visit_reason: z.string(),
  vehicle_plate: z.string(),
  status: visitorStatusSchema,
  arrived_at: z.iso.datetime({ offset: true }).nullable(),
  left_at: z.iso.datetime({ offset: true }).nullable(),
  denial_reason: z.string(),
  notes: z.string(),
  registered_by: userSummarySchema,
  id_card: attachmentSchema.nullable(),
  created_at: z.iso.datetime({ offset: true }),
});
export type Visitor = z.infer<typeof visitorSchema>;

export const visitorCreateRequestSchema = z.object({
  phone: z.string().max(32).optional(),
  visit_reason: z.string().max(200).optional(),
  vehicle_plate: z.string().max(32).optional(),
  notes: z.string().optional(),
  unit_id: z.number().int().min(1),
  first_name: z.string().min(1).max(120),
  last_name: z.string().min(1).max(120),
  admitted: z.boolean().optional(),
  denial_reason: z.string().max(2000).optional(),
  id_card: uploadFileSchema.nullable().optional(),
});
export type VisitorCreateRequest = z.infer<typeof visitorCreateRequestSchema>;

export const visitorDepartureRequestSchema = z.object({
  left_at: z.iso.datetime({ offset: true }).nullable().optional(),
});
export type VisitorDepartureRequest = z.infer<typeof visitorDepartureRequestSchema>;

export const paginatedVisitorListSchema = paginated(visitorSchema);
export type PaginatedVisitorList = z.infer<typeof paginatedVisitorListSchema>;

/** Query parameters of GET /api/v1/visitors/ */
export const visitorsListQueryParamsSchema = z.object({
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
  since: z.iso.datetime({ offset: true }).optional(),
  status: visitorStatusSchema.optional(),
  unit_id: z.number().int().min(1).optional(),
});
export type VisitorsListQueryParams = z.infer<typeof visitorsListQueryParamsSchema>;
