# GEMINI.md — MiroPolis ("MiroFish v2"), frontend

Ce fichier oriente Gemini sur le frontend. Le backend est piloté par Claude via CLAUDE.md — le
contrat d'API en section 6 de ce document est IDENTIQUE à CLAUDE.md §6. Ne jamais diverger sans
mettre à jour les deux fichiers.

## 0. À lire en premier — le backend a été recadré, du code frontend est orphelin

Le backend est passé par plusieurs itérations : une version complète à 7 couches (DB, auth,
comparaison de lois, backtesting, carte de France, moteur temporel à rounds) a été **entièrement
retirée**. Le backend actuel est volontairement proche de MiroFish original + un agent en plus. En
regardant le code déjà présent dans `frontend/src/`, plusieurs fichiers correspondent à l'ancienne
version 7-couches et **n'ont plus d'endpoint backend derrière eux** :

| Fichier frontend existant | Statut |
|---|---|
| `src/api/auth.js`, `src/store/auth.js`, `src/views/LoginView.vue` | **Orphelin** — plus de `/api/auth/*` côté backend, plus de comptes/JWT |
| `src/api/admin.js`, `src/views/AdminView.vue`, `src/components/AdminUserManagement.vue` | **Orphelin** — pas de gestion d'utilisateurs |
| `src/api/backtesting.js`, `src/views/BacktestingView.vue`, `src/components/BacktestingDashboard.vue` | **Orphelin** — backtesting retiré |
| `src/api/comparison.js`, `src/views/ComparisonView.vue`, `src/components/ComparisonDashboard.vue` | **Orphelin** — comparaison de lois retirée |
| `src/api/map.js`, `src/components/FranceMap.vue` | **Orphelin** — carte de France retirée, plus de `/map-data` |
| `src/api/scenarios.js` (`reviewScenario`, `publishScenario`, `listScenarios`) | **Orphelin** — plus de workflow de publication ni de DB de scénarios |
| `src/api/temporal.js` (`getTemporalRounds`, `compareScenarios`, `getBacktestingRuns`, `getUsers`, `updateUserRole`) | **Orphelin en totalité** — l'ancien moteur temporel à rounds/DB n'existe plus |
| `src/components/ProspectiveTimeline.vue`, `PublishReviewPanel.vue`, `ScenarioLibrary.vue` | **À revoir** — conçus pour l'ancien contrat, ne correspondent plus à `/api/scenario/*` (voir §5) |

**Ne pas continuer à développer ces écrans.** Le nouvel agent de scénario tendanciel (§4-6) a un
contrat radicalement plus simple (3 sections de texte, pas de rounds/DB/comparaison) — il faut soit
adapter `ProspectiveTimeline.vue` en un affichage de sections narratives simple (comme
`Step4Report.vue` affiche déjà le rapport), soit en écrire un nouveau composant léger.

### 0bis. Il existe actuellement DEUX circuits de navigation en parallèle, un seul doit survivre

En traçant les `router.push` réels dans le code (pas en supposant), il y a deux chaînes de pages
distinctes et déconnectées :

- **Circuit A (hérité de MiroFish, fonctionnel)** : `Home` → `Process` (`/process/:projectId`) →
  `Simulation` (`/simulation/:simulationId`) → `SimulationRun`
  (`/simulation/:simulationId/start`) → ... puis plus rien (voir plus bas).
- **Circuit B (construit pour l'ancienne version 7-couches, orphelin)** : `Home` → `/scenarios`
  (`ScenariosView` + `ScenarioLibrary.vue`, qui appelle `listScenarios()` → un endpoint qui n'existe
  plus) → `/process/new` (`NewScenarioWizardView`) → `/scenario-detail/:scenarioId`
  (`ScenarioDetailView`, un dashboard à onglets avec carte territoriale et "moteur OpenFisca" —
  fonctionnalités retirées).

**Les deux boutons de la page d'accueil (`Home.vue`) pointent aujourd'hui vers le Circuit B**
(`$router.push('/scenarios')` et `$router.push('/comparison')`) — c'est-à-dire que le parcours
réellement fonctionnel (Circuit A) n'a **plus aucun point d'entrée visible** depuis la landing page
actuelle.

**Décision à appliquer : garder le Circuit A, supprimer/ignorer le Circuit B.** C'est le circuit
hérité de MiroFish, le plus proche de ce que le backend expose réellement. Voir §3 pour le circuit
cible détaillé et la liste des corrections de navigation à appliquer.

Par ailleurs, **`getReportStatus` dans `src/api/report.js` appelle l'endpoint en `GET`, mais le
backend l'expose en `POST`** (`@report_bp.route('/generate/status', methods=['POST'])`, corps JSON
`{task_id, simulation_id}`, pas des query params). C'est un vrai bug à corriger, pas une évolution
de contrat.

