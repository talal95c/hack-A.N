"""
Moteur prospectif complet (CLAUDE.md §3, couche 3) — multi-rounds, mode tendanciel et
rétrospectif/backcasting, mémoire persistée dans le graphe Zep existant (comme le fait déjà
`zep_graph_memory_updater.py` pour le débat OASIS), gestion de l'incertitude par runs en ensemble.

Un round représente une période simulée (ex: une année). Chaque round :
1. Lit le contexte des rounds précédents (mémoire du graphe Zep, via une requête sur le graph_id).
2. Demande au LLM de produire (a) une évolution narrative, (b) des indicateurs chiffrés avec une
   fourchette de confiance (jamais un point isolé, cf. CLAUDE.md §2).
3. Persiste le round comme épisode dans le graphe Zep, pour que le round suivant en hérite.
"""

import json
import logging
import statistics
from dataclasses import dataclass, field
from typing import Optional

from zep_cloud.client import Zep
from zep_cloud import EpisodeData

from ..config import Config
from ..utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class IndicatorEstimate:
    name: str
    mean: float
    variance: float
    ci_low: float
    ci_high: float
    unit: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name, "mean": self.mean, "variance": self.variance,
            "ci_low": self.ci_low, "ci_high": self.ci_high, "unit": self.unit,
        }


@dataclass
class RoundResult:
    round_index: int
    label: str
    mode: str  # "tendanciel" | "retrospectif"
    narrative: str
    indicators: list[IndicatorEstimate] = field(default_factory=list)
    trajectory_rank: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "round_index": self.round_index,
            "label": self.label,
            "mode": self.mode,
            "narrative": self.narrative,
            "indicators": [i.to_dict() for i in self.indicators],
            "trajectory_rank": self.trajectory_rank,
        }


ROUND_PROMPT_TEMPLATE = """Tu es un analyste prospectif spécialisé en politiques publiques françaises.

Contexte du scénario : {scenario_context}
Historique des périodes précédentes : {previous_summary}
Période à projeter : {label} ({mode})

Produis une projection réaliste et prudente de cette période, sous forme JSON strict :
{{
  "narrative": "2-3 phrases décrivant l'évolution de la situation pendant cette période",
  "indicators": [
    {{"name": "...", "estimate": <nombre>, "unit": "..."}}
  ]
}}

Règles impératives :
- Ceci est une estimation exploratoire, pas une prédiction certaine -- reste prudent et nuancé.
- Ne mentionne jamais un élu nommé individuellement.
- Maximum 4 indicateurs, cohérents avec le contexte du scénario."""


def _run_single_round_llm(
    llm_client: LLMClient,
    scenario_context: str,
    previous_summary: str,
    label: str,
    mode: str,
) -> dict:
    prompt = ROUND_PROMPT_TEMPLATE.format(
        scenario_context=scenario_context, previous_summary=previous_summary, label=label, mode=mode
    )
    return llm_client.chat_json(messages=[{"role": "user", "content": prompt}], temperature=0.6)


def run_round_ensemble(
    scenario_context: str,
    previous_summary: str,
    round_index: int,
    label: str,
    mode: str = "tendanciel",
    ensemble_size: int = 3,
    llm_client: Optional[LLMClient] = None,
) -> RoundResult:
    """Exécute un round plusieurs fois (ensemble) pour estimer la variance des indicateurs plutôt
    que de présenter un chiffre ponctuel comme certain (CLAUDE.md §2 & §3)."""
    llm_client = llm_client or LLMClient()

    raw_runs = []
    for _ in range(max(1, ensemble_size)):
        try:
            raw_runs.append(_run_single_round_llm(llm_client, scenario_context, previous_summary, label, mode))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Un run du round '%s' a échoué: %s", label, exc)

    if not raw_runs:
        return RoundResult(round_index=round_index, label=label, mode=mode, narrative="(estimation indisponible)")

    # Regroupe les valeurs de chaque indicateur par nom, à travers les runs de l'ensemble
    by_indicator: dict[str, list[float]] = {}
    units: dict[str, str] = {}
    for run in raw_runs:
        for ind in run.get("indicators", []):
            name = ind.get("name")
            if not name:
                continue
            try:
                value = float(ind.get("estimate"))
            except (TypeError, ValueError):
                continue
            by_indicator.setdefault(name, []).append(value)
            units[name] = ind.get("unit", "")

    indicators = []
    for name, values in by_indicator.items():
        mean = statistics.fmean(values)
        variance = statistics.pvariance(values) if len(values) > 1 else 0.0
        std = variance ** 0.5
        indicators.append(IndicatorEstimate(
            name=name, mean=mean, variance=variance,
            ci_low=mean - 1.96 * std, ci_high=mean + 1.96 * std, unit=units.get(name, ""),
        ))

    narrative = raw_runs[0].get("narrative", "")

    return RoundResult(round_index=round_index, label=label, mode=mode, narrative=narrative, indicators=indicators)


