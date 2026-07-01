"""Tâches Celery pour le moteur prospectif (CLAUDE.md §5 & §3)."""

from ..celery_app import celery_app
from ..services import temporal_engine


@celery_app.task(name="miropolis.run_tendential_scenario")
def run_tendential_scenario_task(
    scenario_context: str, graph_id: str, n_periods: int, ensemble_size: int = 3
) -> list[dict]:
    rounds = temporal_engine.run_tendential_scenario(
        scenario_context=scenario_context, graph_id=graph_id, n_periods=n_periods, ensemble_size=ensemble_size
    )
    return [r.to_dict() for r in rounds]


@celery_app.task(name="miropolis.run_retrospective_scenario")
def run_retrospective_scenario_task(
    scenario_context: str, graph_id: str, target_future: str, n_periods: int, n_candidate_trajectories: int = 3
) -> list[list[dict]]:
    trajectories = temporal_engine.run_retrospective_scenario(
        scenario_context=scenario_context, graph_id=graph_id, target_future=target_future,
        n_periods=n_periods, n_candidate_trajectories=n_candidate_trajectories,
    )
    return [[r.to_dict() for r in trajectory] for trajectory in trajectories]
