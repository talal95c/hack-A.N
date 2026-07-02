# CLAUDE.md — MiroPolis ("MiroFish v2")

Ce fichier oriente Claude sur le backend. Le frontend est piloté par Gemini via GEMINI.md — le
contrat d'API en section 7 de ce document est IDENTIQUE au contrat GEMINI.md. Ne jamais diverger
sans mettre à jour les deux fichiers.

## 1. Vision — ce que le produit doit permettre, précisément

> Les Députés IA : configurés selon la composition réelle de l'hémicycle et le programme de leur
> parti. Ils débattent, proposent des amendements et votent sur le texte soumis.
> Les Citoyens IA : un échantillon représentatif de la population (âge, profession, géographie).
> Ils réagissent aux débats et évaluent l'impact concret de la loi sur leur quotidien (pouvoir
> d'achat, environnement, services publics).
> Grâce à ce jumeau numérique, le législateur peut tester des formulations d'amendements pour
> maximiser le consensus ou identifier les angles morts d'une réforme.

Concrètement, ce débat tourne sur un **flux unique** — une seule plateforme OASIS (Reddit,
retenue pour son action `CREATE_COMMENT`, qui permet à un Citoyen de réagir directement sous la
publication d'un Député), et non deux plateformes parallèles distinctes type réseau social
générique. Aucune restriction technique dure n'empêche un Citoyen de publier — le cadrage vient de
la persona/prompt de chaque agent, qui oriente les Députés vers la proposition/débat d'amendements
et les Citoyens vers la réaction aux publications des Députés plutôt que l'initiative. *(Cible de
design ; implémentation à faire dans une passe séparée — voir §2 pour le principe "OASIS reste le
moteur, tel quel" qui continue de s'appliquer : ceci se joue en configuration et en prompts, jamais
dans les scripts d'orchestration OASIS.)*

C'est la définition de référence du produit — chaque décision technique de ce document doit s'y
rattacher explicitement. Trois conséquences directes :

1. **Les Députés IA ne sont pas de simples "personas génériques par groupe"** : ils doivent être
   ancrés sur (a) la composition réelle de l'hémicycle (nombre de sièges par groupe, vérifié
   fonctionnel via data.gouv.fr — voir §5) ET (b) une ligne politique/programme représentative du
   groupe, et ils doivent produire un **résultat de vote explicite** sur le texte, pas seulement une
   réaction qualitative vague. Voir §6.2.
2. **Les Citoyens IA réagissent selon 3 axes d'impact concret nommés** : pouvoir d'achat,
   environnement, services publics — pas une réaction générique "content/pas content". Les prompts
   de génération de persona et les sections de rapport doivent citer ces axes explicitement.
3. **L'objectif final est outillé pour l'itération** : le législateur doit pouvoir tester une
   formulation d'amendement et voir l'effet sur le consensus. Dans l'état actuel du produit
   (MiroFish v2, un run = un texte de loi), cet objectif est atteint de deux façons : (a) relancer
   le pipeline avec un texte modifié (un nouvel upload = une nouvelle simulation, aucune
   fonctionnalité dédiée nécessaire) et (b) l'agent de scénario tendanciel calcule maintenant un
   **vote simulé pondéré par sièges réels** (§6.2) qui donne une mesure concrète et comparable du
   consensus d'une formulation à l'autre. La comparaison structurée de plusieurs formulations en une
   seule vue (A/B) a été explicitement retirée du scope (§2) — à ne réintroduire que sur demande
   explicite.

MiroPolis garde par ailleurs l'architecture MiroFish telle quelle, de bout en bout (upload →
ontologie → graphe Zep → simulation OASIS → rapport → interaction profonde).

## 2. Historique — ce qui a été tenté puis retiré (ne pas réintroduire sans qu'on le redemande)

- Une plateforme complète à 7 couches (PostgreSQL, Celery, comptes/JWT, workflow de publication,
  comparaison de lois, backtesting, carte de France par région, pipeline OpenFisca/LexImpact,
  DataCirco) a été entièrement construite puis **entièrement retirée** sur demande explicite : le
  produit doit rester proche de MiroFish, pas devenir une plateforme d'entreprise.
- Une proposition de remplacer le moteur de simulation OASIS par un mécanisme d'interaction maison
  (agents appelés individuellement en boucle, sans sous-processus) a été **explicitement rejetée** :
  OASIS reste le moteur d'interaction, tel quel.
