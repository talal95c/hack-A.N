"""Tâches Celery pour la comparaison multi-lois (CLAUDE.md §5 & §4)."""

from ..celery_app import celery_app
from ..services import comparison_engine


@celery_app.task(name="miropolis.run_comparison")
def run_comparison_task(name: str, snapshots: list[dict]) -> dict:
    """`snapshots` : liste de {"scenario_id", "scenario_name", "areas"} (areas = format /map-data)."""
    typed_snapshots = [
        comparison_engine.ScenarioMapSnapshot(
            scenario_id=s["scenario_id"], scenario_name=s["scenario_name"], areas=s["areas"]
        )
        for s in snapshots
    ]
    result = comparison_engine.compare_scenarios(typed_snapshots)
    run_id = comparison_engine.persist_comparison_run(
        scenario_ids=[s.scenario_id for s in typed_snapshots], name=name, result=result
    )
    payload = result.to_dict()
    payload["run_id"] = run_id
    return payload
