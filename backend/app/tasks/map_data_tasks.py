"""Tâche Celery pour la construction de map_data.json (CLAUDE.md §5 & §6)."""

from ..celery_app import celery_app
from ..services.map_data_builder import RegionMarginals, build_map_data, persist_map_data
from ..services.population_synthesizer import Dimension


@celery_app.task(name="miropolis.build_map_data")
def build_map_data_task(
    simulation_id: str,
    region_marginals: list[dict],
    agents_per_region: int,
    archetype_scores: dict,
    openfisca_results_path: str | None = None,
) -> dict:
    """`region_marginals` : liste de {"region_code": str, "dimensions": [{"name", "categories",
    "marginal"}]} -- sérialisable en JSON pour passer par la file de jobs."""
    typed_marginals = [
        RegionMarginals(
            region_code=rm["region_code"],
            dimensions=[
                Dimension(name=d["name"], categories=d["categories"], marginal=d["marginal"])
                for d in rm["dimensions"]
            ],
        )
        for rm in region_marginals
    ]
    payload = build_map_data(
        simulation_id=simulation_id,
        region_marginals=typed_marginals,
        agents_per_region=agents_per_region,
        archetype_scores=archetype_scores,
        openfisca_results_path=openfisca_results_path,
    )
    output_path = persist_map_data(simulation_id, payload)
    payload["_output_path"] = output_path
    return payload
