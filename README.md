# API de gestion immobilière

API REST (Django 5.2, DRF, PostgreSQL ≥ 14) d'un SaaS de gestion de résidences : référentiel
(syndicats, promoteurs, propriétés, bâtiments, lots), propriété et location, services aux résidents
(annonces, demandes de service, réservations, boutique, bibliothèque, locations courte durée,
sondages, marketplace, visiteurs, chat) et notifications multicanales.

## Démarrage

```bash
uv sync                                   # dépendances (pyproject.toml / uv.lock)
cp .env.example .env                      # puis renseigner les valeurs
uv run python manage.py migrate
uv run python manage.py create_platform_admin --email admin@exemple.com
uv run python manage.py runserver         # OpenAPI : /api/docs/ (en mode DEBUG)
```

| Commande | Rôle |
|---|---|
| `uv run pytest` | Tests (PostgreSQL requis : les contraintes d'exclusion sont testées pour de vrai). Le profil de test est `config/settings_test.py`. |
| `uv run ruff check .` / `uv run ruff format .` | Lint et formatage (100 colonnes). Le CI (`.github/workflows/ci.yml`) vérifie les deux, ainsi que les migrations, le schéma OpenAPI et les tests. |
| `python manage.py outbox_worker` | Relais de l'outbox : envoi des e-mails et des push, avec reprises et back-off. |
| `python manage.py run_scheduled_jobs` | Expiration des baux, clôture des événements et sondages échus, purge de l'outbox, des jetons de session expirés et des clés d'idempotence (idempotent, toutes les 15 min). |
| `python manage.py purge_orphan_attachments` | Supprime les fichiers stockés sans ligne `Attachment` (quotidien). |

Toutes les routes sont préfixées par `/api/v1/`. Sondes de la plateforme : `/healthz/` (processus vivant) et
`/readyz/` (base joignable). Le déploiement (Azure Container Apps) est documenté à part.

## Organisation du code

Un monolithe modulaire : une app Django par domaine, toutes construites sur le même patron.

```
apps/<module>/
├─ models.py          structure et contraintes de base uniquement
├─ errors.py          les erreurs métier nommées du module (une fabrique par erreur)
├─ policies.py        qui a le droit de faire quoi (une classe par ressource)
├─ services/          les règles métier : un fichier par ressource (ou services.py si une seule)
├─ notices.py         ce que les gens sont prévenus (textes et destinataires des notifications)
├─ audit.py           les actions écrites dans le journal d'audit
├─ serializers.py | serializers/  la forme des entrées et des sorties, sans règle
├─ views.py | views/  parse → appelle le service → rend la réponse (un module par ressource)
├─ urls.py
└─ tests/             test_services.py (règles), test_api.py (HTTP)
```

### Les couches et leurs responsabilités

- **Vues** : elles orchestrent seulement (valider la forme, charger le contexte, appeler le service,
  sérialiser). Aucun accès ORM. Une route = une action métier ; aucun CRUD généré.
- **Services** : toute mutation et toute lecture soumise à une règle. Ils reçoivent des paramètres
  explicites (`actor`, objets, dataclasses), jamais `request`, et lèvent des erreurs de domaine
  (`apps.common.exceptions`) : ils s'appellent donc à l'identique depuis une vue, une commande ou un test.
- **Policies** : chacune répond par un booléen (`can_view`, `can_cancel`…) et fournit le filtre de lecture
  (`visible_filter`). Le service choisit l'erreur : `NotFound` quand l'objet doit rester secret,
  `PermissionDenied` sinon.
- **Erreurs** : `InvalidInput` → 400, `PermissionDenied`/`FeatureDisabled` → 403, `NotFound` → 404,
  `BusinessRuleViolation`/`InvalidTransition` → 409, toutes rendues en `{"error": {"code", "message", …}}`.
  Une contrainte de base connue est traduite par `translate_integrity_errors`, qui prend des *fabriques*
  d'erreurs : une exception n'est jamais partagée entre deux requêtes.
- **Notifications** : les services décrivent l'événement dans `notices.py` ; le dispatcher applique les
  préférences, écrit la boîte de réception et l'outbox dans la même transaction que le changement métier.
  Un échec d'envoi n'annule donc jamais une opération, et une opération annulée ne notifie personne.

### Ce qui vit où

| App | Responsabilité |
|---|---|
| `common` | Noyau technique sans métier : erreurs, gestionnaire d'erreurs HTTP, vues de base (`BaseAPIView`, `UIConfigStepView`), JSON (orjson), schéma OpenAPI, modèles abstraits, helpers DB (`apply_changes`, `translate_integrity_errors`), fichiers (`files/`), journal (`audit`) et sondes (`health`). |
| `accounts` | Identité **et** autorisation : `User`, rôle unique, assignations (syndicat, propriété, bâtiment), `AccessService` (les faits : qui gère, qui travaille sur place, qui habite), inscription, mots de passe. |
| `properties` | Référentiel : syndicats, promoteurs, propriétés, bâtiments, lots, registre de propriété, activation des modules par propriété (`FeatureGate`), navigation de configuration (`SyndicatService.list_reachable`, `PropertyService.list_reachable_in`) et statistiques du tableau de bord. |
| `leasing` | Baux, occupants, états des lieux. |
| `notifications` | Point d'entrée unique des notifications, boîte de réception, outbox et relais. |
| `announcements`, `service_requests`, `work_orders`, `events`, `amenities`, `store`, `library`, `short_term_rental`, `surveys`, `marketplace`, `visitors`, `chat` | Modules fonctionnels. |

### Dépendances entre modules

Les modules sont en couches. Un module bas n'importe jamais les *services* d'un module haut en tête de fichier (il les appelle par un import local, voir plus bas) ; il peut en revanche lire ses *modèles*, qui ne dépendent de rien au-dessus (`properties` lit `leasing.Lease` pour ses statistiques) :
`common ← accounts.models ← properties ← leasing ← accounts.services ← notifications / modules fonctionnels ← chat`.

Aucun signal, aucun registre : quand un module bas doit déclencher quelque chose dans un module haut, il
l'appelle directement, par un import placé dans la fonction (pas en tête de fichier) pour ne pas faire
remonter la dépendance au niveau du module entier. Le commentaire à côté de l'import dit toujours pourquoi :

```python
# A new property starts with the standard library tree. Local import:
# the library module is built on top of properties.
from apps.library.services import FolderService

FolderService.create_default_folders(prop=prop)
```

Quelques exemples : `PropertyService.create`/`.delete` appellent `library.FolderService` pour créer ou
retirer l'arborescence par défaut ; `UnitService.delete` vérifie directement `leasing.Lease` avant de
refuser la suppression d'un lot loué ; `LeaseService.terminate`/`.cancel`/`.delete` appellent
`short_term_rental.ShortTermRentalService` pour annuler ou bloquer selon les sous-locations en cours. Ces
appels se lisent à l'endroit où ils ont lieu, sans détour par un mécanisme d'écoute.

### Suppression et archivage

Deux actions distinctes, au choix de l'utilisateur :

- **archiver** (ou désactiver, clôturer, annuler selon la ressource) garde tout l'historique ;
- **supprimer** est une action consciente et destructive, jamais refusée parce que d'autres
  enregistrements dépendent de la ressource :
  - ce qui **appartient** à la ressource part avec elle (`CASCADE`). Supprimer un bâtiment supprime ses
    lots, leurs baux, leurs occupants, leurs demandes, et ainsi de suite ;
  - ce qui la **cite seulement comme auteur** reste, sans auteur (`SET_NULL`).

Cela vaut aussi pour les comptes : supprimer un utilisateur supprime ce qui est à lui (ses propriétés de
lots, ses places dans les baux, ses demandes, réservations, commandes, annonces de la marketplace,
messages, réponses aux sondages, appareils, notifications, assignations), avec leurs fichiers. Ce qu'il a
rédigé ou enregistré pour la résidence (annonces, événements, documents, visiteurs…) reste, sans auteur.
Un lot resté sans propriétaire revient au promoteur, un bail resté sans occupant prend fin. Qui ne veut
pas supprimer un compte le désactive.

Une seule exception : une propriété ne peut pas exister sans promoteur. Supprimer un promoteur qui en
développe encore répond 409 ; on lui en substitue un autre sur ses propriétés d'abord. Une ligne de
commande garde ses nom et prix quand le produit est retiré du catalogue. Les dossiers par défaut de la
bibliothèque ne sont qu'une préconfiguration : ils se modifient et se suppriment comme les autres.

Un fichier ou une notification pointe vers un enregistrement par `(type, id)`, sans clé étrangère : la base
ne peut pas les supprimer en cascade. Chaque `delete()` de service finit donc par
`apps.common.deletion.destroy(objet)`, qui recense toutes les lignes atteintes par la cascade et supprime
leurs fichiers (chaque type de fichier déclare son modèle propriétaire dans `rules.py`) et leurs traces de
notification, dans la même transaction. `purge_orphan_attachments` récupère les blobs stockés sans ligne.

### Pièces jointes

Les règles de chaque type de fichier (formats, nombre, taille, modèle propriétaire) sont dans
`apps/common/attachments/rules.py`. Le format est détecté d'après le contenu, jamais d'après l'extension,
et le fichier est stocké sous l'extension de ce format. Le champ `url` d'une pièce jointe est l'adresse du
fichier dans son stockage (Azure Blob en production, disque local en développement) : il s'utilise tel
quel, sans appel supplémentaire.

### Autorisation

Un compte a **un seul rôle** sur toute la plateforme (`User.role` : `admin`, `syndic`, `manager`,
`security`, `maintenance`, `cleaning`, `provider`, `standard`). Où ce rôle s'exerce est porté par trois
tables d'assignation (`UserSyndicat`, `UserProperty`, `UserBuilding`). Propriétaire et locataire ne sont
jamais des rôles stockés : ils se déduisent de `UnitOwnership` et de `LeaseMember`.

- `accounts/services/authorization.py` (`AccessService`) énonce des **faits**, jamais des décisions.
- Chaque module décide pour ses ressources dans son `policies.py`.
- `accounts/services/visibility.py` répond à la question des contenus adressés à des rôles.

### Sélection du syndicat et de la propriété

Le serveur ne traite jamais une requête de tableau de bord sans savoir, de façon certaine, pour quelle
propriété — pour ne jamais risquer de mélanger les données de deux propriétés. Après la connexion, le
client choisit donc son syndicat puis sa propriété en trois étapes, chacune annoncée dans l'en-tête
`X-UI-Config-Step` :

| Étape | Le client envoie | Le serveur répond |
|---|---|---|
| `syndicat` | `X-UI-Config-Step: syndicat` | Les syndicats que le compte peut ouvrir (`GET /ui-config/syndicats/`), sans pagination. |
| `property` | + `X-Syndicat-Id` | Les propriétés de ce syndicat (`GET /ui-config/properties/`). |
| `dashboard` | + `X-Property-Id` | Toute route du tableau de bord. |

Une fois la paire choisie, **toute requête de tableau de bord porte les trois** : `X-Syndicat-Id`,
`X-Property-Id`, et `X-UI-Config-Step: dashboard`. La propriété sélectionnée vient toujours de ces
en-têtes ; le serveur n'a donc jamais à deviner dans quelle propriété il se trouve. Trois bases portent la
règle :

| Base | Exige |
|---|---|
| `ApiMixin` + `APIView` (DRF) | rien — connexion, `/me/`, notifications, console d'administration |
| `apps.common.views.UIConfigStepView` | `X-UI-Config-Step` égal à l'étape déclarée par la vue (`syndicat` ou `property`) |
| `apps.common.views.BaseAPIView` | `X-Syndicat-Id`, `X-Property-Id`, `X-UI-Config-Step: dashboard` |

`BaseAPIView` résout la sélection avant la vue : la propriété doit exister, être visible du compte et
appartenir au syndicat choisi. La vue travaille ensuite avec `self.property`, qu'elle passe aux services ;
ceux-ci cherchent chaque enregistrement *dans* cette propriété (`get_visible(prop=…)`). Un enregistrement
d'une autre propriété répond 404, même à un compte qui gère les deux. Une route qui porte aussi la
propriété dans son URL (`/properties/{id}/…`) exige qu'elle soit la propriété sélectionnée.

La connexion (`POST /auth/token/`) renvoie le `SessionContext` que le client attend : `credentials` (les jetons),
`ui_config` (mode de l'app, étape, syndicat et propriété choisis, modules activés) et `user` (identité, rôle,
patrimoine : lots possédés et loués). Ce que le backend ne peut pas décider seul (mode, étape, syndicat et
propriété) vaut `null`, les listes sont vides, et le rôle est porté par huit indicateurs dont un seul est vrai.

### Invariants garantis par la base

Baux actifs, réservations exclusives et locations courte durée qui ne se chevauchent pas
(`ExclusionConstraint`), une salle de chat par contexte, un seul fichier par emplacement unique,
quote-parts de propriété bornées. Ceux que la base ne sait pas exprimer sont tenus dans les services sous
verrou de ligne (`select_for_update`) : un lot a toujours un propriétaire, un bail actif a un occupant,
le stock est réservé à la commande.

## Ajouter un module

1. `models.py` et sa migration.
2. `errors.py`, `policies.py`, `services/`, `notices.py`, `audit.py`. Le `delete()` d'un service vérifie
   le droit, écrit l'audit puis appelle `destroy(objet)`. Un nouveau type de fichier déclare son modèle
   propriétaire dans `apps/common/attachments/rules.py`.
3. `serializers.py`, `views.py`, `urls.py` (à déclarer dans `config/urls.py`, l'app dans `INSTALLED_APPS`).
   Une vue de tableau de bord hérite de `apps.common.views.BaseAPIView` et passe `prop=self.property` au
   `get_visible` de ses services, qui filtre sur cette propriété.
4. `tests/test_services.py` pour les règles, `test_api.py` pour l'orchestration HTTP.
