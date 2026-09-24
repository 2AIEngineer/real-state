// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { inboxNotificationCategorySchema, pushPlatformSchema, severitySchema } from "./enums";
import { paginated } from "./shared";

export const inboxNotificationSchema = z.object({
  id: z.number().int(),
  category: inboxNotificationCategorySchema,
  /** e.g. service_request.created */
  notification_type: z.string(),
  severity: severitySchema,
  title: z.string(),
  body: z.string(),
  data: z.unknown(),
  target_type: z.string().nullable(),
  object_id: z.number().int().nullable(),
  is_read: z.boolean(),
  read_at: z.iso.datetime({ offset: true }).nullable(),
  created_at: z.iso.datetime({ offset: true }),
});
export type InboxNotification = z.infer<typeof inboxNotificationSchema>;

export const notificationPreferenceSchema = z.object({
  enabled_push: z.boolean().optional(),
  enabled_email: z.boolean().optional(),
  service_request_enabled: z.boolean().optional(),
  announcements_enabled: z.boolean().optional(),
  events_enabled: z.boolean().optional(),
  bookings_enabled: z.boolean().optional(),
  store_enabled: z.boolean().optional(),
  library_enabled: z.boolean().optional(),
  short_term_rental_enabled: z.boolean().optional(),
  surveys_enabled: z.boolean().optional(),
  marketplace_enabled: z.boolean().optional(),
  visitors_enabled: z.boolean().optional(),
  chat_enabled: z.boolean().optional(),
});
export type NotificationPreference = z.infer<typeof notificationPreferenceSchema>;

export const notificationUnreadCountSchema = z.object({
  unread: z.number().int(),
});
export type NotificationUnreadCount = z.infer<typeof notificationUnreadCountSchema>;

export const notificationsMarkedReadSchema = z.object({
  /** Number of notifications marked as read. */
  updated: z.number().int(),
});
export type NotificationsMarkedRead = z.infer<typeof notificationsMarkedReadSchema>;

export const paginatedInboxNotificationListSchema = paginated(inboxNotificationSchema);
export type PaginatedInboxNotificationList = z.infer<typeof paginatedInboxNotificationListSchema>;

export const patchedNotificationPreferenceRequestSchema = z.object({
  enabled_push: z.boolean().optional(),
  enabled_email: z.boolean().optional(),
  service_request_enabled: z.boolean().optional(),
  announcements_enabled: z.boolean().optional(),
  events_enabled: z.boolean().optional(),
  bookings_enabled: z.boolean().optional(),
  store_enabled: z.boolean().optional(),
  library_enabled: z.boolean().optional(),
  short_term_rental_enabled: z.boolean().optional(),
  surveys_enabled: z.boolean().optional(),
  marketplace_enabled: z.boolean().optional(),
  visitors_enabled: z.boolean().optional(),
  chat_enabled: z.boolean().optional(),
});
export type PatchedNotificationPreferenceRequest = z.infer<typeof patchedNotificationPreferenceRequestSchema>;

export const pushTokenSchema = z.object({
  device_id: z.string().max(191),
  expo_push_token: z.string().max(255),
  platform: z.string().max(16).optional(),
  is_active: z.boolean(),
  created_at: z.iso.datetime({ offset: true }),
  last_seen_at: z.iso.datetime({ offset: true }),
});
export type PushToken = z.infer<typeof pushTokenSchema>;

export const pushTokenRegisterRequestSchema = z.object({
  device_id: z.string().min(1).max(191),
  expo_push_token: z.string().min(1).max(255),
  platform: pushPlatformSchema.optional(),
});
export type PushTokenRegisterRequest = z.infer<typeof pushTokenRegisterRequestSchema>;

/** Query parameters of GET /api/v1/notifications/ */
export const notificationsListQueryParamsSchema = z.object({
  category: inboxNotificationCategorySchema.optional(),
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
  unread: z.boolean().optional(),
});
export type NotificationsListQueryParams = z.infer<typeof notificationsListQueryParamsSchema>;
