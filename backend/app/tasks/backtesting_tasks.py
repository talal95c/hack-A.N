"""Tâches Celery pour le module de backtesting (CLAUDE.md §5 & §7)."""

from ..celery_app import celery_app
from ..services import backtesting_engine


@celery_app.task(name="miropolis.run_backtest")
def run_backtest_task(law_reference: str, simulated_positions: dict, law_label: str | None = None) -> dict:
    result = backtesting_engine.run_backtest(law_reference, simulated_positions)
    run_id = None
    if result.real_outcome_available:
        run_id = backtesting_engine.persist_backtest_run(result, law_label=law_label)
    payload = result.to_dict()
    payload["run_id"] = run_id
    return payload
