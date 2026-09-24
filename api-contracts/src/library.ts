// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { propertyRoleSchema } from "./enums";
import { attachmentSchema, paginated, uploadFileSchema, userSummarySchema } from "./shared";

export const libraryDocumentSchema = z.object({
  id: z.number().int(),
  property: z.number().int(),
  folder: z.number().int(),
  title: z.string(),
  description: z.string(),
  target_roles: z.array(propertyRoleSchema),
  file: attachmentSchema.nullable(),
  created_by: userSummarySchema,
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type LibraryDocument = z.infer<typeof libraryDocumentSchema>;

export const libraryDocumentCreateRequestSchema = z.object({
  folder_id: z.number().int().min(1),
  title: z.string().min(1).max(200),
  description: z.string().optional(),
  target_roles: z.array(propertyRoleSchema),
  file: uploadFileSchema,
});
export type LibraryDocumentCreateRequest = z.infer<typeof libraryDocumentCreateRequestSchema>;

export const libraryFolderSchema = z.object({
  id: z.number().int(),
  property: z.number().int(),
  parent_folder: z.number().int().nullable(),
  en_name: z.string(),
  fr_name: z.string(),
  description: z.string(),
  /** Created automatically with the property. */
  is_system: z.boolean(),
  subfolders_count: z.number().int(),
  created_at: z.iso.datetime({ offset: true }),
});
export type LibraryFolder = z.infer<typeof libraryFolderSchema>;

export const libraryFolderCreateRequestSchema = z.object({
  parent_folder_id: z.number().int().min(1).nullable().optional(),
  en_name: z.string().min(1).max(160),
  fr_name: z.string().min(1).max(160),
  description: z.string().optional(),
});
export type LibraryFolderCreateRequest = z.infer<typeof libraryFolderCreateRequestSchema>;

export const paginatedLibraryDocumentListSchema = paginated(libraryDocumentSchema);
export type PaginatedLibraryDocumentList = z.infer<typeof paginatedLibraryDocumentListSchema>;

export const paginatedLibraryFolderListSchema = paginated(libraryFolderSchema);
export type PaginatedLibraryFolderList = z.infer<typeof paginatedLibraryFolderListSchema>;

export const patchedLibraryDocumentRequestSchema = z.object({
  title: z.string().min(1).max(200).optional(),
  description: z.string().optional(),
  folder_id: z.number().int().min(1).optional(),
});
export type PatchedLibraryDocumentRequest = z.infer<typeof patchedLibraryDocumentRequestSchema>;

export const patchedLibraryFolderRequestSchema = z.object({
  en_name: z.string().min(1).max(160).optional(),
  fr_name: z.string().min(1).max(160).optional(),
  description: z.string().optional(),
  parent_folder_id: z.number().int().min(1).nullable().optional(),
});
export type PatchedLibraryFolderRequest = z.infer<typeof patchedLibraryFolderRequestSchema>;

/** Query parameters of GET /api/v1/library/documents/ */
export const libraryDocumentsListQueryParamsSchema = z.object({
  folder_id: z.number().int().min(1).optional(),
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
  search: z.string().max(120).optional(),
});
export type LibraryDocumentsListQueryParams = z.infer<typeof libraryDocumentsListQueryParamsSchema>;

/** Query parameters of GET /api/v1/library/folders/ */
export const libraryFoldersListQueryParamsSchema = z.object({
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
  parent_id: z.number().int().min(1).optional(),
  root_only: z.boolean().optional(),
});
export type LibraryFoldersListQueryParams = z.infer<typeof libraryFoldersListQueryParamsSchema>;
