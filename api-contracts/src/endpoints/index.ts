// Contracts of the backend API, kept in sync with its OpenAPI schema (see README).
import { accountsEndpoints } from "./accounts";
import { amenitiesEndpoints } from "./amenities";
import { announcementsEndpoints } from "./announcements";
import { chatEndpoints } from "./chat";
import { eventsEndpoints } from "./events";
import { leasingEndpoints } from "./leasing";
import { libraryEndpoints } from "./library";
import { marketplaceEndpoints } from "./marketplace";
import { notificationsEndpoints } from "./notifications";
import { propertiesEndpoints } from "./properties";
import { serviceRequestsEndpoints } from "./service-requests";
import { shortTermRentalsEndpoints } from "./short-term-rentals";
import { storeEndpoints } from "./store";
import { surveysEndpoints } from "./surveys";
import { visitorsEndpoints } from "./visitors";
import { workOrdersEndpoints } from "./work-orders";

/**
 * Every API operation, by name: method, path, the headers it needs, and the
 * schemas of its parameters, body and response. The operations of one module
 * live in `endpoints/<module>.ts`.
 *
 * - `uiConfigStep`: `"dashboard"` for every dashboard call (which sends
 *   `X-UI-Config-Step: dashboard`); `"syndicat"` or `"property"` for the two
 *   pages of the configuration path; `null` when the call belongs to no step.
 * - `requiredHeaders`: the selection headers to send besides the step header
 *   (`X-Syndicat-Id`, `X-Property-Id`).
 */
export const endpoints = {
  ...accountsEndpoints,
  ...amenitiesEndpoints,
  ...announcementsEndpoints,
  ...chatEndpoints,
  ...eventsEndpoints,
  ...leasingEndpoints,
  ...libraryEndpoints,
  ...marketplaceEndpoints,
  ...notificationsEndpoints,
  ...propertiesEndpoints,
  ...serviceRequestsEndpoints,
  ...shortTermRentalsEndpoints,
  ...storeEndpoints,
  ...surveysEndpoints,
  ...visitorsEndpoints,
  ...workOrdersEndpoints,
} as const;

export type EndpointName = keyof typeof endpoints;

export {
  accountsEndpoints,
  amenitiesEndpoints,
  announcementsEndpoints,
  chatEndpoints,
  eventsEndpoints,
  leasingEndpoints,
  libraryEndpoints,
  marketplaceEndpoints,
  notificationsEndpoints,
  propertiesEndpoints,
  serviceRequestsEndpoints,
  shortTermRentalsEndpoints,
  storeEndpoints,
  surveysEndpoints,
  visitorsEndpoints,
  workOrdersEndpoints,
};
