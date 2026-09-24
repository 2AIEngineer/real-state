// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { genderSchema, initiatorCapacitySchema, shortTermRentalStatusSchema } from "./enums";
import { attachmentSchema, paginated, userSummarySchema } from "./shared";

export const patchedShortTermRentalMemberRequestSchema = z.object({
  first_name: z.string().min(1).max(120).optional(),
  last_name: z.string().min(1).max(120).optional(),
  gender: genderSchema.optional(),
  date_of_birth: z.iso.date().nullable().optional(),
  nationality: z.string().max(80).optional(),
  id_document_number: z.string().max(64).optional(),
  phone: z.string().max(32).optional(),
  email: z.union([z.email(), z.literal("")]).optional(),
  make_primary: z.boolean().optional(),
});
export type PatchedShortTermRentalMemberRequest = z.infer<typeof patchedShortTermRentalMemberRequestSchema>;

export const shortTermRentalMemberSchema = z.object({
  id: z.number().int(),
  short_term_rental: z.number().int(),
  first_name: z.string(),
  last_name: z.string(),
  gender: genderSchema,
  date_of_birth: z.iso.date().nullable(),
  nationality: z.string(),
  id_document_number: z.string(),
  phone: z.string(),
  email: z.union([z.email(), z.literal("")]),
  id_card: attachmentSchema.nullable(),
  created_at: z.iso.datetime({ offset: true }),
});
export type ShortTermRentalMember = z.infer<typeof shortTermRentalMemberSchema>;

export const shortTermRentalMemberCreateRequestSchema = z.object({
  first_name: z.string().min(1).max(120),
  last_name: z.string().min(1).max(120),
  gender: genderSchema.optional(),
  date_of_birth: z.iso.date().nullable().optional(),
  nationality: z.string().max(80).optional(),
  id_document_number: z.string().max(64).optional(),
  phone: z.string().max(32).optional(),
  email: z.union([z.email(), z.literal("")]).optional(),
  make_primary: z.boolean().optional(),
});
export type ShortTermRentalMemberCreateRequest = z.infer<typeof shortTermRentalMemberCreateRequestSchema>;

export const shortTermRentalMemberInputRequestSchema = z.object({
  first_name: z.string().min(1).max(120),
  last_name: z.string().min(1).max(120),
  gender: genderSchema.optional(),
  date_of_birth: z.iso.date().nullable().optional(),
  nationality: z.string().max(80).optional(),
  id_document_number: z.string().max(64).optional(),
  phone: z.string().max(32).optional(),
  email: z.union([z.email(), z.literal("")]).optional(),
});
export type ShortTermRentalMemberInputRequest = z.infer<typeof shortTermRentalMemberInputRequestSchema>;

export const shortTermRentalRescheduleRequestSchema = z.object({
  checkin_date: z.iso.date(),
  checkout_date: z.iso.date(),
});
export type ShortTermRentalRescheduleRequest = z.infer<typeof shortTermRentalRescheduleRequestSchema>;

export const shortTermRentalSchema = z.object({
  id: z.number().int(),
  unit: z.number().int(),
  initiated_by: userSummarySchema,
  initiator_capacity: initiatorCapacitySchema,
  /** Lease bounding the rental when declared by a tenant. */
  lease: z.number().int().nullable(),
  checkin_date: z.iso.date(),
  checkout_date: z.iso.date(),
  status: shortTermRentalStatusSchema,
  primary_member: z.number().int().nullable(),
  members: z.array(shortTermRentalMemberSchema),
  notes: z.string(),
  checked_in_at: z.iso.datetime({ offset: true }).nullable(),
  completed_at: z.iso.datetime({ offset: true }).nullable(),
  cancelled_at: z.iso.datetime({ offset: true }).nullable(),
  cancellation_reason: z.string(),
  created_at: z.iso.datetime({ offset: true }),
});
export type ShortTermRental = z.infer<typeof shortTermRentalSchema>;

export const shortTermRentalCreateRequestSchema = z.object({
  unit_id: z.number().int().min(1),
  checkin_date: z.iso.date(),
  checkout_date: z.iso.date(),
  notes: z.string().max(2000).optional(),
  members: z.array(shortTermRentalMemberInputRequestSchema),
  primary_index: z.number().int().min(0).optional(),
});
export type ShortTermRentalCreateRequest = z.infer<typeof shortTermRentalCreateRequestSchema>;

export const paginatedShortTermRentalListSchema = paginated(shortTermRentalSchema);
export type PaginatedShortTermRentalList = z.infer<typeof paginatedShortTermRentalListSchema>;

/** Query parameters of GET /api/v1/short-term-rentals/ */
export const shortTermRentalsListQueryParamsSchema = z.object({
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
  status: shortTermRentalStatusSchema.optional(),
  unit_id: z.number().int().min(1).optional(),
});
export type ShortTermRentalsListQueryParams = z.infer<typeof shortTermRentalsListQueryParamsSchema>;