## 1. Vision

MiroPolis garde l'architecture MiroFish : upload d'un texte de loi → construction d'un graphe de
connaissances → génération d'agents (Députés = groupes parlementaires réels, Citoyens = archétypes
INSEE) → simulation multi-agents (débat) → **deux agents indépendants** consomment le résultat :
un agent de **recap** (`ReportAgent`, existant) et un agent de **scénario tendanciel**
(`ScenarioAgent`, nouveau).

## 2. Architecture du site

### Frontend (Vue 3 + Vite + Vue Router 4)

```
src/
├── views/           # une vue par route (voir §3 pour le circuit complet)
├── components/      # composants réutilisés par plusieurs vues (Step1..Step5, GraphPanel, etc.)
├── api/             # un fichier par ressource backend, chaque fonction = un appel axios
├── store/           # état partagé minimal (reactive(), pas de Pinia)
└── i18n/            # locales/*.json, français prioritaire
```

Chaque étape du parcours (§3) est un **composant `StepN...vue`** monté dans une vue conteneur
(`MainView.vue`/`Process.vue`, `SimulationView.vue`, etc.) qui gère la navigation entre étapes et
conserve l'état de la session (project_id, simulation_id, report_id, scenario_id) soit en props de
route, soit dans `store/pendingUpload.js` / `store/simulation.js`.

### Backend (Flask, fichiers, pas de DB)

```
backend/
├── app/
│   ├── api/            # blueprints Flask : graph.py, simulation.py, report.py, scenario.py
│   ├── services/        # logique métier (voir §4)
│   ├── models/          # Project, Task -- dataclasses sérialisées en JSON, PAS de DB
│   └── config.py
├── uploads/              # LE stockage réel de l'application
│   ├── projects/<project_id>/          # texte de loi, ontologie, project.json
│   ├── simulations/<simulation_id>/    # profils d'agents, config, logs OASIS, run_state.json
│   ├── reports/<report_id>.json        # sortie du ReportAgent (recap)
│   └── scenarios/<scenario_id>.json    # sortie du ScenarioAgent (nouveau)
└── .venv311/             # environnement Python 3.11 dédié au sous-processus OASIS
                           # (camel-oasis incompatible Python 3.12) -- transparent pour le frontend,
                           # mentionné ici seulement pour comprendre pourquoi la simulation tourne
                           # dans un sous-processus séparé avec ses propres logs.
```

**Aucune base de données.** Chaque identifiant (`project_id`, `simulation_id`, `report_id`,
`scenario_id`) correspond à un dossier ou fichier JSON sur disque. Une conséquence directe pour le
frontend : **il n'y a pas de liste globale de "tous les scénarios d'un utilisateur"** (pas de
compte, pas de DB à interroger) — la navigation se fait uniquement via les identifiants passés de
route en route (`project_id` → `simulation_id` → `report_id`/`scenario_id`).

**Toute opération longue (ontologie, graphe, simulation, rapport, scénario) est asynchrone** : un
`POST .../generate` (ou `.../build`, `.../prepare`, `.../start`) répond immédiatement avec un
`task_id`, pendant qu'un thread tourne en fond côté serveur. Le frontend doit **poller** un endpoint
de statut toutes les ~2 secondes jusqu'à `status: "completed"` ou `"failed"`. C'est le même pattern
partout (ontologie, graphe, préparation, simulation, rapport, scénario) — un seul mécanisme de
polling générique côté frontend suffit pour toutes ces étapes.

## 3. Le circuit cible — routes, déclencheurs de navigation, paramètres

Focus uniquement sur la **logique de navigation** (quelle route, quel `router.push`, quels
paramètres/props passent d'une page à l'autre) — pas de design, pas d'UI. Circuit A (§0bis),
inspiré du parcours MiroFish d'origine.

### Table des routes cibles

| # | Route | Nom | Composant(s) | Param requis pour entrer |
|---|---|---|---|---|
| 0 | `/` | `Home` | `Home.vue` | aucun |
| 1-2 | `/process/:projectId` | `Process` | `MainView.vue` → `Step1GraphBuild.vue` puis `Step2EnvSetup.vue` (état interne, pas de sous-route) | `projectId` |
| 3 | `/simulation/:simulationId` | `Simulation` | `SimulationView.vue` → `Step3Simulation.vue` (écran de préparation/lancement) | `simulationId` |
| 3bis | `/simulation/:simulationId/start` | `SimulationRun` | `SimulationRunView.vue` (suivi temps réel du débat) | `simulationId`, query `maxRounds?` |
| 4 | `/results/:simulationId` **(à créer, remplace `/report/:reportId`)** | `Results` | `ReportView.vue` (à renommer/adapter) | `simulationId` — **pas** `reportId`/`scenarioId`, voir plus bas pourquoi |
| 5 | `/interaction/:simulationId` **(param à corriger, voir plus bas)** | `Interaction` | `InteractionView.vue` | `simulationId` |

