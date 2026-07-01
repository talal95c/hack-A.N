# GEMINI.md — MiroPolis, frontend (plateforme complète)

Ce fichier oriente Gemini sur le frontend. Le backend est piloté par Claude via CLAUDE.md — le
contrat d'API en section 3 de ce document est IDENTIQUE à CLAUDE.md §6. Ne jamais diverger sans
mettre à jour les deux fichiers.

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

## 4. Contrat d'API (IDENTIQUE à CLAUDE.md §6)

### `GET /api/simulation/<id>/map-data?granularity=region|circonscription`
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
Règle d'affichage : toujours afficher l'intervalle de confiance quand il est présent (barre d'erreur
ou fourchette textuelle), jamais un point isolé pour une donnée calculée.

Autres endpoints à intégrer : `/api/backtesting/runs`, `/api/temporal/scenario[...]`,
`/api/comparison/runs[...]`, `/api/scenarios/<id>/publish`, `/api/auth/login`.

### Fixtures de développement
Créer un dossier `src/mocks/` avec une fixture par endpoint nouveau, respectant exactement les schémas
ci-dessus, pour développer chaque vue indépendamment de l'avancement backend.

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
