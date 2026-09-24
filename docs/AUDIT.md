# Audit de l'API — septembre 2026

Périmètre : tout le dépôt (`apps/`, `config/`, `scripts/`, `tests/`, `api-contracts/`), commit `def4b34`.
Le déploiement Azure (ACR/ACA) n'est pas au cœur de cet audit ; la section 8 liste seulement ce qu'il
faut prévoir dans le code dès maintenant pour que la phase de déploiement se passe bien.

## 0. État au 24 septembre 2026 (après corrections)

| # | Constat | État | Où |
|---|---|---|---|
| S1 | Sélection syndicat/propriété non vérifiée | **Corrigé** : `BaseAPIView` résout `self.property`, chaque `get_visible` filtre sur elle | `apps/common/views.py`, `tests/test_selection.py` |
| S2 | Extension de stockage choisie par le client | **Corrigé** : extension et `Content-Type` suivent le format détecté | `apps/common/files/rules.py`, `models/attachments.py` |
| S3 | Fichiers privés publics | **Corrigé** : liens signés utilisables tels quels (`<img src>`), permanents pour les images publiques, personnels et valables 12–24 h pour le reste ; conteneur Azure privé + SAS ; route `/media/` supprimée | `apps/common/files/`, `tests/test_file_links.py` |
| S4 | Jetons non révocables | **Corrigé** : liste noire, `POST /auth/logout/`, révocation au changement de mot de passe et à la désactivation, lien de reset de 2 h | `apps/accounts/services/tokens.py`, `setup_links.py`, `tests/test_sessions.py` |
| S5 | Throttling contournable | **Corrigé** : `NUM_PROXIES`, throttles globaux, limite de connexion par compte, cache Redis via `REDIS_URL` | `config/settings.py`, `apps/accounts/throttles.py` |
| S6 | Secrets dans l'outbox | **Corrigé** : contenu effacé dès qu'un message est final, purge après 30 jours | `apps/notifications/services/delivery.py`, `retention.py` |
| — | Corps JSON de 50 Mo en mémoire | **Corrigé** : 5 Mo | `config/settings.py` |
| — | Effacement RGPD incomplet | **Corrigé** en partie : genre, langue, appareils, inbox, préférences. Reste à décider : conservation des pièces d'identité | `apps/accounts/services/status.py` |
| — | Push en doublon | **Corrigé** : un message par lot de 100 destinataires | `apps/notifications/services/dispatcher.py` |
| — | Secrets courts / `ENVIRONMENT` inconnu | **Corrigé** : refus de démarrer en production | `config/env.py` |
| — | CI absente | **Corrigé** : ruff, migrations, schéma OpenAPI, pytest, contrats TS | `.github/workflows/ci.yml` |
| — | Sondes de santé | **Ajouté** : `/healthz/`, `/readyz/` | `apps/common/health.py` |
| — | Lisibilité | **Fait** : modules découpés par ressource (voir section 11) | — |

Restent ouverts, parce qu'ils relèvent d'une décision produit ou de la phase déploiement :
fuseau horaire par propriété (§5.1 ; en attendant, fixer `TIME_ZONE`), administrateurs en copie de
tout (§5.2), clés d'idempotence (§5.5), suppression définitive vs archivage (§5.6), cache par requête
d'`AccessService` (§6), mypy et couverture (§7), préparation ACA (§9).

## 1. Synthèse