### Déclencheurs de navigation, étape par étape

**Étape 0 → 1.** Sur `Home.vue`, l'utilisateur dépose un fichier + décrit son besoin
(`simulation_requirement`), stockés dans `store/pendingUpload.js`. Le clic sur le bouton principal
déclenche `POST /api/graph/ontology/generate`, puis `router.push({ name: 'Process', params: {
projectId: res.data.project_id } })` — **`MainView.vue` fait déjà exactement ça à la ligne 218**
(`router.replace({ name: 'Process', params: { projectId: res.data.project_id } })`), il faut juste
que ce soit CE flux que les boutons de `Home.vue` déclenchent, pas `$router.push('/scenarios')`.

**Étape 1 → 2.** Interne à `MainView.vue`/`Process.vue` : pas de changement de route, juste un
changement d'étape affichée (`Step1GraphBuild.vue` puis `Step2EnvSetup.vue`) une fois
`POST /api/graph/build` terminé.

**Étape 2 → 3.** Une fois les agents générés (`POST /api/simulation/prepare` terminé,
`simulation_id` connu), navigation vers `Simulation` avec `simulationId` en param — c'est le rôle de
`SimulationView.vue` de gérer le lancement effectif ensuite.

**Étape 3 → 3bis.** Déjà implémenté correctement dans `SimulationView.vue` (`handleNextStep`,
ligne ~152) : `router.push({ name: 'SimulationRun', params: { simulationId:
currentSimulationId.value }, query: { maxRounds } })`.

