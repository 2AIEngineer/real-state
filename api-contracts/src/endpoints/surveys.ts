// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { z } from "zod";
import { bulkActionResultSchema, uploadFilesRequestSchema } from "../shared";
import { paginatedSurveyListSchema, patchedSurveyRequestSchema, surveyCreateRequestSchema, surveyParticipationSchema, surveyResponseRequestSchema, surveyResultsSchema, surveySchema, surveysListQueryParamsSchema } from "../surveys";

/** Endpoints of the surveys module. */
export const surveysEndpoints = {
  /** Bulk action (admin, syndic, manager): closes every published survey of the selected property past its closing date. */
  surveysCloseExpiredCreate: {
    method: "POST",
    path: "/api/v1/surveys/close-expired/",
    tag: "Surveys",
    auth: true,
    uiConfigStep: "dashboard",
    requiredHeaders: ["X-Syndicat-Id", "X-Property-Id"],
    response: bulkActionResultSchema,
    status: 200,
  },
  /** Tells the serializer which surveys the reader already answered. */
  surveysCloseCreate: {
    method: "POST",
    path: "/api/v1/surveys/{survey_id}/close/",
    tag: "Surveys",
    auth: true,
    uiConfigStep: "dashboard",
    requiredHeaders: ["X-Syndicat-Id", "X-Property-Id"],
    pathParams: z.object({ survey_id: z.number().int() }),
    response: surveySchema,
    status: 200,
  },
  /** Tells the serializer which surveys the reader already answered. */
  surveysCreate: {
    method: "POST",
    path: "/api/v1/surveys/",
    tag: "Surveys",
    auth: true,
    uiConfigStep: "dashboard",
    requiredHeaders: ["X-Syndicat-Id", "X-Property-Id"],
    body: surveyCreateRequestSchema,
    bodyType: "json",
    response: surveySchema,
    status: 201,
  },
  /** Deletes a survey nobody answered. */
  surveysDestroy: {
    method: "DELETE",
    path: "/api/v1/surveys/{survey_id}/",
    tag: "Surveys",
    auth: true,
    uiConfigStep: "dashboard",
    requiredHeaders: ["X-Syndicat-Id", "X-Property-Id"],
    pathParams: z.object({ survey_id: z.number().int() }),
    response: null,
    status: 204,
  },
  /** Tells the serializer which surveys the reader already answered. */
  surveysFilesCreate: {
    method: "POST",
    path: "/api/v1/surveys/{survey_id}/files/",
    tag: "Surveys",
    auth: true,
    uiConfigStep: "dashboard",
    requiredHeaders: ["X-Syndicat-Id", "X-Property-Id"],
    pathParams: z.object({ survey_id: z.number().int() }),
    body: uploadFilesRequestSchema,
    bodyType: "multipart",
    response: surveySchema,
    status: 201,
  },
  /** Tells the serializer which surveys the reader already answered. */
  surveysList: {
    method: "GET",
    path: "/api/v1/surveys/",
    tag: "Surveys",
    auth: true,
    uiConfigStep: "dashboard",
    requiredHeaders: ["X-Syndicat-Id", "X-Property-Id"],
    queryParams: surveysListQueryParamsSchema,
    response: paginatedSurveyListSchema,
    status: 200,
  },
  /** Tells the serializer which surveys the reader already answered. */
  surveysPartialUpdate: {
    method: "PATCH",
    path: "/api/v1/surveys/{survey_id}/",
    tag: "Surveys",
    auth: true,
    uiConfigStep: "dashboard",
    requiredHeaders: ["X-Syndicat-Id", "X-Property-Id"],
    pathParams: z.object({ survey_id: z.number().int() }),
    body: patchedSurveyRequestSchema,
    bodyType: "json",
    response: surveySchema,
    status: 200,
  },
  /** Tells the serializer which surveys the reader already answered. */
  surveysPublishCreate: {
    method: "POST",
    path: "/api/v1/surveys/{survey_id}/publish/",
    tag: "Surveys",
    auth: true,
    uiConfigStep: "dashboard",
    requiredHeaders: ["X-Syndicat-Id", "X-Property-Id"],
    pathParams: z.object({ survey_id: z.number().int() }),
    response: surveySchema,
    status: 200,
  },
  surveysResponsesCreate: {
    method: "POST",
    path: "/api/v1/surveys/{survey_id}/responses/",
    tag: "Surveys",
    auth: true,
    uiConfigStep: "dashboard",
    requiredHeaders: ["X-Syndicat-Id", "X-Property-Id"],
    pathParams: z.object({ survey_id: z.number().int() }),
    body: surveyResponseRequestSchema,
    bodyType: "json",
    response: surveyParticipationSchema,
    status: 201,
  },
  surveysResultsRetrieve: {
    method: "GET",
    path: "/api/v1/surveys/{survey_id}/results/",
    tag: "Surveys",
    auth: true,
    uiConfigStep: "dashboard",
    requiredHeaders: ["X-Syndicat-Id", "X-Property-Id"],
    pathParams: z.object({ survey_id: z.number().int() }),
    response: surveyResultsSchema,
    status: 200,
  },
  /** Tells the serializer which surveys the reader already answered. */
  surveysRetrieve: {
    method: "GET",
    path: "/api/v1/surveys/{survey_id}/",
    tag: "Surveys",
    auth: true,
    uiConfigStep: "dashboard",
    requiredHeaders: ["X-Syndicat-Id", "X-Property-Id"],
    pathParams: z.object({ survey_id: z.number().int() }),
    response: surveySchema,
    status: 200,
  },
} as const;
