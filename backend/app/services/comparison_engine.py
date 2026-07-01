"""
Orchestration de la comparaison multi-lois (CLAUDE.md §3, couche 4) : plusieurs variantes/scénarios
tournent (en jobs Celery, cf. backend/app/tasks/comparison_tasks.py), puis ce module consolide les
résultats en un tableau de bord unifié (cartes côte à côte, écarts d'indicateurs avec intervalles).
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ScenarioMapSnapshot:
    """Instantané des données carte (contrat `/api/simulation/<id>/map-data`) pour un scénario
    donné, utilisé comme entrée de la comparaison."""
    scenario_id: str
    scenario_name: str
    areas: list[dict]  # même structure que le champ `areas` du contrat d'API


@dataclass
class AreaDelta:
    area_code: str
    area_name: str
    qualitative_score_delta: dict  # {scenario_id: score} pour affichage côte à côte
    openfisca_value_delta: float | None  # écart de valeur calculée (si dispo des deux côtés)

    def to_dict(self) -> dict:
        return {
            "area_code": self.area_code,
            "area_name": self.area_name,
            "qualitative_score_delta": self.qualitative_score_delta,
            "openfisca_value_delta": self.openfisca_value_delta,
        }


@dataclass
class ComparisonResult:
    scenario_ids: list[str]
    scenario_names: list[str]
    areas: list[AreaDelta] = field(default_factory=list)
    national_indicator_deltas: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "scenario_ids": self.scenario_ids,
            "scenario_names": self.scenario_names,
            "areas": [a.to_dict() for a in self.areas],
            "national_indicator_deltas": self.national_indicator_deltas,
        }


def compare_scenarios(snapshots: list[ScenarioMapSnapshot]) -> ComparisonResult:
    """Consolide N instantanés de carte (un par scénario/variante comparée) en un résultat de
    comparaison unifié -- CLAUDE.md §4 : "comparaison possible au niveau d'un article ou d'un
    amendement, pas seulement du texte entier" (chaque snapshot peut représenter une variante
    fine, pas nécessairement un texte de loi entier)."""
    if len(snapshots) < 2:
        raise ValueError("La comparaison nécessite au moins 2 scénarios")

    # Index des zones par code -- "code" est la clé canonique du contrat d'API (CLAUDE.md §6),
    # cf. map_data_builder.py.
    areas_by_scenario: dict[str, dict[str, dict]] = {
        snap.scenario_id: {a["code"]: a for a in snap.areas}
        for snap in snapshots
    }

    # Union de tous les codes de zone rencontrés à travers les scénarios comparés
    all_area_codes: set[str] = set()
    for areas in areas_by_scenario.values():
        all_area_codes.update(areas.keys())

    area_deltas = []
    for code in sorted(all_area_codes):
        qualitative_by_scenario = {}
        openfisca_values = {}
        area_name = code
        for snap in snapshots:
            area = areas_by_scenario[snap.scenario_id].get(code)
            if area is None:
                continue
            area_name = area.get("name") or area_name
            qualitative_by_scenario[snap.scenario_id] = area.get("qualitative_score")
            openfisca = area.get("openfisca_indicator") or {}
            if openfisca.get("available"):
                openfisca_values[snap.scenario_id] = openfisca.get("value")

        openfisca_delta = None
        if len(openfisca_values) >= 2:
            values = list(openfisca_values.values())
            openfisca_delta = max(values) - min(values)

        area_deltas.append(AreaDelta(
            area_code=code, area_name=area_name,
            qualitative_score_delta=qualitative_by_scenario,
            openfisca_value_delta=openfisca_delta,
        ))

    return ComparisonResult(
        scenario_ids=[s.scenario_id for s in snapshots],
        scenario_names=[s.scenario_name for s in snapshots],
        areas=area_deltas,
    )


def persist_comparison_run(scenario_ids: list[str], name: str, result: ComparisonResult) -> str:
    """Enregistre le résultat consolidé dans la table ComparisonRun."""
    from ..db import get_session
    from ..db.models import ComparisonRun, ComparisonRunStatus
    from datetime import datetime, timezone

    session = get_session()
    try:
        run = ComparisonRun(
            name=name,
            scenario_ids=scenario_ids,
            status=ComparisonRunStatus.COMPLETED,
            result=result.to_dict(),
            completed_at=datetime.now(timezone.utc),
        )
        session.add(run)
        session.commit()
        return run.id
    finally:
        session.close()