**Étape 3bis → 4 — TRANSITION MANQUANTE, à ajouter.** `SimulationRunView.vue` n'a **aucune**
navigation sortante vers une page de résultat (vérifié : un seul `router.push` dans tout le fichier,
qui revient en arrière vers `Simulation`). Il faut ajouter : une fois
`GET /api/simulation/<id>/run-status` indique la simulation terminée, afficher un bouton "Voir les
résultats" qui fait `router.push({ name: 'Results', params: { simulationId:
currentSimulationId.value } })`.

**Pourquoi la route de résultat doit être keyée par `simulationId` et pas `reportId`.** La route
actuelle `/report/:reportId` (`ReportView.vue`) suppose qu'on a déjà un `report_id` en arrivant —
mais à la sortie de l'étape 3bis, on n'a que le `simulation_id` ; le `report_id` (et le
`scenario_id`) ne sont créés qu'au moment où `POST /api/report/generate` /
`POST /api/scenario/generate` sont appelés. Il faut donc que la page de résultat parte de
`simulation_id`, appelle `GET /api/report/by-simulation/:simulationId` et
`GET /api/scenario/by-simulation/:simulationId` pour savoir si un recap/scénario existe déjà
(sinon proposer de les générer), plutôt que d'exiger un id qu'on n'a pas encore. C'est la même
page qui gère les deux générations en parallèle (recap = `ReportAgent`, scénario tendanciel =
`ScenarioAgent`), pas deux routes séparées — les deux se lancent et se pollent indépendamment,
mais restent affichés sur un seul écran puisqu'ils partagent le même `simulation_id` de contexte.

**Étape 4 → 5.** Une fois au moins le recap disponible (`interview_unlocked` déjà renvoyé par
`GET /api/report/check/<simulation_id>` dans le backend existant), navigation vers `Interaction`
avec `simulationId` en param — **pas `reportId`** comme le fait la route actuelle
(`/interaction/:reportId`), pour la même raison qu'au point précédent : `Step5Interaction.vue` a
besoin de `simulation_id` pour interroger les agents (`POST /api/simulation/interview` prend
`simulation_id`, pas un `report_id`).

**Navigation retour.** Chaque vue a déjà un lien "MIROFISH" en haut qui ramène à `/` — cohérent,
à garder. `SimulationView.vue`/`SimulationRunView.vue` ont déjà un retour vers l'étape précédente
avec les bons params — pattern à répliquer sur les nouvelles transitions.

### Résumé des corrections de navigation à appliquer

1. `Home.vue` : les CTA doivent lancer le flux d'upload (Étape 0→1), pas pointer vers
   `/scenarios`/`/comparison`.
2. `SimulationRunView.vue` : ajouter la navigation sortante vers `Results` en fin de simulation
   (actuellement absente).
3. Renommer/recadrer la route résultat pour qu'elle prenne `simulationId`, pas `reportId`.
4. `InteractionView.vue`/route `/interaction/:id` : même correction, `simulationId` pas `reportId`.
5. Retirer les routes/vues du Circuit B de `router/index.js` une fois le Circuit A vérifié
   fonctionnel (`/scenarios`, `/scenario-detail/:scenarioId`, `/comparison`, `/backtesting`,
   `/admin`, `/login`, `/process/new`) — ou au minimum ne plus les lier depuis `Home.vue`.

## 4. Règles du backend à connaître (même si tu ne touches pas le code Python)

- **Pas de compte, pas d'auth, pas de rôle.** Retirer l'injection du header `Authorization` dans
  `src/api/index.js` n'est pas urgent (elle est juste ignorée côté serveur) mais ne pas construire
  de flux de connexion.
- **Les deux agents (Report/Scenario) peuvent échouer indépendamment** (LLM manquant, graphe vide,
  etc.) — toujours gérer leur état séparément côté UI (l'un peut être `completed` pendant que l'autre
  est `failed` ou pas encore lancé).
- **Vocabulaire imposé** (CLAUDE.md §2) : "estimation exploratoire" jamais "prédiction" ; jamais
  d'élu nommé individuellement, seulement des groupes parlementaires.
- **Disclaimer visible** sur le recap ET sur le scénario tendanciel : *"estimation qualitative
  générée par IA, ne reflète pas la position officielle des groupes parlementaires ni une prédiction
  fiable de vote réel."*
- **Zéro Emoji dans l'interface (UI) :** STRICTEMENT INTERDIT d'utiliser des emojis (⚡, 📑, 📄, 🚀, etc.) dans les boutons, titres, menus ou textes. L'interface doit maintenir un design architectural, sobre, scientifique et purement textuel/graphique.

## 5. Composants existants — statut

| Composant | Statut |
|---|---|
| `Step1GraphBuild.vue`, `Step2EnvSetup.vue`, `Step3Simulation.vue`, `Step5Interaction.vue` | Bons, alignés avec le backend actuel |
| `Step4Report.vue` | Bon pour le recap (4a) — à dupliquer/étendre pour afficher aussi le scénario tendanciel (4b) à côté |
| `GraphPanel.vue`, `HistoryDatabase.vue`, `LanguageSwitcher.vue`, `MiroNavbar.vue` | Inchangés |
| `ProspectiveTimeline.vue` | À réécrire simple (3 sections de texte, pas de rounds) ou remplacer par un rendu façon `Step4Report.vue` |
| `AdminUserManagement.vue`, `BacktestingDashboard.vue`, `ComparisonDashboard.vue`, `FranceMap.vue`, `PublishReviewPanel.vue`, `ScenarioLibrary.vue` | Orphelins (§0), ne pas continuer à les développer |

## 6. Contrat d'API (IDENTIQUE à CLAUDE.md §6)

### Hérité, inchangé
`/api/graph/ontology/generate`, `/api/graph/build`, `/api/graph/task/<id>`,
`/api/simulation/create`, `/prepare`, `/prepare/status`, `/start`, `/<id>/run-status`,
`/<id>/actions`, `/<id>/profiles`, `/interview` ; `/api/report/generate`, `/generate/status`
(**POST**, pas GET), `/<report_id>`.

### Nouveau : agent de scénario tendanciel
- `POST /api/scenario/generate` — `{simulation_id, force_regenerate?}` → `{scenario_id, task_id, status}`.
- `POST /api/scenario/generate/status` — `{task_id}` ou `{simulation_id}` → statut de tâche (même
  forme que `/api/report/generate/status`).
- `GET /api/scenario/<scenario_id>` → `{scenario_id, simulation_id, status, title, sections: [{title, content}], error, created_at, completed_at}`.
- `GET /api/scenario/by-simulation/<simulation_id>` → dernier scénario généré pour cette simulation
  (utile pour éviter de regénérer si déjà fait, même logique que `ReportManager.get_report_by_simulation`).

Pas de champ exotique (pas de score OpenFisca, pas de carte, pas de rounds/variance) — `sections`
est une liste de texte à afficher comme le rapport de recap.

## 7. i18n

Structure existante conservée (`locales/*.json`), français prioritaire.

## 8. Coordination avec le backend (Claude)

Le contrat d'API de CLAUDE.md §6 fait autorité au même titre que ce document. Avant de développer un
écran, vérifier dans ce fichier (§0 et §5) s'il correspond à une fonctionnalité encore active côté
backend — plusieurs itérations ont ajouté puis retiré des pans entiers de la plateforme, mieux vaut
vérifier que supposer.
