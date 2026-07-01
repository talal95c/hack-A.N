# CLAUDE.md — MiroPolis (plateforme complète, fork MiroFish)

Ce fichier oriente Claude sur l'ensemble du projet : vision, architecture, principes non négociables,
backend, et contrat d'API partagé avec le frontend (piloté par Gemini via GEMINI.md).
Toute divergence entre ce fichier et GEMINI.md sur le contrat d'API doit être corrigée immédiatement
dans les deux fichiers.

## 1. Vision

MiroPolis est un jumeau numérique exploratoire de l'Assemblée Nationale et de la société française,
fork de MiroFish, conçu comme une **plateforme utilisée en continu** (pas une démo ponctuelle) par
des députés et leurs collaborateurs pour tester l'impact d'un texte de loi avant son examen :
construire un scénario, le comparer à des variantes, l'interroger en direct, en tirer une trajectoire
prospective, publier un rapport dont la rigueur méthodologique est vérifiable (backtesting), pas
seulement déclarée.

Trois axes fusionnés :
1. **Données réglementaires spatialisées** (Tricoteuses, OpenFisca/LexImpact, data.gouv.fr, DataCirco).
2. **Couche prospective complète** (tendancielle et rétrospective/backcasting, multi-rounds).
3. **MiroPolis** : simulation multi-agents (Députés IA par groupe parlementaire, Citoyens IA sur
   population synthétique représentative).

Plan de conception détaillé (historique des décisions, débats de conception) :
`C:\Users\talal\.claude\plans\now-you-understand-how-idempotent-parrot.md`.

## 2. Principes non négociables (justifiés par l'éthique/le droit/la méthode, pas par le calendrier)

- **Jamais d'élu nommé individuellement en sortie publique.** Les votes/amendements individuels réels
  (Tricoteuses) sont exploités en interne uniquement, pour le backtesting et la calibration — jamais
  affichés comme "ce député votera X".
- **Tout code de règle légale généré automatiquement (pipeline OpenFisca) passe par une validation
  humaine avant usage.** Un LLM qui traduit un article de loi en paramètre fiscal exécutable est une
  aide à la traduction, pas une source de vérité autonome.
- **Toute publication externe d'un résultat de simulation passe par un workflow de revue humaine**
  (état de cycle de vie explicite sur un scénario : brouillon → revu → publié).
- **Distinction permanente et visible entre donnée calculée (OpenFisca) et donnée estimée (agents
  LLM)** — jamais fusionnées sans étiquette.
- **Aucune incertitude cachée** : tout indicateur issu de simulation est accompagné d'une variance
  (calculée par runs en ensemble), jamais un chiffre ponctuel présenté comme certain.
