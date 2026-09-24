// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { orderStatusSchema } from "./enums";
import { attachmentSchema, decimalString, paginated, userSummarySchema } from "./shared";

export const actionNoteRequestSchema = z.object({
  note: z.string().max(4000).optional(),
});
export type ActionNoteRequest = z.infer<typeof actionNoteRequestSchema>;

export const orderItemSchema = z.object({
  id: z.number().int(),
  product: z.number().int(),
  product_name: z.string(),
  unit_price: decimalString(/^-?\d{0,10}(?:\.\d{0,2})?$/),
  quantity: z.number().int(),
  line_total: decimalString(/^-?\d{0,10}(?:\.\d{0,2})?$/),
});
export type OrderItem = z.infer<typeof orderItemSchema>;

export const orderLineRequestSchema = z.object({
  product_id: z.number().int().min(1),
  quantity: z.number().int().min(1).max(1000),
});
export type OrderLineRequest = z.infer<typeof orderLineRequestSchema>;

export const patchedProductRequestSchema = z.object({
  description: z.string().optional(),
  category: z.string().max(80).optional(),
  sku: z.string().max(64).optional(),
  stock_quantity: z.number().int().min(0).optional(),
  is_active: z.boolean().optional(),
  name: z.string().min(1).max(160).optional(),
  price: decimalString(/^-?\d{0,10}(?:\.\d{0,2})?$/).optional(),
});
export type PatchedProductRequest = z.infer<typeof patchedProductRequestSchema>;

export const productSchema = z.object({
  id: z.number().int(),
  property: z.number().int(),
  name: z.string(),
  description: z.string(),
  category: z.string(),
  sku: z.string(),
  price: decimalString(/^-?\d{0,10}(?:\.\d{0,2})?$/),
  stock_quantity: z.number().int(),
  is_active: z.boolean(),
  images: z.array(attachmentSchema),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type Product = z.infer<typeof productSchema>;

export const productCreateRequestSchema = z.object({
  description: z.string().optional(),
  category: z.string().max(80).optional(),
  sku: z.string().max(64).optional(),
  stock_quantity: z.number().int().min(0).optional(),
  is_active: z.boolean().optional(),
  name: z.string().min(1).max(160),
  price: decimalString(/^-?\d{0,10}(?:\.\d{0,2})?$/),
});
export type ProductCreateRequest = z.infer<typeof productCreateRequestSchema>;

export const orderSchema = z.object({
  id: z.number().int(),
  property: z.number().int(),
  unit: z.number().int().nullable(),
  orderer: userSummarySchema,
  status: orderStatusSchema,
  total_amount: decimalString(/^-?\d{0,10}(?:\.\d{0,2})?$/),
  delivery_instructions: z.string(),
  customer_note: z.string(),
  staff_note: z.string(),
  items: z.array(orderItemSchema),
  confirmed_at: z.iso.datetime({ offset: true }).nullable(),
  delivered_at: z.iso.datetime({ offset: true }).nullable(),
  cancelled_at: z.iso.datetime({ offset: true }).nullable(),
  cancellation_reason: z.string(),
  created_at: z.iso.datetime({ offset: true }),
});
export type Order = z.infer<typeof orderSchema>;

export const orderCreateRequestSchema = z.object({
  unit_id: z.number().int().min(1).nullable().optional(),
  items: z.array(orderLineRequestSchema),
  delivery_instructions: z.string().max(1000).optional(),
  customer_note: z.string().max(1000).optional(),
});
export type OrderCreateRequest = z.infer<typeof orderCreateRequestSchema>;

export const paginatedOrderListSchema = paginated(orderSchema);
export type PaginatedOrderList = z.infer<typeof paginatedOrderListSchema>;

export const paginatedProductListSchema = paginated(productSchema);
export type PaginatedProductList = z.infer<typeof paginatedProductListSchema>;

/** Query parameters of GET /api/v1/store/orders/ */
export const storeOrdersListQueryParamsSchema = z.object({
  mine: z.boolean().optional(),
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
  status: orderStatusSchema.optional(),
});
export type StoreOrdersListQueryParams = z.infer<typeof storeOrdersListQueryParamsSchema>;

/** Query parameters of GET /api/v1/store/products/ */
export const storeProductsListQueryParamsSchema = z.object({
  include_inactive: z.boolean().optional(),
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
  search: z.string().max(80).optional(),
});
export type StoreProductsListQueryParams = z.infer<typeof storeProductsListQueryParamsSchema>;
