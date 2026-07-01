# GEMINI.md — MiroPolis, frontend (plateforme complète)

Ce fichier oriente Gemini sur le frontend. Le backend est piloté par Claude via CLAUDE.md — le
contrat d'API en section 4 de ce document est IDENTIQUE à CLAUDE.md §6. Ne jamais diverger sans
mettre à jour les deux fichiers.

## 0. À lire avant de commencer : état réel du backend (vérifié, pas supposé)

Le backend a été implémenté ET testé bout-en-bout (pas seulement écrit). Voici ce qui change
concrètement ta façon de coder le frontend :

- **Pour lancer le backend en local**, il y a **deux environnements Python distincts** :
  - `backend/.venv` (Python 3.12) : fait tourner le serveur Flask/API principal — c'est celui que
    tu utilises pour tester tes appels API.
  - `backend/.venv311` (Python 3.11) : dédié au sous-processus de simulation OASIS et au script de
    précalcul OpenFisca (`camel-oasis` et `openfisca-france` ne s'installent pas sous Python 3.12).
    Le serveur Flask le détecte et l'utilise automatiquement pour lancer les simulations — tu n'as
    normalement pas besoin d'y toucher, sauf si tu dois lancer toi-même
    `backend/scripts/precompute_openfisca.py` pour avoir des données `openfisca_indicator`
    réalistes en local.
- **Les données de composition des groupes parlementaires sont réelles et vérifiées en direct**
  (577 sièges, dataset officiel data.gouv.fr, pas Tricoteuses comme prévu initialement — l'endpoint
  Tricoteuses n'a jamais pu être confirmé publiquement). Ça ne change rien côté contrat d'API
  frontend, juste une info si tu vois `"source": "data.gouv.fr/an-groupes"` dans des logs/réponses
  internes.
- **La carte ne fonctionne qu'en granularité région pour l'instant** (13 régions), et **rien ne la
  génère automatiquement** après une simulation — voir détails en section 4. Construis
  `FranceMap.vue` pour gérer proprement l'état "pas encore de données" en priorité, avant de
  peaufiner le rendu avec de vraies données.
- **`openfisca_indicator.available: false` est l'état normal par défaut**, pas une erreur à
  masquer — la majorité des régions n'auront jamais de donnée calculée tant que le script de
  précalcul n'a pas tourné pour le scénario en cours.

## 1. Vision produit côté frontend

Une plateforme utilisée en continu par des députés/collaborateurs, pas une démo ponctuelle : gestion
de scénarios, comparaison de lois, carte territoriale fine (circonscription), moteur prospectif
visualisable dans le temps, module de transparence méthodologique (backtesting), comptes et
permissions, accessibilité RGAA obligatoire.

Plan de conception détaillé (historique des décisions, débats de conception) :
`C:\Users\talal\.claude\plans\now-you-understand-how-idempotent-parrot.md`.

## 2. Stack technique

- Vue 3 + Vite, Vue Router 4, Vue-i18n 11, **D3.js 7** (carte + visualisations temporelles/comparaison).
- Axios avec intercepteurs (`src/api/index.js`) — étendre pour gérer l'auth (JWT/session).
- **Évolution recommandée du state management** : passer de la `reactive()` minimale actuelle à
  **Pinia**, maintenant que l'app gère des comptes utilisateurs, des scénarios multiples et un état
  de comparaison — la justification n'est plus la simplicité d'un MVP mais la structuration d'une
  vraie application multi-vues avec état partagé complexe.

## 3. Inventaire des composants

### Base héritée de MiroFish (conservée, adaptée au vocabulaire)
`App.vue`, `main.js`, `router/index.js`, `i18n/index.js`, `LanguageSwitcher.vue`, `HistoryDatabase.vue`
(devient la bibliothèque de scénarios), `GraphPanel.vue` (reste le panneau de graphe de connaissances,
distinct de la carte géographique), `Step1GraphBuild.vue` à `Step5Interaction.vue` (deviennent les
étapes du constructeur de scénario, vocabulaire législatif).

### Nouveaux composants majeurs

- **`FranceMap.vue`** — carte D3 avec bascule de granularité région/circonscription (prop
  `granularity`), légende permanente à échelle qualitative discrète, distinction visuelle
  calculé (OpenFisca)/estimé (IA), surbrillance liée à une interview live en cours.
- **`ScenarioLibrary.vue`** — liste des scénarios sauvegardés, filtrable, avec statut de cycle de vie
  (brouillon/revu/publié).
- **`ComparisonDashboard.vue`** — vue de comparaison A/B/N : cartes côte à côte, graphiques d'écarts
  avec intervalles de confiance.
- **`ProspectiveTimeline.vue`** — visualisation des rounds du moteur temporel (frise chronologique,
  indicateurs qui évoluent, bascule tendanciel/rétrospectif, plusieurs trajectoires candidates
  affichables en rétrospectif).
- **`BacktestingDashboard.vue`** — tableau de bord de transparence méthodologique : métriques de
  calibration (taux d'accord simulé/réel), par groupe parlementaire, par type de texte.
- **`AdminUserManagement.vue`** — gestion des comptes/rôles (visible seulement aux rôles autorisés).
- **`PublishReviewPanel.vue`** — interface du workflow de revue humaine avant publication externe
  d'un scénario.

## 4. Contrat d'API (IDENTIQUE à CLAUDE.md §6) — mis à jour après implémentation et vérification réelle du backend (2026-07)

⚠️ Cette section a été corrigée après une première implémentation testée bout-en-bout (Flask +
DB + endpoints réels, pas seulement écrite sur le papier). Les écarts par rapport à la première
version du contrat sont signalés explicitement ci-dessous — lis-les avant de coder l'intégration,
ils évitent des heures de debug côté frontend.

### `GET /api/simulation/<id>/map-data?granularity=region|circonscription`

**⚠️ État réel vérifié : seule la granularité `region` (13 régions métropolitaines) est
implémentée côté backend pour le moment.** `circonscription` (DataCirco) n'est PAS encore
câblé — le paramètre est accepté par l'endpoint mais la réponse contiendra quand même
`"granularity": "region"` avec des données par région. **Le frontend doit :**
- Toujours traiter le champ `granularity` de la RÉPONSE comme la source de vérité (pas le
  paramètre qu'il a envoyé) — si `"granularity": "region"` revient alors que
  `circonscription` a été demandé, afficher la carte au niveau région sans erreur, pas un écran
  cassé.
- Ne pas construire de sélecteur "région/circonscription" qui laisse croire que les deux
  fonctionnent symétriquement tant que ce n'est pas vrai côté backend.

**⚠️ Clés canoniques confirmées (ne pas utiliser d'alias)** : chaque élément de `areas` utilise
**`code`** et **`name`** — jamais `region_code`/`region_name`/`area_code` (ces variantes ont
existé un temps côté backend pendant le développement et ont été supprimées pour éviter toute
ambiguïté ; si tu vois ces clés quelque part c'est un reliquat à ignorer, pas le contrat réel).

**⚠️ `openfisca_indicator.available` sera `false` sur toutes les régions tant que le script de
précalcul n'a pas été exécuté** (`backend/.venv311/Scripts/python.exe
backend/scripts/precompute_openfisca.py --scenario logement_apl`, exécuté hors ligne par
l'opérateur backend, jamais par le frontend). **C'est un état normal et attendu, pas une
erreur** — le frontend doit afficher proprement "pas de donnée calculée pour cette région"
plutôt que de masquer la carte ou afficher une erreur.

**⚠️ `confidence_interval` n'est PAS encore renvoyé par le backend actuel** (mentionné dans la
version précédente de ce contrat comme cible, mais pas implémenté à ce stade) — ne pas builder
l'UI de barre d'erreur sur `openfisca_indicator` en dur ; vérifier la présence du champ avant de
l'afficher (`if (indicator.confidence_interval) { ... }`), sinon afficher juste la valeur.

```json
{
  "granularity": "region",
  "areas": [
    {
      "code": "84",
      "name": "Auvergne-Rhône-Alpes",
      "qualitative_score": 1,
      "qualitative_score_scale": [-2, -1, 0, 1, 2],
      "openfisca_indicator": { "available": false },
      "archetype_count": 25,
      "top_archetypes": ["Employe", "Cadre", "Ouvrier"]
    }
  ],
  "disclaimer": "estimation exploratoire, distincte des données calculées — voir légende"
}
```

Exemple avec donnée calculée disponible (après exécution du script de précalcul) :
```json
"openfisca_indicator": { "available": true, "label": "Impact moyen calculé (OpenFisca)", "value": -34.2, "unit": "" }
```

**⚠️ Nouvel endpoint non prévu dans la version initiale du contrat, à intégrer** :
`POST /api/simulation/<id>/map-data/build` — déclenche la génération de `map_data.json` à partir
des marges démographiques régionales et des scores de débat. **Rien ne l'appelle
automatiquement à la fin d'une simulation pour le moment** (câblage automatique = TODO backend) ;
pour une démo, il faut soit un bouton "Générer la carte" côté opérateur/admin, soit ce endpoint
est appelé manuellement en amont. Tant qu'il n'a jamais été appelé pour une simulation donnée,
`GET .../map-data` renvoie `{"areas": [], "note": "aucune donnée cartographique pré-calculée..."}`
— état à gérer explicitement dans `FranceMap.vue` (écran vide propre, pas une erreur).

### Autres endpoints — état réel vérifié

- `/api/backtesting/runs`, `/api/temporal/scenario[...]`, `/api/comparison/runs[...]` : implémentés
  et testés, schémas conformes à la version précédente de ce document.
- `/api/scenarios/<id>/publish` : **refuse avec HTTP 409** si `/api/scenarios/<id>/review` n'a pas
  été appelé avant (comportement vérifié, pas juste documenté) — le frontend DOIT implémenter les
  deux étapes comme deux actions UI distinctes (bouton "Marquer comme revu" puis bouton "Publier",
  ce dernier grisé tant que le statut n'est pas `reviewed`), et afficher le message d'erreur du 409
  s'il arrive quand même (ex: appel concurrent).
- `/api/auth/login`, `/api/auth/register` : implémentés, retournent un JWT (`access_token`) à passer
  en `Authorization: Bearer <token>`. **Note dev** : `/review` et `/publish` acceptent actuellement
  les appels sans token (`jwt_required(optional=True)`, pratique en dev) — envoyer quand même le
  token dès qu'il est disponible, ce comportement permissif est amené à se resserrer.

### Fixtures de développement
Créer un dossier `src/mocks/` avec une fixture par endpoint, respectant exactement les schémas
ci-dessus (avec `openfisca_indicator.available: false` dans la majorité des cas de test, c'est
l'état réel le plus fréquent), pour développer chaque vue indépendamment de l'avancement backend.

## 5. Guidelines UX/design

- **Accessibilité RGAA obligatoire** : contrastes, navigation clavier, alternatives textuelles sur la
  carte (pas seulement une image/canvas sans équivalent accessible), attributs ARIA sur les composants
  interactifs.
- **Distinction visuelle systématique et cohérente** calculé/estimé, sur toute la plateforme (carte,
  rapport, comparaison, timeline).
- **Incertitude toujours visible** quand elle existe (barres d'erreur, fourchettes) — ne jamais
  simplifier vers un chiffre unique en UI alors que l'API renvoie un intervalle.
- **Vocabulaire institutionnel sobre**, jamais de jargon technique brut visible (identifiants internes,
  codes d'erreur, endpoints).
- **États de cycle de vie clairs** (brouillon/revu/publié) affichés de façon non ambiguë sur chaque
  scénario.

## 6. i18n

Structure existante conservée (`locales/*.json`), français prioritaire, les autres langues étendues au
même rythme que les nouvelles fonctionnalités plutôt qu'en rattrapage final.

## 7. Feuille de route frontend (alignée sur CLAUDE.md §8)

1. Fondations : migration vers Pinia, adaptation du wizard existant au vocabulaire législatif,
   `FranceMap.vue` en granularité région d'abord.
2. Simulation sociale : intégration des vues liées à la population synthétique et à la couche de vote.
3. Couche temporelle : `ProspectiveTimeline.vue`.
4. Comparaison multi-lois : `ComparisonDashboard.vue`, `FranceMap.vue` en granularité circonscription.
5. Produit complet : `ScenarioLibrary.vue`, `BacktestingDashboard.vue`, `AdminUserManagement.vue`,
   `PublishReviewPanel.vue`, passe complète d'accessibilité RGAA.

## 8. Coordination avec le backend (Claude)

Le contrat d'API de CLAUDE.md §6 fait autorité au même titre que ce document. Toute divergence
nécessaire doit être proposée et répercutée dans les deux fichiers avant implémentation, jamais
contournée localement côté frontend.
