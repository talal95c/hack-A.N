# GEMINI.md — MiroPolis ("MiroFish v2"), frontend

Ce fichier oriente Gemini sur le frontend. Le backend est piloté par Claude via CLAUDE.md — les
règles de la section 1 ci-dessous sont IDENTIQUES à CLAUDE.md, à la lettre. Ne jamais diverger sans
mettre à jour les deux fichiers en même temps.

---

## 1. Règles backend — à respecter à la lettre pour la cohérence

### 1.1 Définition de référence du produit (ne jamais s'en écarter)

> Les Députés IA : configurés selon la composition réelle de l'hémicycle et le programme de leur
> parti. Ils débattent, proposent des amendements et votent sur le texte soumis.
> Les Citoyens IA : un échantillon représentatif de la population (âge, profession, géographie).
> Ils réagissent aux débats et évaluent l'impact concret de la loi sur leur quotidien (pouvoir
> d'achat, environnement, services publics).
> Grâce à ce jumeau numérique, le législateur peut tester des formulations d'amendements pour
> maximiser le consensus ou identifier les angles morts d'une réforme.

### 1.2 Principes non négociables

- **Jamais d'élu nommé individuellement** — les "Députés" sont toujours des groupes parlementaires.
- **Vocabulaire imposé** : "estimation exploratoire" / "vote simulé", jamais "prédiction" présentée
  comme certaine ; "enrichissement par données réelles", jamais "calibration statistique".
- **Disclaimer visible** partout où un résultat de simulation/scénario est affiché : *"estimation
  qualitative générée par IA, ne reflète pas la position officielle des groupes parlementaires ni
  une prédiction fiable de vote réel."*
- **Zéro emoji dans l'interface.** Strictement interdit dans les boutons, titres, menus ou textes
  (⚡, 📑, 📄, 🚀, etc.) — interface architecturale, sobre, scientifique, purement textuelle/graphique.
- **Pas de DB, pas de compte, pas d'auth, pas de file de jobs.** Stockage fichier uniquement,
  identifiants passés de route en route (pas de liste globale interrogeable côté serveur).
- **Toute opération longue est asynchrone** : `POST .../generate|build|prepare|start` répond avec
  un `task_id` immédiatement ; poll un endpoint de statut toutes les ~2s jusqu'à `completed`/`failed`.
  Un seul mécanisme de polling générique suffit pour toutes les étapes (ontologie, graphe,
  préparation, simulation, rapport, scénario).
- **Deux agents indépendants en sortie de simulation**, jamais fusionnés en un seul objet :
  `ReportAgent` (recap, `report_id`) et `ScenarioAgent` (projection + vote simulé, `scenario_id`).
  Ils peuvent échouer/se terminer à des moments différents — gérer leur état séparément.

### 1.3 Ce qu'on A (fonctionnalités actives, à qui appartient quoi)

| Fonctionnalité | Endpoint(s) | Composant |
|---|---|---|
| Upload + ontologie | `POST /api/graph/ontology/generate`, `GET /api/graph/task/<id>` | `Step1GraphBuild.vue` |
| Construction du graphe | `POST /api/graph/build` | `Step1GraphBuild.vue` |
| Génération des agents (Députés/Citoyens) | `POST /api/simulation/create`, `/prepare`, `/prepare/status` | `Step2EnvSetup.vue` |
| Débat multi-agents (OASIS) | `POST /api/simulation/start`, `GET .../run-status`, `.../actions` | `Step3Simulation.vue` |
| Recap de la simulation | `POST /api/report/generate`, `/generate/status`, `GET /<report_id>` | `Step4Report.vue` |
| **Scénario tendanciel + vote simulé** | `POST /api/scenario/generate`, `/generate/status`, `GET /<scenario_id>`, `GET /by-simulation/<simulation_id>` | `Step4Scenario.vue` |
| Interview d'un agent précis | `POST /api/simulation/interview` | `Step5Interaction.vue` |