- Le frontend contenait, en parallèle, des écrans construits pour cette même plateforme 7-couches
  (login, admin, comparaison, backtesting, bibliothèque de scénarios en DB) — supprimés du frontend
  également (voir GEMINI.md §0-§2 pour le détail).

## 3. Principes non négociables

- **Jamais d'élu nommé individuellement.** Les agents "Députés" sont calibrés par **groupe
  parlementaire**, jamais par élu identifiable — même dans le calcul du vote simulé (§6.2), qui
  reste agrégé par groupe.
- **Vocabulaire** : "enrichissement par données réelles" (jamais "calibration statistique" abusive) ;
  "estimation exploratoire" / "vote simulé" (jamais "prédiction" présentée comme certaine).
- **Disclaimer visible** sur toute vue affichant un résultat de simulation ou de scénario :
  *"estimation qualitative générée par IA, ne reflète pas la position officielle des groupes
  parlementaires ni une prédiction fiable de vote réel."*
- **Pas de DB, pas de file de jobs, pas de compte utilisateur.** Stockage fichier uniquement (comme
  MiroFish natif) — voir §4.
- **Toute nouvelle dépendance lourde** (DB, file de jobs, auth) nécessite une demande explicite,
  cf. §2.

## 4. Ce qui ne bouge pas (cœur MiroFish, ne pas réécrire)

| Fichier | Rôle |
|---|---|
| `backend/app/services/graph_builder.py`, `zep_entity_reader.py`, `zep_tools.py`, `zep_graph_memory_updater.py` | Pipeline graphe/mémoire Zep |
| `backend/app/services/simulation_runner.py`, `simulation_ipc.py`, `simulation_manager.py` | Orchestration OASIS (sous-processus), IPC, Interview |
| `backend/scripts/run_twitter_simulation.py`, `run_reddit_simulation.py`, `run_parallel_simulation.py`, `action_logger.py` | Scripts exécutés par le sous-processus OASIS, tournent sous `backend/.venv311` |
| `backend/.venv311` | Environnement Python 3.11 dédié — **toujours nécessaire**, `camel-oasis` ne s'installe pas sous Python 3.12 (contrainte réelle, vérifiée, indépendante de toute décision produit) |
| `backend/app/models/project.py`, `task.py` | Stockage fichier JSON, jamais remplacé par une DB |
| `backend/app/utils/*` | `llm_client.py`, `locale.py`, `logger.py`, `retry.py`, `zep_paging.py`, `file_parser.py` |
| `backend/app/api/graph.py` | Endpoints d'upload/ontologie/graphe |

## 5. Sources de données réelles

- `backend/app/services/regulatory_data/tricoteuses_client.py` — `fetch_parliamentary_groups()` :
  composition réelle des groupes parlementaires **et effectifs réels** (vérifié fonctionnel : 12
  groupes, 577 sièges au total, dataset officiel data.gouv.fr "Groupes politiques actifs de
  l'Assemblée nationale", mis à jour automatiquement — colonnes `nombreMembres`, `couleurAssociee`,
  et des indicateurs comportementaux réels du groupe (`scoreRose`, `socreCohesion`,
  `scoreParticipation` dans le CSV source) exploitables pour enrichir encore la persona).
- `backend/app/services/regulatory_data/datagouv_mcp_client.py` — client générique data.gouv.fr,
  utilisé par `tricoteuses_client`.
- `backend/app/services/population_synthesizer.py` — calage IPF sur distributions INSEE
  (âge/CSP/région), génère les archétypes citoyens pondérés (vérifié fonctionnel : les poids
  démographiques d'un run somment à 1.0).
- `backend/app/services/vote_aggregation.py` — agrégation d'un ensemble de positions de groupes
  (support/oppose/abstain/undecided) en un résultat de vote pondéré par sièges réels, avec
  détection explicite d'incertitude (`outcome: "uncertain"` si plus de 15% des sièges sont
  indécis — jamais un résultat tranché arbitrairement). **Câblé dans `scenario_agent.py`** (§6.2).

### Limite honnête sur "le programme de leur parti"

