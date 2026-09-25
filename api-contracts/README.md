# Contrats de l'API (Zod + TypeScript)

Schémas [Zod](https://zod.dev) (v4) et types TypeScript de toute l'API, à copier tels quels dans le frontend (`src/` suffit).

Ils suivent le schéma OpenAPI du backend, donc directement les serializers, et des tests vérifient qu'ils ne s'en éloignent pas (voir plus bas). Ils décrivent chaque objet renvoyé, chaque corps de requête, chaque paramètre d'URL (`queryParams`) et chaque endpoint.

## Contenu de `src/`

| Fichier | Contenu |
|---|---|
| `shared.ts` | Ce qui sert à tous les domaines. D'abord les briques communes : enveloppe d'erreur (`apiErrorSchema`), codes d'erreur connus (`knownErrorCodes`), pagination (`paginated`), fichiers envoyés (`uploadFileSchema`), décimaux (`decimalString`). Ensuite les schémas partagés par plusieurs domaines (`attachmentSchema`, `userSchema`, `userSummarySchema`…). |
| `enums.ts` | Toutes les valeurs fermées : rôles (`accountRoleSchema`, `propertyRoleSchema`), statuts, catégories… |
| `accounts.ts`, `properties.ts`, `leasing.ts`, `amenities.ts`, `announcements.ts`, `events.ts`, `library.ts`, `marketplace.ts`, `store.ts`, `service-requests.ts`, `work-orders.ts`, `visitors.ts`, `short-term-rentals.ts`, `surveys.ts`, `chat.ts`, `notifications.ts` | Schémas d'un domaine : objets renvoyés (`leaseSchema`), corps de requête (`leaseCreateRequestSchema`, `patchedLeaseRequestSchema`), listes paginées (`paginatedLeaseListSchema`), paramètres d'URL (`leasesListQueryParamsSchema`). |
| `endpoints/` | Le catalogue des opérations, **un fichier par module** (`endpoints/leasing.ts`, `endpoints/store.ts`…), réunis par `endpoints/index.ts` (voir plus bas). |
| `index.ts` | Réexporte tout. |

Chaque schéma a son type : `leaseSchema` → `type Lease`, `leaseCreateRequestSchema` → `type LeaseCreateRequest`, `accountRoleSchema` → `type AccountRole`.

## Utilisation

```ts
import { endpoints, leaseSchema, type Lease, apiErrorSchema } from "@/api-contracts";

// Valider une réponse
const lease: Lease = leaseSchema.parse(await response.json());

// Valider un formulaire avant l'envoi
const body = endpoints.leasesCreate.body.parse(formValues);

// Lire une erreur
const { error } = apiErrorSchema.parse(await response.json());
if (error.code === "lease_overlap") { /* ... */ }
```

Chaque entrée de `endpoints` indique :

| Clé | Sens |
|---|---|
| `method`, `path` | Méthode et chemin (`/api/v1/leases/{lease_id}/`). |
| `auth` | `false` pour les rares endpoints publics (connexion, mot de passe). |
| `uiConfigStep` | Valeur de `X-UI-Config-Step` à envoyer : `"dashboard"` pour tout appel du tableau de bord, `"syndicat"` ou `"property"` pour les deux pages du parcours de configuration, `null` quand l'appel n'appartient à aucune étape (connexion, notifications, console d'administration). |
| `requiredHeaders` | En-têtes de sélection à envoyer en plus : `X-Syndicat-Id`, `X-Property-Id`. |
| `pathParams`, `queryParams` | Schémas des paramètres de chemin et des paramètres d'URL. |
| `body`, `bodyType` | Schéma du corps et son encodage : `"json"`, ou `"multipart"` dès qu'il contient un fichier. |
| `response`, `status` | Schéma de la réponse en cas de succès et son code ; `response: null` quand il n'y a pas de corps (204). |

### Sélection du syndicat et de la propriété

La connexion (`endpoints.authTokenCreate`) renvoie le `SessionContext` : `credentials`, `ui_config` et `user`. Ce que le backend ne peut pas décider (`app_mode`, `step`, syndicat et propriété choisis) vaut `null`, les listes sont vides.

Le client choisit ensuite un syndicat puis une propriété, en annonçant l'étape où il se trouve dans `X-UI-Config-Step` (`uiConfigStepSchema` : `syndicat`, `property`, `dashboard` ; aucun en-tête juste après la connexion) :

```ts
import { endpoints } from "@/api-contracts";

// 1. endpoints.uiConfigSyndicatsList  -> uiConfigStep "syndicat"          (liste complète, sans pagination)
// 2. endpoints.uiConfigPropertiesList -> uiConfigStep "property",  + X-Syndicat-Id  (liste complète)
// 3. tout le reste                    -> uiConfigStep "dashboard", + X-Syndicat-Id et X-Property-Id
```

Dans le tableau de bord, **chaque appel** porte donc les trois en-têtes. La propriété ouverte n'est jamais un paramètre d'URL ni un champ de corps : le serveur la lit dans l'en-tête.

Quelques conventions de l'API reflétées dans les schémas :
- les dates-heures sont en ISO 8601 avec fuseau, les dates en `AAAA-MM-JJ` ;
- les montants et pourcentages sont des chaînes décimales (`"12.50"`) pour garder leur précision ;
- un e-mail ou une URL facultatifs valent `""` quand ils ne sont pas renseignés ;
- un POST peut porter l'en-tête facultatif `Idempotency-Key` (`IDEMPOTENCY_KEY_HEADER`) : un UUID généré une fois par action et renvoyé à chaque nouvel essai, pour ne jamais créer de doublon ;
- les actions en masse du tableau de bord (`leasesExpireDueCreate`, `eventsCompletePastCreate`, `surveysCloseExpiredCreate`, `bookingsCompletePastCreate`, `shortTermRentalsCompletePastCreate`) s'appellent sans corps, sur la propriété sélectionnée, et répondent `{ count }` (`bulkActionResultSchema`) ;
- toutes les listes sont paginées (`count`, `next`, `previous`, `results`), sauf les listes courtes documentées comme tableaux simples (les deux pages `ui-config/`, créneaux d'un équipement, tours d'une demande, membres d'une location courte durée).

## Mettre à jour après un changement du backend

Les fichiers de `src/` s'éditent à la main : après un changement d'API, modifier le schéma ou l'endpoint concerné (un endpoint vit dans `src/endpoints/<module>.ts`), puis lancer la vérification ci-dessous, qui dit précisément ce qui ne colle plus.

## Vérifier que les contrats collent à l'API

```bash
# 1. Depuis la racine du backend : exporter le schéma OpenAPI et capturer de vraies réponses
python manage.py spectacular --format openapi-json --file api-contracts/tests/openapi.json
CONTRACT_SAMPLES=$PWD/api-contracts/tests/samples.json pytest tests/test_api_contract_samples.py

# 2. Les comparer aux contrats
cd api-contracts
npm install
npm run typecheck
npm test
```

- `tests/routes.test.ts` compare les contrats au schéma OpenAPI : mêmes routes (aucune en trop, aucune manquante), mêmes en-têtes requis, même code de succès, mêmes champs dans chaque corps de requête et chaque réponse.
- `tests/schemas.test.ts` va au fond de chaque opération : paramètres de chemin et d'URL, corps et réponse, champ par champ et à tous les niveaux d'imbrication — obligatoire ou facultatif, `null` possible ou non, type, valeurs d'énumération, encodage `json`/`multipart`.
- `tests/contracts.test.ts` passe de vraies réponses de l'API (étape 1 : chaque GET, plus la connexion) dans le schéma de leur endpoint.

Un échec signale un contrat qui ne correspond plus à ce que l'API expose ou renvoie.