Le vote simulé (`vote_outcome` dans la réponse de `GET /api/scenario/<id>`) est pondéré par les
577 sièges réels des 12 groupes parlementaires (data.gouv.fr, vérifié) — `null` si le calcul a
échoué côté backend, à gérer proprement (pas d'erreur affichée, juste l'absence du bloc vote).

> Note sur "Débat multi-agents (OASIS)" : le design cible est une **plateforme unique** (Reddit,
> pour son action `CREATE_COMMENT`) plutôt que Twitter+Reddit en parallèle — voir Page 4 ci-dessous
> et CLAUDE.md §1. Implémentation pas encore faite ; `Step3Simulation.vue` tourne encore sur les
> deux plateformes historiques aujourd'hui.

### 1.4 Ce qu'on N'A PAS (ne jamais recoder sans demande explicite)

Comptes/auth/rôles, base de données, file de jobs (Celery), workflow de publication/revue,
comparaison de deux lois côte à côte, backtesting, carte de France, calcul OpenFisca, données par
circonscription (DataCirco). Tout ça a été construit une fois puis explicitement retiré (voir
CLAUDE.md §2 pour l'historique complet) — les fichiers correspondants ont déjà été supprimés du
frontend (`LoginView.vue`, `AdminView.vue`, `BacktestingView.vue`, `ComparisonView.vue`,
`ScenariosView.vue`, `ScenarioDetailView.vue`, et les composants/API associés). Si tu retrouves une
référence à l'un de ces noms quelque part, c'est un reliquat à supprimer, pas une fonctionnalité à
terminer.

---

## 2. Le circuit utilisateur, page par page

Un seul circuit linéaire (vérifié fichier par fichier, pas supposé). Chaque page correspond à une
route, une vue conteneur (`views/`) et un ou deux composants `Step*.vue` qu'elle héberge. Pour
chaque page : ce qu'elle affiche/fait, d'où on y arrive, vers où on peut repartir.

### Page 0 — Accueil (`/`, `Home.vue`)

**Contenu/fonction** : page d'entrée, aucun appel API. Un seul bouton d'action.
**On y arrive** : point de départ, ou clic sur le logo depuis n'importe quelle autre page.
**On peut aller vers** : `/process/new` (seul bouton présent).

### Page 1 — Nouveau scénario (`/process/new`, `NewScenarioWizardView.vue`)

**Contenu/fonction** : formulaire d'upload (dépôt de fichiers PDF/DOCX/TXT du texte de loi) + un
petit formulaire texte ("Réglages du scénario" : titre, groupe parlementaire "auteur" indicatif,
domaine de calcul — **champ obsolète référençant OpenFisca, retiré (§1.4), à nettoyer visuellement
plus tard**, objectifs prioritaires). Aucun appel API tant qu'on n'a pas soumis : les fichiers sont
stockés dans `store/pendingUpload.js`.
**On y arrive** : depuis `Home.vue` (seul point d'entrée) ou clic direct dans `MiroNavbar`.
**Action de sortie** : `launchSimulation()` remplit `pendingUpload` puis `router.push('/process/start')`
— qui matche la route dynamique `/process/:projectId` avec `projectId = 'start'`.
**On peut aller vers** : uniquement `/process/start` (pas de retour possible sauf via le logo).

### Page 2 — Construction du graphe (`/process/:projectId`, `MainView.vue` → `Step1GraphBuild.vue`)

**Contenu/fonction** : si `projectId` vaut `'new'` ou `'start'`, lit `pendingUpload`, appelle
`POST /api/graph/ontology/generate` (récupère le vrai `project_id`), puis `POST /api/graph/build`.
Affiche la progression (ontologie proposée : types d'entités = groupes parlementaires/archétypes
citoyens ; puis le graphe de connaissances construit, visualisé dans `GraphPanel.vue` à gauche).

**⚠️ Code mort à supprimer.** `MainView.vue` contient une branche `currentStep === 2` qui affiche
`Step2EnvSetup.vue` — **inatteignable en usage normal**, car le vrai bouton de sortie de
`Step1GraphBuild.vue` (fonction `handleEnterEnvSetup`, pas l'event `next-step`) ne passe jamais par
cet état : il appelle directement `POST /api/simulation/create` puis navigue vers la route
`Simulation` (page 3). `Step2EnvSetup.vue` tourne réellement à la page 3, pas ici. La branche
`currentStep === 2` dans `MainView.vue` (état `currentStep`, gestion `@next-step`/`@go-back` pour ce
cas précis) est du code mort à supprimer pour éviter toute confusion future entre les deux endroits
où `Step2EnvSetup.vue` semble utilisé.

**On y arrive** : depuis la page 1 (upload initial), ou en revenant en arrière depuis la page 3.
**On peut aller vers** : `/simulation/:simulationId` (page 3, une fois le graphe construit) ou `/`.

### Page 3 — Génération des agents (`/simulation/:simulationId`, `SimulationView.vue` → `Step2EnvSetup.vue`)

**Contenu/fonction** : c'est ici, et seulement ici, que `Step2EnvSetup.vue` tourne réellement.
Appelle `POST /api/simulation/prepare` (génère les profils Députés/Citoyens à partir des données
réelles Tricoteuses/data.gouv.fr/INSEE, cf. §1.1), poll `POST /api/simulation/prepare/status`,
affiche la liste des agents générés (`GET /api/simulation/<id>/profiles`). Permet de configurer le
nombre de rounds (`maxRounds`) avant de lancer le débat.
**On y arrive** : depuis la page 2 (fin de construction du graphe).
**On peut aller vers** : retour à `/process/:projectId` (page 2, `handleGoBack`) ; ou avancer vers
`/simulation/:simulationId/start` (page 4, `handleNextStep`, avec `maxRounds` en query param).

### Page 4 — Débat multi-agents (`/simulation/:simulationId/start`, `SimulationRunView.vue` → `Step3Simulation.vue`)

**Contenu/fonction** : lance `POST /api/simulation/start`, poll `GET .../run-status` et `.../actions`
pour afficher le débat en temps réel (amendements proposés, soutiens/oppositions des groupes,
réactions des archétypes citoyens). Moteur OASIS en sous-processus (`.venv311`, transparent ici).

**Cible de design (implémentation à venir, cf. CLAUDE.md §1)** : un **flux unique** au lieu de deux
panneaux de plateformes parallèles ("Info Plaza"/"Topic Community") — une seule plateforme OASIS
(Reddit, pour son action `CREATE_COMMENT`) où les Députés publient leurs propositions d'amendement
et les Citoyens réagissent en commentaire. Aucune restriction technique dure sur qui peut publier ;
le cadrage vient du prompt de persona de chaque agent. Tant que cette passe de code n'est pas faite,
`Step3Simulation.vue` affiche encore les deux plateformes historiques.
**On y arrive** : depuis la page 3 (lancement de la simulation).
**Action de sortie (déjà câblée, `Step3Simulation.vue`, `handleNextStep`)** : une fois le débat
terminé, appelle `POST /api/report/generate` (`force_regenerate: true`), récupère `report_id`, puis
`router.push({ name: 'Report', params: { reportId } })`.
**On peut aller vers** : `/report/:reportId` (page 5) en sortie normale ; retour arrière possible
vers `/simulation/:simulationId` (page 3).

### Page 5 — Résultats : recap + scénario tendanciel (`/report/:reportId`, `ReportView.vue`)

**Contenu/fonction** : page à deux onglets, tous deux alimentés par le `simulation_id` résolu depuis
`reportId` (`GET /api/report/<reportId>` → `simulation_id` → `GET /api/simulation/<id>` →
`project_id` → graphe affiché à gauche via `GraphPanel.vue`) :
- Onglet "Synthèse des Débats" (`Step4Report.vue`) : le recap déjà généré au moment de la navigation
  depuis la page 4 (5 sections : synthèse décideur, cartographie des parties prenantes, réactions et
  positions observées, points de blocage, recommandations).
- Onglet "Projection dans le temps" (`Step4Scenario.vue`) : **pas généré automatiquement** — bouton
  "Générer" qui appelle `POST /api/scenario/generate` sur le même `simulation_id`. Affiche ensuite 3
  sections (état actuel observé, trajectoire tendancielle, points de bascule) **et le vote simulé
  pondéré par sièges réels** (décompte par groupe parlementaire, résultat adopté/rejeté/incertain).

**On y arrive** : depuis la page 4 automatiquement (recap déjà en cours de génération à l'arrivée).
**On peut aller vers** : `/interaction/:reportId` (page 6) ; `/` (logo).

### Page 6 — Interaction profonde (`/interaction/:reportId`, `InteractionView.vue` → `Step5Interaction.vue`)

**Contenu/fonction** : même résolution `reportId` → `simulation_id` qu'à la page 5. Permet de choisir
un agent précis (Député d'un groupe, ou archétype citoyen) et de lui poser une question en direct
(`POST /api/simulation/interview`, `simulation_id` + `agent_id` + `question`) — réponse générée avec
la persona de l'agent.
**On y arrive** : depuis la page 5 uniquement.
**On peut aller vers** : `/` (logo) ; dernière étape du circuit, pas de suite.

### Schéma récapitulatif

```
Home (/)
  -> NewScenarioWizard (/process/new)                     [upload + reglages texte]
    -> Process (/process/:projectId)                       [Step1GraphBuild : ontologie + graphe]
      -> Simulation (/simulation/:simulationId)             [Step2EnvSetup : generation agents]
        -> SimulationRun (/simulation/:simulationId/start)  [Step3Simulation : debat OASIS]
          -> Report (/report/:reportId)                     [Step4Report + Step4Scenario, 2 onglets]
            -> Interaction (/interaction/:reportId)         [Step5Interaction : interview]
```

Chaque flèche est un `router.push` réel déjà présent dans le code (vérifié fichier par fichier), à
l'exception de la suppression de code mort mentionnée à la Page 2.

---

## 3. Contrat d'API (identique à CLAUDE.md §7)

### Hérité, inchangé
`/api/graph/ontology/generate`, `/api/graph/build`, `/api/graph/task/<id>`,
`/api/simulation/create`, `/prepare`, `/prepare/status`, `/start`, `/<id>/run-status`,
`/<id>/actions`, `/<id>/profiles`, `/interview` ; `/api/report/generate`, `/generate/status`
(POST), `/<report_id>`.

### Agent de scénario tendanciel
- `POST /api/scenario/generate` — `{simulation_id, force_regenerate?}` → `{scenario_id, task_id, status}`.
- `POST /api/scenario/generate/status` — `{task_id}` ou `{simulation_id}` → statut de tâche.
- `GET /api/scenario/<scenario_id>` →
  ```json
  {
    "scenario_id": "...", "simulation_id": "...", "status": "completed", "title": "...",
    "sections": [{"title": "...", "content": "..."}],
    "vote_outcome": {
      "total_seats": 577, "support_seats": 300, "oppose_seats": 200,
      "abstain_seats": 30, "undecided_seats": 47,
      "outcome": "adopted", "majority_threshold": 251,
      "by_group": [{"group_name": "EPR", "seats": 91, "position": "support"}]
    },
    "error": null, "created_at": "...", "completed_at": "..."
  }
  ```
  `vote_outcome` peut être `null` — toujours vérifier sa présence avant d'afficher le bloc vote
  (`Step4Scenario.vue` le fait déjà correctement, à reproduire si le composant est modifié).
- `GET /api/scenario/by-simulation/<simulation_id>` → dernier scénario généré pour cette simulation.

## 4. i18n

Structure existante conservée (`locales/*.json`), français prioritaire.

## 5. Coordination avec le backend (Claude)

CLAUDE.md fait autorité au même titre que ce document sur les règles de la section 1. Avant de
construire un nouvel écran, vérifier qu'il correspond à une ligne du tableau §1.3 (ce qu'on a) — si
ce n'est pas le cas, c'est probablement une fonctionnalité du §1.4 (ce qu'on n'a pas), à ne pas
recoder sans demande explicite.