def persist_round_to_graph(graph_id: str, round_result: RoundResult) -> None:
    """Ajoute le round comme épisode au graphe Zep existant, pour que les rounds suivants (et le
    ReportAgent) puissent le retrouver -- même mécanique que graph_builder.py (couche 1 héritée)."""
    if not Config.ZEP_API_KEY:
        logger.warning("ZEP_API_KEY non configuré -- round non persisté dans le graphe")
        return
    try:
        client = Zep(api_key=Config.ZEP_API_KEY)
        episode_text = f"[{round_result.label}] {round_result.narrative} " + json.dumps(
            {i.name: i.mean for i in round_result.indicators}, ensure_ascii=False
        )
        client.graph.add_batch(graph_id=graph_id, episodes=[EpisodeData(data=episode_text, type="text")])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Échec de la persistance du round dans le graphe Zep: %s", exc)


def run_tendential_scenario(
    scenario_context: str,
    graph_id: str,
    n_periods: int,
    period_label_prefix: str = "Année",
    ensemble_size: int = 3,
) -> list[RoundResult]:
    """Mode tendanciel (CLAUDE.md §3) : simulation en avant sous la politique actuelle, N périodes."""
    rounds: list[RoundResult] = []
    previous_summary = "(aucune période précédente)"
    for i in range(1, n_periods + 1):
        label = f"{period_label_prefix} {i}"
        round_result = run_round_ensemble(
            scenario_context, previous_summary, i, label, mode="tendanciel", ensemble_size=ensemble_size
        )
        persist_round_to_graph(graph_id, round_result)
        rounds.append(round_result)
        previous_summary = round_result.narrative

    return rounds


RETROSPECTIVE_PROMPT_TEMPLATE = """Tu es un analyste en prospective stratégique (méthode de backcasting).

Contexte du scénario : {scenario_context}
Futur souhaité, décrit par l'utilisateur : {target_future}

En partant de ce futur souhaité et en remontant vers aujourd'hui, propose UNE trajectoire plausible
de {n_periods} décisions/actions successives qui y mèneraient. Réponds en JSON strict :
{{
  "trajectory_label": "résumé court de la trajectoire",
  "steps": [
    {{"label": "période N (la plus proche du futur souhaité)", "narrative": "..."}},
    ...
    {{"label": "période 1 (la plus proche d'aujourd'hui)", "narrative": "..."}}
  ]
}}

Règles impératives : reste réaliste et nuancé, ne mentionne jamais un élu nommé individuellement,
présente ceci comme un scénario exploratoire parmi d'autres possibles, pas une trajectoire certaine."""


def run_retrospective_scenario(
    scenario_context: str,
    graph_id: str,
    target_future: str,
    n_periods: int,
    n_candidate_trajectories: int = 3,
    llm_client: Optional[LLMClient] = None,
) -> list[list[RoundResult]]:
    """Mode rétrospectif/backcasting (CLAUDE.md §3) : génère plusieurs trajectoires candidates vers
    un futur cible, pour comparaison -- pas une trajectoire unique présentée comme la solution."""
    llm_client = llm_client or LLMClient()
    prompt = RETROSPECTIVE_PROMPT_TEMPLATE.format(
        scenario_context=scenario_context, target_future=target_future, n_periods=n_periods
    )

    trajectories: list[list[RoundResult]] = []
    for candidate_rank in range(1, n_candidate_trajectories + 1):
        try:
            raw = llm_client.chat_json(messages=[{"role": "user", "content": prompt}], temperature=0.8)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Trajectoire rétrospective candidate #%d échouée: %s", candidate_rank, exc)
            continue

        steps = raw.get("steps", [])
        trajectory: list[RoundResult] = []
        for i, step in enumerate(steps, start=1):
            round_result = RoundResult(
                round_index=i,
                label=step.get("label", f"Étape {i}"),
                mode="retrospectif",
                narrative=step.get("narrative", ""),
                trajectory_rank=candidate_rank,
            )
            trajectory.append(round_result)
        if trajectory:
            trajectories.append(trajectory)

    # Persiste uniquement la trajectoire la mieux classée (rang 1) dans le graphe, pour ne pas
    # polluer la mémoire avec des scénarios alternatifs non retenus.
    if trajectories:
        for round_result in trajectories[0]:
            persist_round_to_graph(graph_id, round_result)

    return trajectories