Le "programme de leur parti" (§1) n'est **pas** alimenté par un document de programme officiel
verbatim — aucune source de ce type n'a été identifiée/branchée. La ligne politique du groupe dans
les personas (`oasis_profile_generator.py`) repose sur (a) le nom réel du groupe (que la
connaissance générale du LLM associe à une ligne politique connue) et (b) les indicateurs
comportementaux réels du groupe (cohésion, participation, `scoreRose`) listés ci-dessus. C'est une
approximation raisonnable, pas un fait à présenter comme calibré sur un texte de programme réel — à
formuler ainsi dans toute documentation utilisateur.

### Limite honnête sur la classification individu/groupe (bug connu, pas encore corrigé)

Les listes `INDIVIDUAL_ENTITY_TYPES`/`GROUP_ENTITY_TYPES` dans `oasis_profile_generator.py` datent
encore du vocabulaire de l'ancien MiroFish (student, professor, university, ngo...) et ne
reconnaissent pas les types réels de l'ontologie MiroPolis (`ParliamentaryGroup`,
`TenantArchetype`, etc.). Conséquence : la plupart des archétypes citoyens reçoivent aujourd'hui
par erreur le prompt "groupe parlementaire" au lieu du prompt "citoyen". À corriger dans la passe
de code à venir sur le débat unifié (voir §1) — tant que ce n'est pas fait, ne pas présenter les
personas Citoyens générées comme fiables.

## 6. Les deux agents en sortie de simulation

Les deux agents lisent la **même mémoire** (le graphe Zep peuplé par la simulation OASIS), mais
produisent des documents séparés (`report_id` ≠ `scenario_id`), générés/affichés indépendamment.

### 6.1 Agent de recap — `report_agent.py` (existant, adapté)

Plan à 5 sections fixes : synthèse décideur, cartographie des parties prenantes, réactions et
positions observées, points de blocage, recommandations. Doit couvrir les 3 axes d'impact cités en
§1 (pouvoir d'achat, environnement, services publics) dans la section "réactions et positions
observées" — à vérifier/renforcer si les sorties générées les omettent.

### 6.2 Agent de scénario tendanciel — `scenario_agent.py` (nouveau)

Même principe que `report_agent.py` (recherche outillée sur le graphe via `zep_tools.py`,
notamment `insight_forge`), mais agent **séparé**, avec un plan à 3 sections resserré (état actuel
observé, trajectoire tendancielle, points de bascule).

**Calcule et expose un vote simulé réel** (`ScenarioAgent._compute_vote_outcome`, concrétise
"Ils ... votent sur le texte soumis") :
1. Récupère la composition réelle des groupes (`tricoteuses_client.fetch_parliamentary_groups()`).
2. Demande au LLM d'extraire, à partir de la mémoire de simulation (recherche `insight_forge`), la
   position de **chaque groupe réel listé** (support/oppose/abstain/undecided) — jamais de position
   inventée pour un groupe non mentionné dans la mémoire (défaut : `undecided`).
3. Agrège via `vote_aggregation.aggregate_vote()` : résultat pondéré par sièges réels, avec
   détection d'incertitude.
4. Résultat exposé dans `ScenarioReport.vote_outcome` (voir contrat §7) et injecté dans le contexte
   de la première section ("État actuel observé") pour que la narration s'appuie dessus.

Dégrade proprement à `vote_outcome: null` si les données réelles ou l'extraction échouent — ne
casse jamais la génération des sections narratives.

## 7. Contrat d'API (IDENTIQUE à GEMINI.md)

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
    "scenario_id": "...", "simulation_id": "...", "status": "completed",
    "title": "...",
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
  `vote_outcome` peut être `null` (dégradation propre, voir §6.2) — le frontend doit gérer ce cas
  sans erreur.
- `GET /api/scenario/by-simulation/<simulation_id>` → dernier scénario généré pour cette simulation.

## 8. Conventions

- Tout nouveau module de données externes suit le pattern déjà en place dans
  `regulatory_data/` : dégrader proprement (`available=False` + message clair) plutôt que lever une
  exception, jamais d'appel réseau live pendant une démo.
- Toute fonctionnalité ajoutée doit se rattacher explicitement à la définition de référence du
  produit (§1) — si une idée ne sert ni le réalisme des Députés/Citoyens IA, ni les 3 axes d'impact
  cités, ni l'objectif de test d'amendements/consensus, la questionner avant de l'implémenter.