Le code est d'un niveau nettement supérieur à la moyenne : architecture en couches tenue partout
(vues → services → policies), erreurs de domaine uniformes, invariants portés par PostgreSQL
(contraintes d'exclusion, contraintes partielles), verrous de ligne là où la base ne suffit pas,
outbox transactionnelle pour les notifications, détection du format des fichiers d'après le contenu.
376 tests passent (1 ignoré), `ruff` est propre, le schéma OpenAPI se génère sans avertissement (140 chemins,
213 opérations) et le snapshot de `api-contracts` est à jour.

Les points à traiter avant toute mise en production sont presque tous **transverses** (fichiers,
jetons, sélection de la propriété, throttling) plutôt que dans la logique métier :

| # | Sévérité | Constat | Preuve |
|---|---|---|---|
| S1 | Élevée | La sélection `X-Syndicat-Id` / `X-Property-Id` n'est pas vérifiée sur les routes de détail ni sur les listes : l'invariant annoncé par le README n'est pas tenu | test `xfail` |
| S2 | Élevée | L'extension du fichier stocké vient du nom fourni par le client → un PDF nommé `x.html` est servi en `text/html` (XSS stockée) | test `xfail` |
| S3 | **Critique** | Les fichiers privés (pièces d'identité, justificatifs, états des lieux) sont publics : `serve` Django sans authentification, et URLs Azure non signées | test `xfail` |
| S4 | Élevée | Aucun moyen de révoquer un jeton : ni changement de mot de passe, ni rotation, ni désactivation d'appareil ne coupent une session volée | 2 tests `xfail` |
| S5 | Élevée | Le throttling de l'authentification se contourne avec un `X-Forwarded-For` arbitraire, et il est local à chaque processus | test `xfail` |
| S6 | Élevée | Le lien de réinitialisation du mot de passe (jeton valide 72 h) est stocké en clair dans l'outbox, jamais purgée | lecture de code |

Ces sept comportements sont reproduits par `tests/test_audit_findings.py` : chaque test décrit le
comportement **attendu** et est marqué `xfail(strict=True)`. Quand un défaut est corrigé, le test
passe, le mode strict le signale, et on retire le marqueur : le test protège alors la correction.

## 2. Méthode

- Lecture complète du noyau (`common`, `accounts`, `notifications`, `config`) et lecture ciblée des
  modules fonctionnels (services, policies, vues de `service_requests`, `store`, `properties`, etc.).
- Exécution : `pytest` sur PostgreSQL 16 (376 passés, 1 ignoré), `ruff check`, `ruff format --check`,
  `manage.py check --deploy`, génération du schéma OpenAPI et comparaison au snapshot.
- Chaque hypothèse de sécurité a été vérifiée par un test exécuté, pas seulement par lecture.

## 3. Points forts à conserver

- **Architecture** : un patron unique par app (`models / errors / policies / services / notices /
  audit / serializers / views`) appliqué sans exception ; aucune requête ORM dans les vues ; services
  appelables depuis une commande, un worker ou un test.
- **Autorisation** : séparation nette entre les faits (`AccessService`) et les décisions (`policies.py`
  par module) ; `NotFound` pour ce qui doit rester secret, `PermissionDenied` sinon.
- **Intégrité** : `ExclusionConstraint` pour baux, réservations et locations courte durée,
  `select_for_update` ordonné par clé (pas d'interblocage sur les commandes), `translate_integrity_errors`
  avec des fabriques d'erreurs, `deleting()` qui transforme les `PROTECT` en 409 lisibles.
- **Notifications** : outbox écrite dans la transaction métier, relais `SKIP LOCKED` multi-instances,
  back-off exponentiel, désactivation des jetons Expo `DeviceNotRegistered`.
- **Fichiers** : format détecté par signature, noms de stockage aléatoires, règles par type d'entité,
  suppression des blobs après commit, commande de purge des orphelins.
- **Mise à jour partielle** : `apply_changes` avec liste blanche de champs : pas d'affectation de masse.
- **Tests** : près de 380 tests lisibles, organisés en règles (`test_services`) et HTTP (`test_api`), sur une
  vraie base PostgreSQL.

## 4. Sécurité

### S1 — La propriété sélectionnée n'est pas un périmètre réel (élevée)

`BaseAPIView.initial` (`apps/common/views.py:145`) vérifie seulement que les trois en-têtes sont
**présents**. Ensuite :

- les routes de détail et d'action (`/service-requests/{id}/`, `/orders/{id}/cancel/`…) chargent l'objet
  par son identifiant sans comparer sa propriété à `X-Property-Id` ;
- les listes filtrent sur `X-Property-Id` mais n'utilisent jamais `X-Syndicat-Id` : un syndicat
  étranger est accepté (`ServiceRequestService.list_visible`, idem `leasing`, `store`, `visitors`…) ;
- certaines routes portent en plus l'identifiant de propriété dans l'URL
  (`/properties/{property_id}/…`, `apps/properties/urls.py`) : l'URL l'emporte, l'en-tête est ignoré.

Les policies empêchent l'accès à une propriété **non autorisée**, donc ce n'est pas une fuite entre
clients. Mais un gestionnaire de deux propriétés peut lire et modifier les données de B en ayant
sélectionné A, ce que le README présente comme impossible (« le serveur n'a jamais à deviner »).
C'est aussi la garantie sur laquelle le frontend va s'appuyer.

**Recommandation** : résoudre la sélection une seule fois, dans `BaseAPIView.initial` :
`self.selection = SelectionService.resolve(actor, syndicat_id, property_id)` qui charge la propriété,
vérifie `prop.syndicat_id == syndicat_id` et l'accès de l'acteur (404 sinon). Les services reçoivent
`prop` (objet) au lieu de `property_id`, et chaque `get_visible` prend `prop` et filtre
`property=prop`. Pour les routes `/properties/{property_id}/…`, soit retirer l'identifiant de l'URL
(il vient de l'en-tête), soit exiger qu'il soit égal à l'en-tête. Un test paramétré sur toutes les
routes `BaseAPIView` (à partir du schéma OpenAPI, comme `test_api_contract_samples.py`) fermera le
sujet durablement.

### S2 — Extension de stockage contrôlée par le client (élevée)

`attachment_upload_to` (`apps/common/models.py:178`) reprend le suffixe du nom envoyé. La validation
porte sur le contenu (PDF valide) mais le fichier est stocké en `….html`, et `serve` comme Azure Blob
en déduisent `Content-Type: text/html`. Un fichier PDF/HTML polyglotte devient une XSS stockée sur
l'origine qui sert les fichiers — l'origine de l'API tant que les fichiers sont servis par Django.

**Recommandation** : dériver l'extension du type MIME détecté (table `mime → extension` à côté de
`RULES`), passer le type détecté comme `content_type` au stockage, et servir les téléchargements avec
`Content-Disposition: attachment` et `X-Content-Type-Options: nosniff` pour tout ce qui n'est pas une
image.

### S3 — Fichiers privés accessibles sans authentification (critique)

- En stockage disque, `config/urls.py:28` expose tout `MEDIA_ROOT` via `django.views.static.serve`,
  sans authentification, y compris en production si les variables Azure manquent (le repli est
  silencieux, `config/settings.py:153`).
- En stockage Azure, `expiration_secs: None` (`config/settings.py:162`) implique un conteneur à accès
  public et des URLs permanentes.

Or ces fichiers incluent des pièces d'identité (locataires, visiteurs, locations courte durée),
des justificatifs de domicile et des photos d'états des lieux. Le caractère aléatoire du nom ne
protège pas : les URLs circulent (notifications, journaux, historique du navigateur, partage) et
restent valides après la révocation des droits. C'est un sujet RGPD / loi 09-08, pas seulement
technique.

**Recommandation** :
1. Conteneur Azure **privé** ; URLs SAS courtes (5–15 min) générées à la sérialisation, idéalement via
   *user delegation SAS* (identité managée, pas de clé de compte).
2. Séparer deux classes de fichiers : *publics* (logos, photos de produits/annonces) éventuellement
   servis par CDN, et *privés* (tout le reste) jamais servis sans contrôle.
3. Ou, plus simple et plus strict : un endpoint `GET /files/{id}/` qui applique la policy de l'entité
   propriétaire puis redirige vers une SAS de courte durée.
4. Supprimer la route `media/` hors développement et faire échouer le démarrage en production si le
   stockage distant n'est pas configuré.

### S4 — Jetons non révocables (élevée)

- `password_changed_at` est enregistré (`apps/accounts/services/passwords.py:35`) mais n'est jamais lu :
  un jeton d'accès ou de rafraîchissement émis avant un changement ou une réinitialisation du mot de
  passe reste valide.
- `ROTATE_REFRESH_TOKENS=True` sans `rest_framework_simplejwt.token_blacklist` : l'ancien jeton de
  rafraîchissement reste utilisable après rotation. Combiné à 14 jours glissants, une session volée
  est de fait illimitée.
- Aucun endpoint de déconnexion.

**Recommandation** : activer `token_blacklist` avec `BLACKLIST_AFTER_ROTATION=True` ; ajouter
`POST /auth/logout/` (blacklist du refresh) ; ajouter au JWT une revendication `pwd_at` (ou un
compteur `token_version` sur `User`) et la comparer dans une classe d'authentification dérivée de
`JWTAuthentication` et dans le serializer de refresh. Réduire la durée du lien de réinitialisation
(72 h → 1 h pour une réinitialisation ; garder 72 h pour une invitation, avec un générateur distinct).

### S5 — Throttling contournable et non partagé (élevée)

- DRF identifie le client par `X-Forwarded-For` entier quand `NUM_PROXIES` n'est pas défini : un
  en-tête différent à chaque appel remet le compteur à zéro (vérifié : 30 réinitialisations sans 429).
- Le cache est `LocMemCache` (`config/settings.py:242`) : le quota est multiplié par le nombre de
  workers Gunicorn et de réplicas.
- Seul le scope `auth` est limité ; le reste de l'API n'a aucune limite (`DEFAULT_THROTTLE_CLASSES: []`).

**Recommandation** : `NUM_PROXIES = 1` (derrière l'ingress ACA, à valider au déploiement) ; cache Redis
(Azure Cache for Redis / Managed Redis) ; throttles `user` et `anon` globaux ; pour le login, un
throttle par identifiant (e-mail normalisé) en plus de l'IP pour freiner le credential stuffing.

### S6 — Secrets dans l'outbox, pas de rétention (élevée)

Le lien de réinitialisation est rendu dans le corps de l'e-mail (`apps/accounts/notices.py:43`) puis
stocké dans `OutboxMessage.payload`, qui n'est jamais purgé. Toute personne ayant accès en lecture à la
base ou à une sauvegarde peut prendre le contrôle d'un compte pendant la durée de validité du jeton.

**Recommandation** : vider `payload` (ou au moins le HTML/texte) au passage en `SENT`/`FAILED`, ou
ne stocker que les paramètres et rendre l'e-mail au moment de l'envoi ; purger l'outbox `SENT` après
quelques jours et l'inbox lue après une durée à définir (tâche dans `run_scheduled_jobs`).

### Autres points de sécurité

| Sévérité | Constat | Recommandation |
|---|---|---|
| Moyenne | `DATA_UPLOAD_MAX_MEMORY_SIZE = 50 Mo` : ce plafond concerne les corps **hors fichiers** chargés en mémoire | 2–5 Mo |
| Moyenne | `AccountService.close` n'efface que e-mail, nom, téléphone, mot de passe : restent genre, langue, jetons push, pièces d'identité téléversées, inbox, e-mails dans l'outbox | Lister toutes les données personnelles par table et les effacer dans `close()` ; tester l'exhaustivité |
| Moyenne | Pas de durée de conservation des pièces d'identité des visiteurs et locataires courte durée | Purge planifiée après départ + délai légal |
| Faible | `resolve_many` renvoie la liste des identifiants d'utilisateurs inexistants : énumération possible | Message générique |
| Faible | `SIGNING_KEY` par défaut = `SECRET_KEY` ; avertissement `InsecureKeyLengthWarning` en test | Clé JWT dédiée ≥ 32 octets, validée au démarrage en production |
| Faible | `ALLOWED_HOSTS='*'` par défaut hors production ; `DEBUG` déduit de `ENVIRONMENT` | Échouer au démarrage si `ENVIRONMENT` est absent ou inconnu |
| Faible | `create_default_superuser` à chaque démarrage avec un mot de passe issu de l'environnement | Commande ponctuelle (job), jamais au boot |

## 5. Fiabilité et logique métier

1. **Fuseau horaire unique (moyenne-élevée)** — `TIME_ZONE = UTC` par défaut et aucun fuseau par
   propriété. Les horaires d'ouverture des équipements (`bookings.py:101`), l'échéance des baux
   (`timezone.localdate()`), la clôture des sondages et les heures affichées dans les e-mails sont
   calculés en UTC. Au Maroc (devise par défaut `MAD`) l'écart est d'une heure, et le jour change à
   minuit UTC, pas à minuit local. Ajouter `Property.timezone` (IANA) et convertir à cet endroit, ou au
   minimum fixer `TIME_ZONE` au fuseau cible si le produit reste mono-pays.
2. **Administrateurs en copie de tout (moyenne)** — `include_platform_admins=True` par défaut
   (`dispatcher.py:60`) : chaque administrateur reçoit une ligne d'inbox et un e-mail pour **chaque**
   événement de **toutes** les propriétés. Inutilisable dès quelques dizaines de résidences, et coûteux
   en base. Passer le défaut à `False` et l'activer seulement sur les événements qui les concernent.
3. **Push en doublon (faible)** — un message push couvre tous les destinataires ; si le 2ᵉ lot Expo
   échoue en 5xx après le succès du 1ᵉʳ, tout le message est rejoué. Découper un `OutboxMessage` par
   lot de 100. Les *receipts* Expo ne sont jamais consultés.
4. **Appels réseau dans une transaction (faible)** — `OutboxRelay._deliver_one` garde la transaction
   et le verrou de ligne pendant l'appel SMTP/Expo (jusqu'à 20 s). Acceptable à faible volume ; à terme,
   réclamer la ligne (`status=SENDING`, `claimed_at`) puis envoyer hors transaction.
5. **Idempotence** — aucune clé d'idempotence sur les créations (commandes, réservations, demandes) :
   un client mobile qui rejoue un POST après une coupure crée un doublon. Un en-tête
   `Idempotency-Key` sur ces quelques routes suffit.
6. **Suppressions définitives** — plusieurs objets métier (demandes de service, etc.) sont supprimés
   physiquement ; le journal d'audit garde la trace, mais sans le contenu. À valider fonctionnellement
   (archivage vs suppression), notamment pour les litiges.

## 6. Performance et passage à l'échelle

- `AccessService` fait une requête `EXISTS` par question et ne met rien en cache ; une même requête
  HTTP repose souvent plusieurs fois les mêmes questions. Un cache par requête (dictionnaire sur
  l'acteur, ou `functools.cached_property` sur un objet `Actor`) supprimerait l'essentiel.
- `staff_property_ids` / `accessible_property_ids` matérialisent des ensembles Python, donc des
  `IN (…)` non bornés pour un administrateur. Préférer des sous-requêtes (`.values("id")`) partout.
- Les champs calculés des serializers utilisent déjà des annotations sur les listes : bon réflexe.
  Ajouter un test de nombre de requêtes (`django_assert_max_num_queries`) sur les listes principales
  pour figer cet acquis.
- `visible_filter` combine des `OR` sur des jointures (`assignments__resolver`) suivis de
  `.distinct()` : surveiller les plans d'exécution une fois des données réalistes chargées.

## 7. Qualité, outillage, documentation

- **CI absente** : le README affirme que « le CI vérifie » ruff, mais il n'y a pas de `.github/`.
  Première brique à ajouter : ruff, pytest sur un service PostgreSQL, `manage.py makemigrations --check`,
  génération du schéma OpenAPI avec `--fail-on-warn`, `pip-audit`/`uv` audit des dépendances.
- **Documentation désynchronisée** : le README cite `apps/common/attachments/rules.py`, qui n'existe
  pas (les règles sont dans `apps/common/models.py`) ; `scripts/startup.sh` lance `supervisord.conf`,
  absent du dépôt.
- **Typage** : annotations présentes mais aucun vérificateur. Ajouter `mypy` + `django-stubs` +
  `djangorestframework-stubs` en mode progressif (commencer par `common` et `accounts`).
- **Couverture** : pas de mesure. Ajouter `pytest-cov` en CI (seuil informatif d'abord).
- **Deux sources de dépendances** : `uv.lock` et `requirements.txt` exporté. Une fois l'image Docker
  construite avec `uv sync --frozen`, `requirements.txt` et `scripts/export_reqs.sh` deviennent inutiles.
- **Scripts** : `scripts/commit.sh` fait `git add .` puis pousse — risque d'ajouter des fichiers non
  voulus ; `local_run_install.sh` crée un administrateur avec une adresse en dur.
- **Migrations** : une seule migration initiale par app, ce qui est idéal tant que rien n'est
  déployé. À partir du premier déploiement, elles sont figées : ne plus jamais les régénérer.
- **Observabilité** : ni endpoint de santé, ni traces, ni identifiant de corrélation dans les logs.
  Voir section 8.

## 8. `api-contracts`

Le dossier est cohérent et à jour (snapshot OpenAPI identique au schéma généré, tests Node qui
valident des réponses réelles). Puisqu'il sera supprimé une fois l'API figée :

- Ne pas investir davantage dans les schémas Zod écrits à la main (≈ 5 500 lignes) : le frontend peut
  les **générer** depuis le schéma OpenAPI (`@hey-api/openapi-ts`, `orval` ou `openapi-zod-client`).
- Côté backend, garder la seule chose utile : le schéma OpenAPI versionné (`openapi.json` à la racine
  ou dans `docs/`) et un contrôle CI qui échoue si le schéma change sans mise à jour du fichier. C'est
  le contrat que le frontend consommera.
- Le schéma n'est servi qu'en `DEBUG` : c'est bien pour la production, mais il faut donc le publier
  comme artefact de build.
- À la suppression du dossier, déplacer `tests/test_api_contract_samples.py` ou le supprimer : il
  écrit dans `api-contracts/tests/samples.json`.

## 9. À préparer dans le code pour ACA (sans entrer dans le déploiement)

Ces points ne sont pas urgents, mais ils touchent le code et orientent la suite :

- **Un processus par conteneur** : `startup.sh` + `supervisord` (hérités d'App Service, `antenv`,
  `APP_PATH`) regroupent web, worker et planificateur. Sur ACA : une Container App `web` (Gunicorn),
  une Container App `worker` (`outbox_worker`, mise à l'échelle KEDA possible), et un **ACA Job**
  planifié (cron) pour `run_scheduled_jobs` et `purge_orphan_attachments`. Les migrations dans un Job
  manuel exécuté avant la bascule, pas au démarrage de chaque réplica.
- **Dockerfile** multi-étapes basé sur `uv sync --frozen --no-dev`, utilisateur non root.
- **Santé** : `/healthz` (processus vivant) et `/readyz` (base joignable) pour les sondes ACA.
- **Secrets** : `AZURE_CONNECTION_STRING` avec clé de compte → identité managée + `DefaultAzureCredential`
  (django-storages le supporte) ; secrets dans Key Vault référencés par ACA.
- **Cache partagé** : Redis, indispensable dès deux réplicas (throttling, S5).
- **Proxy** : `NUM_PROXIES`, `SECURE_PROXY_SSL_HEADER` et `ALLOWED_HOSTS` à caler sur l'ingress ACA.
- **Gunicorn** : `timeout = 220` et les commentaires visent App Service ; `cpu_count()` dans un
  conteneur renvoie les cœurs de l'hôte, pas le quota : fixer `GUNICORN_WORKERS` explicitement.
- **Observabilité** : `azure-monitor-opentelemetry` (traces, logs, métriques vers Application Insights),
  logs JSON.

## 10. Plan d'action proposé

| Ordre | Action | Effort |
|---|---|---|
| 1 | S3 : conteneur privé + SAS courtes (ou endpoint de téléchargement contrôlé), suppression de `serve` hors dev | M |
| 2 | S2 : extension dérivée du MIME détecté + `Content-Disposition` | S |
| 3 | S4 : `token_blacklist`, logout, invalidation au changement de mot de passe, durée du lien de reset | S–M |
| 4 | S1 : résolution centrale de la sélection dans `BaseAPIView`, `get_visible(prop=…)`, test sur toutes les routes | M |
| 5 | S5 / S6 : `NUM_PROXIES`, Redis, throttles globaux ; purge et nettoyage de l'outbox | S |
| 6 | CI (ruff, pytest, migrations, schéma OpenAPI, audit des dépendances) | S |
| 7 | Fuseau horaire par propriété ; administrateurs retirés des copies par défaut | M |
| 8 | Effacement RGPD exhaustif et durées de conservation des pièces d'identité | M |
| 9 | Préparation ACA (section 9) — lors de la phase déploiement | M |
| 10 | mypy progressif, couverture, tests de nombre de requêtes | S–M |

S = moins d'une journée, M = quelques jours.

## 11. Performance mesurée et refactor (après corrections)

**orjson.** Sur une liste de 100 demandes de service, le rendu JSON de DRF prend 0,31 ms pour une
requête de 32 ms ; orjson le fait en 0,03 ms. Le gain est réel (×10 sur le rendu) mais marginal sur la
requête (~1 %). Il est intégré (`apps/common/json.py`, sortie identique octet pour octet à DRF, testée),
sans dépendre de `drf-orjson-renderer`. Le temps d'une requête est dans les serializers et la base.

**Requêtes SQL.** Sur toutes les listes du schéma, le nombre de requêtes reste constant quand le nombre
de lignes augmente : pas de N+1. Les champs calculés utilisent des annotations et `AttachmentsField`
charge les fichiers d'une page en une requête.

**Découpage.** Un fichier = une responsabilité :

| Avant | Après |
|---|---|
| `common/models.py` (modèles de base, règles de fichiers, pièces jointes, audit) | `common/models/` (`base`, `attachments`, `audit`) et `common/files/` (`rules`, `formats`, `service`, `links`, `delivery`, `storage`, `serializers`, `views`) |
| `service_requests/services.py` (demande + tours) | `services/requests.py`, `services/rounds.py` (`RoundService`) |
| `library/services.py` | `services/folders.py`, `services/documents.py` |
| `surveys/services.py` | `services/surveys.py`, `services/participation.py` (`ParticipationService`) |
| `accounts/services/accounts.py` (création … fermeture) | `accounts.py` + `status.py` (`AccountStatusService`) |
| `accounts/serializers.py`, `properties/serializers.py` | paquets calqués sur `views/` |
| `views.py` de `leasing`, `amenities`, `store`, `short_term_rental` | paquets `views/` par ressource |
| `NotificationService.notify` (≈150 lignes) | étapes nommées : audience, inbox, push, e-mails, mise en file |
| `config/settings.py` | sections nommées ; lecture de l'environnement dans `config/env.py`, OpenAPI dans `config/openapi.py` |
