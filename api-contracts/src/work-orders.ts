// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { prioritySchema, workOrderActionSchema, workOrderCategorySchema, workOrderStatusSchema } from "./enums";
import { attachmentSchema, paginated, uploadFileSchema, userSummarySchema } from "./shared";

export const patchedWorkOrderRequestSchema = z.object({
  description: z.string().optional(),
  category: workOrderCategorySchema.optional(),
  priority: prioritySchema.optional(),
  scheduled_start: z.iso.datetime({ offset: true }).nullable().optional(),
  scheduled_end: z.iso.datetime({ offset: true }).nullable().optional(),
  due_date: z.iso.date().nullable().optional(),
  title: z.string().min(1).max(200).optional(),
  assignee_id: z.number().int().min(1).nullable().optional(),
});
export type PatchedWorkOrderRequest = z.infer<typeof patchedWorkOrderRequestSchema>;

export const workOrderSchema = z.object({
  id: z.number().int(),
  property: z.number().int(),
  building: z.number().int().nullable(),
  unit: z.number().int().nullable(),
  service_request: z.number().int().nullable(),
  title: z.string(),
  description: z.string(),
  category: workOrderCategorySchema,
  priority: prioritySchema,
  status: workOrderStatusSchema,
  assignee: userSummarySchema.nullable(),
  scheduled_start: z.iso.datetime({ offset: true }).nullable(),
  scheduled_end: z.iso.datetime({ offset: true }).nullable(),
  due_date: z.iso.date().nullable(),
  started_at: z.iso.datetime({ offset: true }).nullable(),
  completed_at: z.iso.datetime({ offset: true }).nullable(),
  completion_note: z.string(),
  cancelled_at: z.iso.datetime({ offset: true }).nullable(),
  cancellation_reason: z.string(),
  files: z.array(attachmentSchema),
  created_by: z.number().int().nullable(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type WorkOrder = z.infer<typeof workOrderSchema>;

export const workOrderCreateRequestSchema = z.object({
  description: z.string().optional(),
  category: workOrderCategorySchema.optional(),
  priority: prioritySchema.optional(),
  scheduled_start: z.iso.datetime({ offset: true }).nullable().optional(),
  scheduled_end: z.iso.datetime({ offset: true }).nullable().optional(),
  due_date: z.iso.date().nullable().optional(),
  building_id: z.number().int().min(1).nullable().optional(),
  unit_id: z.number().int().min(1).nullable().optional(),
  service_request_id: z.number().int().min(1).nullable().optional(),
  assignee_id: z.number().int().min(1).nullable().optional(),
  title: z.string().min(1).max(200),
  files: z.array(uploadFileSchema).optional(),
});
export type WorkOrderCreateRequest = z.infer<typeof workOrderCreateRequestSchema>;

export const workOrderTransitionRequestSchema = z.object({
  action: workOrderActionSchema,
  note: z.string().max(4000).optional(),
});
export type WorkOrderTransitionRequest = z.infer<typeof workOrderTransitionRequestSchema>;

export const paginatedWorkOrderListSchema = paginated(workOrderSchema);
export type PaginatedWorkOrderList = z.infer<typeof paginatedWorkOrderListSchema>;

/** Query parameters of GET /api/v1/work-orders/ */
export const workOrdersListQueryParamsSchema = z.object({
  assigned_to_me: z.boolean().optional(),
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
  status: workOrderStatusSchema.optional(),
});
export type WorkOrdersListQueryParams = z.infer<typeof workOrdersListQueryParamsSchema>;
