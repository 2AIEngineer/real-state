// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { bookingModeSchema, bookingStatusSchema } from "./enums";
import { attachmentSchema, decimalString, paginated, userSummarySchema } from "./shared";

export const amenitySchema = z.object({
  id: z.number().int(),
  property: z.number().int(),
  building: z.number().int().nullable(),
  name: z.string(),
  description: z.string(),
  location: z.string(),
  rules: z.string(),
  booking_mode: bookingModeSchema,
  capacity: z.number().int(),
  requires_approval: z.boolean(),
  opening_time: z.iso.time().nullable(),
  closing_time: z.iso.time().nullable(),
  min_duration_minutes: z.number().int(),
  max_duration_minutes: z.number().int(),
  max_advance_days: z.number().int(),
  /** Flat fee per booking. */
  fee: decimalString(/^-?\d{0,10}(?:\.\d{0,2})?$/),
  /** Security cost charged per booking. */
  security_fee: decimalString(/^-?\d{0,10}(?:\.\d{0,2})?$/),
  /** Price per hour of use; 0 for a free amenity. */
  hourly_price: decimalString(/^-?\d{0,10}(?:\.\d{0,2})?$/),
  is_active: z.boolean(),
  images: z.array(attachmentSchema),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type Amenity = z.infer<typeof amenitySchema>;

export const amenityCreateRequestSchema = z.object({
  description: z.string().optional(),
  location: z.string().max(200).optional(),
  rules: z.string().optional(),
  booking_mode: bookingModeSchema.optional(),
  capacity: z.number().int().min(1).max(10000).optional(),
  requires_approval: z.boolean().optional(),
  opening_time: z.iso.time().nullable().optional(),
  closing_time: z.iso.time().nullable().optional(),
  min_duration_minutes: z.number().int().min(5).max(10080).optional(),
  max_duration_minutes: z.number().int().min(5).max(10080).optional(),
  max_advance_days: z.number().int().min(0).max(730).optional(),
  fee: decimalString(/^-?\d{0,10}(?:\.\d{0,2})?$/).optional(),
  security_fee: decimalString(/^-?\d{0,10}(?:\.\d{0,2})?$/).optional(),
  /** Leave out or 0 for a free amenity. */
  hourly_price: decimalString(/^-?\d{0,10}(?:\.\d{0,2})?$/).optional(),
  building_id: z.number().int().min(1).nullable().optional(),
  name: z.string().min(1).max(120),
});
export type AmenityCreateRequest = z.infer<typeof amenityCreateRequestSchema>;

/** Availability view: occupancy only, no personal data. */
export const amenitySlotSchema = z.object({
  start_datetime: z.iso.datetime({ offset: true }),
  end_datetime: z.iso.datetime({ offset: true }),
  status: bookingStatusSchema,
  party_size: z.number().int(),
});
export type AmenitySlot = z.infer<typeof amenitySlotSchema>;

export const bookingSchema = z.object({
  id: z.number().int(),
  amenity: z.number().int(),
  amenity_name: z.string(),
  booker: userSummarySchema,
  start_datetime: z.iso.datetime({ offset: true }),
  end_datetime: z.iso.datetime({ offset: true }),
  status: bookingStatusSchema,
  party_size: z.number().int(),
  booker_note: z.string(),
  decision_note: z.string(),
  decided_at: z.iso.datetime({ offset: true }).nullable(),
  cancelled_at: z.iso.datetime({ offset: true }).nullable(),
  cancellation_reason: z.string(),
  completed_at: z.iso.datetime({ offset: true }).nullable(),
  created_at: z.iso.datetime({ offset: true }),
});
export type Booking = z.infer<typeof bookingSchema>;

export const bookingCreateRequestSchema = z.object({
  amenity_id: z.number().int().min(1),
  start_datetime: z.iso.datetime({ offset: true }),
  end_datetime: z.iso.datetime({ offset: true }),
  party_size: z.number().int().min(1).optional(),
  note: z.string().max(2000).optional(),
});
export type BookingCreateRequest = z.infer<typeof bookingCreateRequestSchema>;

export const bookingDecisionRequestSchema = z.object({
  approve: z.boolean(),
  note: z.string().max(2000).optional(),
});
export type BookingDecisionRequest = z.infer<typeof bookingDecisionRequestSchema>;

export const paginatedAmenityListSchema = paginated(amenitySchema);
export type PaginatedAmenityList = z.infer<typeof paginatedAmenityListSchema>;

export const paginatedBookingListSchema = paginated(bookingSchema);
export type PaginatedBookingList = z.infer<typeof paginatedBookingListSchema>;

export const patchedAmenityRequestSchema = z.object({
  description: z.string().optional(),
  location: z.string().max(200).optional(),
  rules: z.string().optional(),
  booking_mode: bookingModeSchema.optional(),
  capacity: z.number().int().min(1).max(10000).optional(),
  requires_approval: z.boolean().optional(),
  opening_time: z.iso.time().nullable().optional(),
  closing_time: z.iso.time().nullable().optional(),
  min_duration_minutes: z.number().int().min(5).max(10080).optional(),
  max_duration_minutes: z.number().int().min(5).max(10080).optional(),
  max_advance_days: z.number().int().min(0).max(730).optional(),
  fee: decimalString(/^-?\d{0,10}(?:\.\d{0,2})?$/).optional(),
  security_fee: decimalString(/^-?\d{0,10}(?:\.\d{0,2})?$/).optional(),
  /** Leave out or 0 for a free amenity. */
  hourly_price: decimalString(/^-?\d{0,10}(?:\.\d{0,2})?$/).optional(),
  name: z.string().min(1).max(120).optional(),
  is_active: z.boolean().optional(),
});
export type PatchedAmenityRequest = z.infer<typeof patchedAmenityRequestSchema>;

/** Query parameters of GET /api/v1/amenities/ */
export const amenitiesListQueryParamsSchema = z.object({
  include_inactive: z.boolean().optional(),
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
});
export type AmenitiesListQueryParams = z.infer<typeof amenitiesListQueryParamsSchema>;

/** Query parameters of GET /api/v1/amenities/{amenity_id}/schedule/ */
export const amenitiesScheduleListQueryParamsSchema = z.object({
  end: z.iso.datetime({ offset: true }),
  start: z.iso.datetime({ offset: true }),
});
export type AmenitiesScheduleListQueryParams = z.infer<typeof amenitiesScheduleListQueryParamsSchema>;

/** Query parameters of GET /api/v1/bookings/ */
export const bookingsListQueryParamsSchema = z.object({
  amenity_id: z.number().int().min(1).optional(),
  mine: z.boolean().optional(),
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
  status: bookingStatusSchema.optional(),
});
export type BookingsListQueryParams = z.infer<typeof bookingsListQueryParamsSchema>;