- **Conformité RGPD et accessibilité RGAA** sont des exigences produit, pas des options.
- **Vocabulaire imposé** : "enrichissement/calcul par données réelles" (jamais "calibration
  statistique" abusive) ; "estimation exploratoire" (jamais "prédiction de vote").

## 3. Architecture en 7 couches

### Couche 1 — Données réglementaires spatialisées
- **Tricoteuses** : client GraphQL live vers `assemblee.tricoteuses.fr` (composition des groupes,
  historique de votes/amendements, dossiers législatifs). Synchronisation périodique versionnée par
  législature, pas un cache figé unique.
- **OpenFisca-France (via l'approche LexImpact)** : pipeline `loi → règle calculable` :
  1. Extraction LLM des changements paramétriques candidats du texte de loi.
  2. Rapprochement avec un dictionnaire de correspondance entretenu vers les paramètres
     OpenFisca-France connus (+ fuzzy matching pour les cas ambigus).
  3. Simulation sur une batterie de cas types représentatifs (pondérés INSEE).
  4. **Étape de validation humaine obligatoire** avant que le résultat entre dans un scénario publiable.
- **data.gouv.fr (serveur MCP officiel)** : requêtes live pour tout jeu de données pertinent
  (artificialisation des sols/ZAN via Cerema, budgets carbone, emploi territorial).
- **DataCirco** : données agrégées par circonscription électorale — c'est la granularité cible pour
  la carte, la région n'est qu'un niveau de repli.

### Couche 2 — Simulation sociale (MiroPolis, échelle réelle)
- **Population synthétique de citoyens** générée par calage par marges (iterative proportional
  fitting) sur les distributions croisées réelles INSEE (âge × CSP × région × revenu) — un vrai actif
  méthodologique, pas un simple gonflage du nombre d'agents.
- **Députés IA** : un agent par groupe parlementaire en sortie publique ; modélisation interne plus
  fine (rapporteurs, tendances internes) possible, toujours agrégée avant affichage externe.
- **Couche de vote agrégée** au-dessus du débat OASIS natif (post/comment/like) : simule une
  majorité/minorité réelle en respectant les poids de sièges par groupe.
- **Module de backtesting** : rejoue d'anciens textes de loi (débats pré-vote réels via Tricoteuses),
  compare le résultat simulé au vote historique réel, publie des métriques de calibration/exactitude
  dans un tableau de bord dédié (voir couche 7).

### Couche 3 — Temporelle (moteur prospectif complet)
- Moteur multi-rounds (chaque round = une période), état et mémoire d'agent conservés entre rounds
  via la mémoire temporelle de graphe déjà présente dans MiroFish (`zep_graph_memory_updater.py`).
- **Mode tendanciel** : simulation en avant sous la politique actuelle, N périodes.
- **Mode rétrospectif/backcasting** : recherche de trajectoires de décisions plausibles vers un futur
  cible (boucle proposition LLM + évaluation par le panel d'agents), plusieurs trajectoires candidates
  comparées et classées.
- **Gestion de l'incertitude** : chaque scénario tourne plusieurs fois (ensemble), la variance est
  systématiquement rapportée.

### Couche 4 — Comparaison de lois
- Comparaison A/B/N réelle, plusieurs variantes en parallèle via la file de jobs (couche 5).
- Comparaison possible au niveau d'un article ou d'un amendement, pas seulement du texte entier.
- Tableau de bord unifié : cartes côte à côte, graphiques d'écarts avec intervalles de variance.

### Couche 5 — Infrastructure de production
- **PostgreSQL** remplace le stockage JSON fichier de MiroFish pour tous les modèles (Project,
  Simulation, Scenario, Comparison, BacktestRun, User).
- **Celery + Redis** (ou équivalent) remplace le threading + IPC fichier pour l'orchestration des
  simulations et des jobs OpenFisca/backtesting — retries, supervision, scalabilité horizontale.
- **Comptes et permissions** : comptes réels pour le personnel/élus AN, rôles (créer une simulation,
  publier un résultat, administrer les données de référence).
- **Observabilité** : logs structurés, tableau de bord de métriques (durée des runs, coût LLM/Zep,
  taux d'erreur), alerting.

### Couche 6 — Produit utilisateur
- Scénarios sauvegardés, comparables dans le temps, annotables, partageables en interne AN.
- Historique de chat/interview persistant par utilisateur, exportable.
- Carte à granularité circonscription, recherche/filtre par circonscription.
- Exports professionnels (PDF, CSV/JSON).

### Couche 7 — Gouvernance et rigueur
- Tableau de bord de transparence du backtesting (métriques de calibration vs votes historiques réels).
- Workflow de revue humaine avant toute publication externe (état de cycle de vie du scénario).
- Conformité RGPD complète (DPIA si nécessaire), validation continue avec les canaux juridiques de l'AN.

## 4. Ce qu'on réutilise de MiroFish (base du backend)

| Fichier existant | Rôle | Évolution |
|---|---|---|
| `backend/app/__init__.py` | Factory Flask | Ajout de l'init DB/Celery |
| `backend/app/config.py` | Config/env | Étendu (DB, Redis, clients Tricoteuses/OpenFisca/data.gouv) |
| `backend/app/utils/llm_client.py` | Wrapper LLM | Inchangé dans son principe |
| `backend/app/services/ontology_generator.py` | Ontologie par LLM | Prompt adapté au domaine législatif |
| `backend/app/services/graph_builder.py` | Graphe Zep | Conservé, alimenté aussi par les nouvelles couches de données |
| `backend/app/services/oasis_profile_generator.py` | Personas d'agents | Remplacé/étendu par le générateur de population synthétique (couche 2) |
| `backend/app/services/simulation_runner.py` | Orchestration OASIS + Interview | Conservé comme moteur de débat, enrichi de la couche de vote agrégée |
| `backend/app/services/simulation_ipc.py` | IPC fichier | À terme remplacé par les tâches Celery, garder en transition |
| `backend/app/services/report_agent.py` | Génération de rapport ReACT | Plan de sections étendu (impact chiffré, trajectoires, backtesting) |
| `backend/app/services/zep_graph_memory_updater.py` | Mémoire temporelle Zep | Cœur du moteur prospectif multi-rounds (couche 3) |
| `backend/app/models/project.py`, `task.py` | Persistance fichier | Migrés vers des modèles PostgreSQL (ORM à introduire, ex. SQLAlchemy) |

## 5. Nouveaux modules backend

- `backend/app/services/regulatory_data/tricoteuses_client.py` — client GraphQL Tricoteuses.
- `backend/app/services/regulatory_data/openfisca_pipeline.py` — pipeline loi → règle calculable
  (extraction LLM, rapprochement paramètres, simulation, validation humaine).
- `backend/app/services/regulatory_data/datagouv_mcp_client.py` — requêtes live via le serveur MCP.
- `backend/app/services/regulatory_data/datacirco_client.py` — données par circonscription.
- `backend/app/services/population_synthesizer.py` — génération de population synthétique (IPF sur
  distributions INSEE).
- `backend/app/services/vote_aggregation.py` — couche de vote (poids de sièges, majorité/minorité).
- `backend/app/services/backtesting_engine.py` — rejoue d'anciens textes, calcule les métriques de
  calibration.
- `backend/app/services/temporal_engine.py` — moteur multi-rounds tendanciel/rétrospectif.
- `backend/app/services/comparison_engine.py` — orchestration de la comparaison multi-lois.
- `backend/app/tasks/` — tâches Celery (une par type de job long : construction de graphe, simulation,
  backtesting, comparaison).
- `backend/app/models/` — modèles ORM (User, Role, Project, Scenario, Simulation, ComparisonRun,
  BacktestRun, Round).

## 6. Contrat d'API partagé avec le frontend (SECTION CRITIQUE — identique dans GEMINI.md)

### Endpoints hérités de MiroFish (adaptés au domaine, mécanique conservée)
Upload/ontologie/graphe, création/préparation/démarrage de simulation, interview live, génération de
rapport/chat — mécanique conservée, payloads étendus au vocabulaire législatif.

### Nouveaux endpoints

- `GET /api/simulation/<id>/map-data?granularity=region|circonscription`
```json
{
  "granularity": "circonscription",
  "areas": [
    {
      "code": "75-01",
      "name": "1re circonscription de Paris",
      "qualitative_score": 2,
      "qualitative_score_scale": [-2, -1, 0, 1, 2],
      "openfisca_indicator": { "available": true, "label": "Impact moyen sur l'APL", "value": -34.2, "unit": "EUR/mois", "confidence_interval": [-40.1, -28.3] },
      "archetype_count": 128,
      "top_archetypes": ["Locataire jeune actif", "Retraité urbain"]
    }
  ],
  "disclaimer": "estimation exploratoire, distincte des données calculées — voir légende"
}
```
- `GET /api/backtesting/runs`, `POST /api/backtesting/runs` — lancer/consulter un run de backtesting,
  retourne les métriques de calibration (taux d'accord simulé/réel, par groupe, par type de texte).
- `POST /api/temporal/scenario` — configuration d'un scénario prospectif (mode tendanciel/rétrospectif,
  nombre de rounds, futur cible si rétrospectif).
- `GET /api/temporal/scenario/<id>/rounds` — liste des rounds avec indicateurs et variance.
- `POST /api/comparison/runs` — lance une comparaison A/B/N de lois/variantes.
- `GET /api/comparison/runs/<id>` — résultat consolidé (cartes, écarts, intervalles).
- `POST /api/scenarios/<id>/publish` — déclenche le workflow de revue humaine avant publication externe.
- Auth : `POST /api/auth/login`, gestion de session/JWT, endpoints protégés par rôle.

## 7. Conventions de code

- ORM SQLAlchemy pour tous les nouveaux modèles ; migrations Alembic.
- Tâches longues systématiquement en job Celery, jamais en thread bloquant dans la requête Flask.
- Un module par source de données externe sous `regulatory_data/`, chacun avec une interface commune
  (`fetch(theme, territory) -> StructuredResult`) pour rester interchangeable.
- Tests de calibration du backtesting versionnés et rejouables en CI.

## 8. Feuille de route (phases)

1. Fondations : couches de données réelles + infra production (DB, Celery) + cœur MiroFish adapté.
2. Simulation sociale complète : population synthétique, couche de vote, backtesting.
3. Couche temporelle complète : moteur multi-rounds, mémoire Zep, gestion de l'incertitude.
4. Comparaison multi-lois + carte par circonscription.
5. Produit complet : comptes, gouvernance, accessibilité, observabilité, exports.
