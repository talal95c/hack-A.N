"""
Pipeline de génération de `map_data.json` (CLAUDE.md §6, contrat `GET /api/simulation/<id>/map-data`).

Combine :
1. la population synthétique par région (population_synthesizer.py, un synthétiseur exécuté par
   région avec les marges INSEE de cette région) ;
2. un score qualitatif par archétype (issu du débat OASIS/MiroPolis -- ici accepté en paramètre
   sous forme de dict {archetype_id: score}, calculé en amont par la couche simulation) ;
3. l'indicateur OpenFisca précalculé le cas échéant (backend/uploads/territorial_cache/
   openfisca_results.json, produit par scripts/precompute_openfisca.py).

Écrit le résultat dans backend/uploads/simulations/<simulation_id>/map_data.json, exactement au
format attendu par l'endpoint `GET /api/simulation/<id>/map-data` (CLAUDE.md §6 / GEMINI.md §4).
"""

import json
import logging
import os
from dataclasses import dataclass

from ..config import Config
from .population_synthesizer import Dimension, SyntheticAgent, synthesize_population

logger = logging.getLogger(__name__)

# 13 régions métropolitaines (codes INSEE officiels) -- granularité "region" du contrat d'API.
# La granularité "circonscription" (DataCirco) reste un niveau de repli supérieur non couvert ici,
# cf. CLAUDE.md §1 et GEMINI.md §5 (repli automatique déjà prévu côté contrat).
FRENCH_REGIONS = [
    {"code": "84", "name": "Auvergne-Rhône-Alpes"},
    {"code": "27", "name": "Bourgogne-Franche-Comté"},
    {"code": "53", "name": "Bretagne"},
    {"code": "24", "name": "Centre-Val de Loire"},
    {"code": "94", "name": "Corse"},
    {"code": "44", "name": "Grand Est"},
    {"code": "32", "name": "Hauts-de-France"},
    {"code": "11", "name": "Île-de-France"},
    {"code": "28", "name": "Normandie"},
    {"code": "75", "name": "Nouvelle-Aquitaine"},
    {"code": "76", "name": "Occitanie"},
    {"code": "52", "name": "Pays de la Loire"},
    {"code": "93", "name": "Provence-Alpes-Côte d'Azur"},
]

QUALITATIVE_SCALE = [-2, -1, 0, 1, 2]


@dataclass
class RegionMarginals:
    """Marges démographiques INSEE pour une région donnée (CLAUDE.md §1 : un seul jeu INSEE
    régional pour le MVP). À défaut de marges spécifiques fournies pour une région, des marges
    nationales par défaut sont utilisées (dégradation explicite, jamais silencieuse)."""
    region_code: str
    dimensions: list[Dimension]


def _nearest_qualitative_bucket(raw_score: float) -> int:
    """Projette un score continu sur l'échelle qualitative discrète à 5 niveaux (CLAUDE.md §6 :
    "échelle qualitative à 3-5 niveaux, pas de dégradé continu, pour éviter la fausse précision")."""
    clamped = max(-2.0, min(2.0, raw_score))
    return min(QUALITATIVE_SCALE, key=lambda level: abs(level - clamped))


def build_map_data(
    simulation_id: str,
    region_marginals: list[RegionMarginals],
    agents_per_region: int,
    archetype_scores: dict,
    openfisca_results_path: str | None = None,
) -> dict:
    """Construit le payload complet `map_data.json` pour une simulation donnée.

    `archetype_scores` : dict {archetype_id: score qualitatif brut, ex. -1.5} -- typiquement
    calculé en amont à partir des positions de débat des groupes parlementaires vis-à-vis des
    archétypes citoyens de cette région (issu de vote_aggregation / du débat OASIS).
    """
    openfisca_by_archetype: dict = {}
    if openfisca_results_path and os.path.exists(openfisca_results_path):
        try:
            with open(openfisca_results_path, "r", encoding="utf-8") as f:
                openfisca_payload = json.load(f)
            for result in openfisca_payload.get("results", []):
                openfisca_by_archetype[result["archetype_id"]] = result
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("Lecture openfisca_results.json échouée: %s", exc)

    areas = []
    marginals_by_region = {m.region_code: m for m in region_marginals}

    for region in FRENCH_REGIONS:
        marginals = marginals_by_region.get(region["code"])
        if marginals is None:
            # Dégradation explicite : pas de marges spécifiques pour cette région -> zone absente
            # du résultat plutôt que des données inventées (CLAUDE.md §2, "aucune incertitude cachée").
            continue

        agents: list[SyntheticAgent] = synthesize_population(
            marginals.dimensions, n_agents=agents_per_region, territory_label=region["code"]
        )

        weighted_score_sum = 0.0
        total_weight = 0.0
        openfisca_values = []
        for agent in agents:
            raw_score = archetype_scores.get(agent.archetype_id)
            if raw_score is not None:
                weighted_score_sum += raw_score * agent.demographic_weight
                total_weight += agent.demographic_weight
            of_result = openfisca_by_archetype.get(agent.archetype_id)
            if of_result is not None:
                openfisca_values.append(of_result["value"])

        qualitative_score = (
            _nearest_qualitative_bucket(weighted_score_sum / total_weight) if total_weight > 0 else 0
        )

        openfisca_indicator = {"available": False}
        if openfisca_values:
            openfisca_indicator = {
                "available": True,
                "label": "Impact moyen calculé (OpenFisca)",
                "value": sum(openfisca_values) / len(openfisca_values),
                "unit": "",
            }

        # Regroupe les agents par combinaison de catégories (ex: même CSP) et cumule leur poids,
        # pour afficher les segments démographiques dominants plutôt que des doublons individuels.
        weight_by_label: dict[str, float] = {}
        for a in agents:
            label = a.categories.get("csp") or a.categories.get("profession") or a.archetype_id
            weight_by_label[label] = weight_by_label.get(label, 0.0) + a.demographic_weight
        top_archetypes = [
            label for label, _ in sorted(weight_by_label.items(), key=lambda kv: kv[1], reverse=True)[:3]
        ]

        areas.append({
            # Clés canoniques du contrat d'API (CLAUDE.md §6 / GEMINI.md §4) : "code" et "name"
            # uniquement -- ne pas dupliquer sous d'autres noms (region_code/region_name), pour
            # qu'il n'existe qu'une seule façon de lire ces champs côté frontend.
            "code": region["code"],
            "name": region["name"],
            "qualitative_score": qualitative_score,
            "qualitative_score_scale": QUALITATIVE_SCALE,
            "openfisca_indicator": openfisca_indicator,
            "archetype_count": len(agents),
            "top_archetypes": top_archetypes,
        })

    return {
        "granularity": "region",
        "areas": areas,
        "disclaimer": (
            "estimation exploratoire, distincte des données calculées — voir légende"
        ),
    }


def persist_map_data(simulation_id: str, payload: dict) -> str:
    """Écrit le payload au chemin lu par `GET /api/simulation/<id>/map-data`
    (backend/app/api/simulation.py, `get_map_data`)."""
    sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
    os.makedirs(sim_dir, exist_ok=True)
    output_path = os.path.join(sim_dir, "map_data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return output_path
