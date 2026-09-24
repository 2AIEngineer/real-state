// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { entityTypeSchema } from "./enums";

// ------------------------------------------------------- building blocks

/** Error envelope returned by every failing request. */
export const apiErrorSchema = z.object({
  error: z.object({
    /** Stable machine code, see `knownErrorCodes`. */
    code: z.string(),
    /** Human-readable message (English). */
    message: z.string(),
    /** Input field the error is about, when there is one. */
    field: z.string().optional(),
    /** Extra data: validation errors per field, blocking records... */
    details: z.unknown().optional(),
  }),
});
export type ApiError = z.infer<typeof apiErrorSchema>;

/**
 * Steps of the UI configuration, sent in `X-UI-Config-Step`.
 * The client walks through them after logging in: it lists the syndicats it may
 * open (`syndicat`), then the properties of the one it chose (`property`, with
 * `X-Syndicat-Id`), then works in the dashboard (`dashboard`), where every call
 * carries `X-Syndicat-Id`, `X-Property-Id` and this header (see
 * `endpoints[...].uiConfigStep`).
 */
export const uiConfigSteps = ["logged_in", "syndicat", "property", "dashboard"] as const;

/**
 * Optional header of every POST: a value generated once per intended action
 * (`crypto.randomUUID()`) and reused on each retry of that action. A retry is
 * answered like the first request (header `Idempotent-Replayed: true`) instead
 * of creating a second record.
 */
export const IDEMPOTENCY_KEY_HEADER = "Idempotency-Key";
export type UIConfigStepName = (typeof uiConfigSteps)[number];

/** Error codes the backend can return (the list may grow: codes are strings). */
export const knownErrorCodes = [
  "active_assignments",
  "active_lease_member",
  "active_owner",
  "already_answered",
  "already_assigned",
  "already_member",
  "amenity_inactive",
  "assignment_required",
  "authentication_failed",
  "building_outside_property",
  "capacity_exceeded",
  "conflict",
  "email_taken",
  "feature_disabled",
  "folder_not_empty",
  "idempotency_key_reused",
  "insufficient_stock",
  "invalid",
  "invalid_password",
  "invalid_token",
  "invalid_transition",
  "last_active_member",
  "last_admin",
  "last_image",
  "last_member",
  "lease_already_started",
  "lease_overlap",
  "method_not_allowed",
  "name_taken",
  "no_question",
  "not_authenticated",
  "not_enough_options",
  "not_found",
  "number_taken",
  "outside_lease",
  "ownership_or_tenancy_required",
  "parse_error",
  "permission_denied",
  "primary_member",
  "product_unavailable",
  "promoter_default",
  "promoter_held",
  "property_inactive",
  "property_outside_syndicat",
  "reference_taken",
  "request_in_progress",
  "resource_in_use",
  "role_takes_no_assignment",
  "role_takes_no_unit",
  "rule_violation",
  "security_single_property",
  "selection_required",
  "server_error",
  "short_term_rental_overlap",
  "slot_unavailable",
  "survey_has_responses",
  "system_folder",
  "throttled",
  "token_not_valid",
  "unit_has_leases",
  "unit_has_ownership_history",
  "unit_leased",
  "unsupported_media_type",
  "weak_password",
  "wrong_ui_config_step",
] as const;
export type KnownErrorCode = (typeof knownErrorCodes)[number];

/** Page of results returned by every list endpoint. */
export const paginated = <T extends z.ZodTypeAny>(item: T) =>
  z.object({
    count: z.number().int(),
    next: z.url().nullable().optional(),
    previous: z.url().nullable().optional(),
    results: z.array(item),
  });
export type Paginated<T> = {
  count: number;
  next?: string | null;
  previous?: string | null;
  results: T[];
};

/** A file picked by the user, sent as multipart/form-data. */
export const uploadFileSchema = z.custom<Blob>(
  (value) => typeof Blob !== "undefined" && value instanceof Blob,
  "Expected a file",
);

/** Decimal numbers travel as strings to keep their precision ("12.50"). */
export const decimalString = (pattern: RegExp) => z.string().regex(pattern);

// --------------------------------------------- schemas used by several domains

export const actionReasonRequestSchema = z.object({
  reason: z.string().max(2000).optional(),
});
export type ActionReasonRequest = z.infer<typeof actionReasonRequestSchema>;

/**
 * A stored file with a ready-to-use URL: use it as is (`<img src>`, `<iframe>`,
 * a link), no header and no extra call. Public files (logos, catalogue photos)
 * have a permanent URL; private ones a personal URL valid for 12 to 24 hours,
 * renewed in every API response.
 */
export const attachmentSchema = z.object({
  id: z.number().int(),
  entity_type: entityTypeSchema,
  entity_id: z.number().int(),
  /** Signed link to the file (see above). */
  url: z.string(),
  original_filename: z.string(),
  mime_type: z.string(),
  /** Bytes. */
  size: z.number().int(),
  checksum_sha256: z.string(),
  position: z.number().int(),
  uploaded_by: z.number().int(),
  created_at: z.iso.datetime({ offset: true }),
});
export type Attachment = z.infer<typeof attachmentSchema>;

export const patchedUploadFileRequestSchema = z.object({
  file: uploadFileSchema.optional(),
});
export type PatchedUploadFileRequest = z.infer<typeof patchedUploadFileRequestSchema>;

export const uploadFilesRequestSchema = z.object({
  files: z.array(uploadFileSchema),
});
export type UploadFilesRequest = z.infer<typeof uploadFilesRequestSchema>;

export const userSummarySchema = z.object({
  id: z.number().int(),
  full_name: z.string(),
  email: z.union([z.email(), z.literal("")]),
});
export type UserSummary = z.infer<typeof userSummarySchema>;
