// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { prioritySchema, requesterNoticeSchema, serviceRequestCategorySchema, serviceStatusSchema } from "./enums";
import { attachmentSchema, paginated, uploadFileSchema, userSummarySchema } from "./shared";

export const serviceRequestSchema = z.object({
  id: z.number().int(),
  property: z.number().int(),
  /** Empty when the request concerns common areas. */
  unit: z.number().int().nullable(),
  requester: userSummarySchema,
  title: z.string(),
  description: z.string(),
  category: serviceRequestCategorySchema,
  priority: prioritySchema,
  status: serviceStatusSchema,
  current_round: z.number().int(),
  resolved_at: z.iso.datetime({ offset: true }).nullable(),
  closed_at: z.iso.datetime({ offset: true }).nullable(),
  cancelled_at: z.iso.datetime({ offset: true }).nullable(),
  cancellation_reason: z.string(),
  files: z.array(attachmentSchema),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type ServiceRequest = z.infer<typeof serviceRequestSchema>;

export const serviceRequestAssignRequestSchema = z.object({
  resolver_ids: z.array(z.number().int().min(1)).max(10),
});
export type ServiceRequestAssignRequest = z.infer<typeof serviceRequestAssignRequestSchema>;

export const serviceRequestAssignmentSchema = z.object({
  id: z.number().int(),
  resolver: userSummarySchema,
  resolution_round: z.number().int(),
  assigned_by: z.number().int().nullable(),
  is_resolved: z.boolean(),
  resolved_at: z.iso.datetime({ offset: true }).nullable(),
  resolution_note: z.string(),
  resolution_media: z.array(attachmentSchema),
  requester_notice: requesterNoticeSchema.nullable(),
  requester_rating: z.number().int().nullable(),
  requester_comment: z.string(),
  feedback_at: z.iso.datetime({ offset: true }).nullable(),
  created_at: z.iso.datetime({ offset: true }),
});
export type ServiceRequestAssignment = z.infer<typeof serviceRequestAssignmentSchema>;

export const serviceRequestCreateRequestSchema = z.object({
  unit_id: z.number().int().min(1).nullable().optional(),
  title: z.string().min(1).max(200),
  description: z.string().min(1),
  category: serviceRequestCategorySchema.optional(),
  priority: prioritySchema.optional(),
  files: z.array(uploadFileSchema).optional(),
});
export type ServiceRequestCreateRequest = z.infer<typeof serviceRequestCreateRequestSchema>;

export const serviceRequestFeedbackRequestSchema = z.object({
  notice: requesterNoticeSchema,
  rating: z.number().int().min(1).max(5).nullable().optional(),
  comment: z.string().max(2000).optional(),
});
export type ServiceRequestFeedbackRequest = z.infer<typeof serviceRequestFeedbackRequestSchema>;

export const serviceRequestResolveRequestSchema = z.object({
  note: z.string().optional(),
  files: z.array(uploadFileSchema).optional(),
});
export type ServiceRequestResolveRequest = z.infer<typeof serviceRequestResolveRequestSchema>;

export const paginatedServiceRequestListSchema = paginated(serviceRequestSchema);
export type PaginatedServiceRequestList = z.infer<typeof paginatedServiceRequestListSchema>;

/** Query parameters of GET /api/v1/service-requests/ */
export const serviceRequestsListQueryParamsSchema = z.object({
  mine: z.boolean().optional(),
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
  status: serviceStatusSchema.optional(),
});
export type ServiceRequestsListQueryParams = z.infer<typeof serviceRequestsListQueryParamsSchema>;
