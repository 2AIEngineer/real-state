// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { chatContextTypeSchema } from "./enums";
import { attachmentSchema, paginated, uploadFileSchema, userSummarySchema } from "./shared";

export const chatMessageSchema = z.object({
  id: z.number().int(),
  chat_room: z.number().int(),
  sender: userSummarySchema,
  body: z.string(),
  media: attachmentSchema.nullable(),
  created_at: z.iso.datetime({ offset: true }),
  edited_at: z.iso.datetime({ offset: true }).nullable(),
});
export type ChatMessage = z.infer<typeof chatMessageSchema>;

export const chatMessageCreateRequestSchema = z.object({
  body: z.string().optional(),
  media: uploadFileSchema.nullable().optional(),
});
export type ChatMessageCreateRequest = z.infer<typeof chatMessageCreateRequestSchema>;

export const chatRoomSchema = z.object({
  id: z.number().int(),
  property: z.number().int(),
  context_type: z.string(),
  context_id: z.number().int(),
  last_message_at: z.iso.datetime({ offset: true }).nullable(),
  /** Messages from others since the viewer last read the room. */
  unread_count: z.number().int(),
  created_at: z.iso.datetime({ offset: true }),
});
export type ChatRoom = z.infer<typeof chatRoomSchema>;

export const chatRoomOpenRequestSchema = z.object({
  context_type: chatContextTypeSchema,
  context_id: z.number().int().min(1),
});
export type ChatRoomOpenRequest = z.infer<typeof chatRoomOpenRequestSchema>;

export const paginatedChatMessageListSchema = paginated(chatMessageSchema);
export type PaginatedChatMessageList = z.infer<typeof paginatedChatMessageListSchema>;

export const paginatedChatRoomListSchema = paginated(chatRoomSchema);
export type PaginatedChatRoomList = z.infer<typeof paginatedChatRoomListSchema>;

export const patchedChatMessageRequestSchema = z.object({
  body: z.string().optional(),
});
export type PatchedChatMessageRequest = z.infer<typeof patchedChatMessageRequestSchema>;

/** Query parameters of GET /api/v1/chat/rooms/ */
export const chatRoomsListQueryParamsSchema = z.object({
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
});
export type ChatRoomsListQueryParams = z.infer<typeof chatRoomsListQueryParamsSchema>;

/** Query parameters of GET /api/v1/chat/rooms/{room_id}/messages/ */
export const chatRoomsMessagesListQueryParamsSchema = z.object({
  before_id: z.number().int().min(1).optional(),
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
});
export type ChatRoomsMessagesListQueryParams = z.infer<typeof chatRoomsMessagesListQueryParamsSchema>;
