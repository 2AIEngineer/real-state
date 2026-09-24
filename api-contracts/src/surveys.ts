// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { propertyRoleSchema, surveyStatusSchema } from "./enums";
import { attachmentSchema, paginated } from "./shared";

export const surveyAnswerRequestSchema = z.object({
  question_id: z.number().int().min(1),
  option_id: z.number().int().min(1),
});
export type SurveyAnswerRequest = z.infer<typeof surveyAnswerRequestSchema>;

export const surveyOptionSchema = z.object({
  id: z.number().int(),
  text: z.string(),
  position: z.number().int(),
});
export type SurveyOption = z.infer<typeof surveyOptionSchema>;

export const surveyOptionResultSchema = z.object({
  id: z.number().int(),
  text: z.string(),
  votes: z.number().int(),
});
export type SurveyOptionResult = z.infer<typeof surveyOptionResultSchema>;

export const surveyParticipationSchema = z.object({
  id: z.number().int(),
  submitted_at: z.iso.datetime({ offset: true }),
});
export type SurveyParticipation = z.infer<typeof surveyParticipationSchema>;

export const surveyQuestionSchema = z.object({
  id: z.number().int(),
  text: z.string(),
  position: z.number().int(),
  options: z.array(surveyOptionSchema),
});
export type SurveyQuestion = z.infer<typeof surveyQuestionSchema>;

export const surveyQuestionInputRequestSchema = z.object({
  text: z.string().min(1).max(1000),
  options: z.array(z.string().min(1).max(200)).max(20),
});
export type SurveyQuestionInputRequest = z.infer<typeof surveyQuestionInputRequestSchema>;

export const surveyQuestionResultSchema = z.object({
  id: z.number().int(),
  text: z.string(),
  options: z.array(surveyOptionResultSchema),
});
export type SurveyQuestionResult = z.infer<typeof surveyQuestionResultSchema>;

export const surveyResponseRequestSchema = z.object({
  answers: z.array(surveyAnswerRequestSchema),
});
export type SurveyResponseRequest = z.infer<typeof surveyResponseRequestSchema>;

export const surveyResultsSchema = z.object({
  survey_id: z.number().int(),
  participants: z.number().int(),
  /** People the survey was addressed to when published. */
  recipients: z.number().int(),
  questions: z.array(surveyQuestionResultSchema),
});
export type SurveyResults = z.infer<typeof surveyResultsSchema>;

export const patchedSurveyRequestSchema = z.object({
  title: z.string().min(1).max(200).optional(),
  description: z.string().optional(),
  target_roles: z.array(propertyRoleSchema).optional(),
  closes_at: z.iso.datetime({ offset: true }).nullable().optional(),
  questions: z.array(surveyQuestionInputRequestSchema).optional(),
});
export type PatchedSurveyRequest = z.infer<typeof patchedSurveyRequestSchema>;

export const surveySchema = z.object({
  id: z.number().int(),
  property: z.number().int(),
  title: z.string(),
  description: z.string(),
  target_roles: z.array(propertyRoleSchema),
  status: surveyStatusSchema,
  closes_at: z.iso.datetime({ offset: true }).nullable(),
  published_at: z.iso.datetime({ offset: true }).nullable(),
  closed_at: z.iso.datetime({ offset: true }).nullable(),
  questions: z.array(surveyQuestionSchema),
  files: z.array(attachmentSchema),
  has_answered: z.boolean().nullable(),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});
export type Survey = z.infer<typeof surveySchema>;

export const surveyCreateRequestSchema = z.object({
  title: z.string().min(1).max(200),
  description: z.string().optional(),
  target_roles: z.array(propertyRoleSchema),
  closes_at: z.iso.datetime({ offset: true }).nullable().optional(),
  questions: z.array(surveyQuestionInputRequestSchema),
});
export type SurveyCreateRequest = z.infer<typeof surveyCreateRequestSchema>;

export const paginatedSurveyListSchema = paginated(surveySchema);
export type PaginatedSurveyList = z.infer<typeof paginatedSurveyListSchema>;

/** Query parameters of GET /api/v1/surveys/ */
export const surveysListQueryParamsSchema = z.object({
  /** Un numéro de page de l'ensemble des résultats. */
  page: z.number().int().optional(),
  /** Nombre de résultats à retourner par page. */
  page_size: z.number().int().optional(),
  status: surveyStatusSchema.optional(),
});
export type SurveysListQueryParams = z.infer<typeof surveysListQueryParamsSchema>;
