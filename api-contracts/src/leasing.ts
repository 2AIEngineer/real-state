// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { checkPhaseSchema, componentConditionSchema, leaseStatusSchema, leaseTerminationReasonSchema } from "./enums";
import { attachmentSchema, paginated, uploadFileSchema, userSummarySchema } from "./shared";

export const leaseComponentStateSchema = z.object({
  id: z.number().int(),
  lease: z.number().int(),
  name: z.string(),
  description: z.string(),
  state: componentConditionSchema,
  on_check: checkPhaseSchema,
  on_check_date: z.iso.date(),
  recorded_by: z.number().int().nullable(),
  files: z.array(attachmentSchema),
  created_at: z.iso.datetime({ offset: true }),
});
export type LeaseComponentState = z.infer<typeof leaseComponentStateSchema>;

export const leaseComponentStateInputRequestSchema = z.object({
  name: z.string().min(1).max(120),
  description: z.string().optional(),
  state: componentConditionSchema,
  on_check: checkPhaseSchema,
  on_check_date: z.iso.date(),
  files: z.array(uploadFileSchema).optional(),
});
export type LeaseComponentStateInputRequest = z.infer<typeof leaseComponentStateInputRequestSchema>;

export const leaseMemberSchema = z.object({
  id: z.number().int(),
  lease: z.number().int(),
  user: userSummarySchema,
  joined_at: z.iso.date(),
  left_at: z.iso.date().nullable(),
  is_active: z.boolean(),
  is_signatory: z.boolean(),
  emergency_contact_name: z.string(),
  emergency_contact_phone: z.string(),
  emergency_contact_relation: z.string(),
  vehicles_info: z.unknown(),
  pets_info: z.unknown(),
  proof_of_identity: attachmentSchema.nullable(),
  proof_of_address: attachmentSchema.nullable(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type LeaseMember = z.infer<typeof leaseMemberSchema>;

export const leaseMemberDepartureRequestSchema = z.object({
  left_at: z.iso.date(),
});
export type LeaseMemberDepartureRequest = z.infer<typeof leaseMemberDepartureRequestSchema>;

export const leaseMemberPetRequestSchema = z.object({
  name: z.string().min(1).max(60),
  species: z.string().min(1).max(60),
  breed: z.string().max(60).optional(),
});
export type LeaseMemberPetRequest = z.infer<typeof leaseMemberPetRequestSchema>;

export const leaseMemberVehicleRequestSchema = z.object({
  plate_number: z.string().min(1).max(32),
  make: z.string().max(60).optional(),
  model: z.string().max(60).optional(),
  color: z.string().max(30).optional(),
  parking_spot: z.string().max(30).optional(),
});
export type LeaseMemberVehicleRequest = z.infer<typeof leaseMemberVehicleRequestSchema>;

export const leaseTerminationRequestSchema = z.object({
  effective_date: z.iso.date(),
  reason: leaseTerminationReasonSchema.optional(),
});
export type LeaseTerminationRequest = z.infer<typeof leaseTerminationRequestSchema>;

export const paginatedLeaseComponentStateListSchema = paginated(leaseComponentStateSchema);
export type PaginatedLeaseComponentStateList = z.infer<typeof paginatedLeaseComponentStateListSchema>;

export const patchedLeaseComponentStateRequestSchema = z.object({
  name: z.string().min(1).max(120).optional(),
  description: z.string().optional(),
  state: componentConditionSchema.optional(),
  on_check_date: z.iso.date().optional(),
});
export type PatchedLeaseComponentStateRequest = z.infer<typeof patchedLeaseComponentStateRequestSchema>;

export const patchedLeaseMemberRequestSchema = z.object({
  emergency_contact_name: z.string().max(200).optional(),
  emergency_contact_phone: z.string().max(32).optional(),
  emergency_contact_relation: z.string().max(80).optional(),
  vehicles_info: z.array(leaseMemberVehicleRequestSchema).optional(),
  pets_info: z.array(leaseMemberPetRequestSchema).optional(),
  is_signatory: z.boolean().optional(),
});
export type PatchedLeaseMemberRequest = z.infer<typeof patchedLeaseMemberRequestSchema>;

export const patchedLeaseRequestSchema = z.object({
  end_date: z.iso.date().nullable().optional(),
  contract_reference: z.string().max(120).nullable().optional(),
  notes: z.string().optional(),
});
export type PatchedLeaseRequest = z.infer<typeof patchedLeaseRequestSchema>;

export const leaseSchema = z.object({
  id: z.number().int(),
  unit: z.number().int(),
  property: z.number().int(),
  start_date: z.iso.date(),
  /** NULL = open-ended / tacit renewal. */
  end_date: z.iso.date().nullable(),
  status: leaseStatusSchema,
  contract_reference: z.string().nullable(),
  notes: z.string(),
  terminated_on: z.iso.date().nullable(),
  termination_reason: z.union([leaseTerminationReasonSchema, z.literal("")]),
  cancelled_at: z.iso.datetime({ offset: true }).nullable(),
  cancellation_reason: z.string(),
  members: z.array(leaseMemberSchema),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type Lease = z.infer<typeof leaseSchema>;

export const leaseMemberInputRequestSchema = z.object({
  emergency_contact_name: z.string().max(200).optional(),
  emergency_contact_phone: z.string().max(32).optional(),
  emergency_contact_relation: z.string().max(80).optional(),
  vehicles_info: z.array(leaseMemberVehicleRequestSchema).optional(),
  pets_info: z.array(leaseMemberPetRequestSchema).optional(),
  user_id: z.number().int().min(1),
  is_signatory: z.boolean().optional(),
  joined_at: z.iso.date().nullable().optional(),
});
export type LeaseMemberInputRequest = z.infer<typeof leaseMemberInputRequestSchema>;

export const paginatedLeaseListSchema = paginated(leaseSchema);
export type PaginatedLeaseList = z.infer<typeof paginatedLeaseListSchema>;

export const leaseCreateRequestSchema = z.object({
  unit_id: z.number().int().min(1),
  start_date: z.iso.date(),
  end_date: z.iso.date().nullable().optional(),
  contract_reference: z.string().max(120).nullable().optional(),
  notes: z.string().optional(),
  members: z.array(leaseMemberInputRequestSchema),
});
export type LeaseCreateRequest = z.infer<typeof leaseCreateRequestSchema>;

/** Query parameters of GET /api/v1/leases/ */
export const leasesListQueryParamsSchema = z.object({
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
  status: leaseStatusSchema.optional(),
  unit_id: z.number().int().min(1).optional(),
});
export type LeasesListQueryParams = z.infer<typeof leasesListQueryParamsSchema>;

/** Query parameters of GET /api/v1/leases/{lease_id}/lease-component-states/ */
export const leasesLeaseComponentStatesListQueryParamsSchema = z.object({
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
});
export type LeasesLeaseComponentStatesListQueryParams = z.infer<typeof leasesLeaseComponentStatesListQueryParamsSchema>;
