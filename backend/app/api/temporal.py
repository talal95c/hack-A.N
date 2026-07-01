"""
Endpoints du moteur temporel (CLAUDE.md §6) :
POST /api/temporal/scenario, GET /api/temporal/scenario/<id>/rounds
Couche 3 -- mode tendanciel / rétrospectif.
"""

from flask import request, jsonify

from . import temporal_bp
from ..tasks.temporal_tasks import run_tendential_scenario_task, run_retrospective_scenario_task
from ..db import get_session
from ..db.models import Round, Scenario, TemporalMode


@temporal_bp.route('/scenario', methods=['POST'])
def create_temporal_scenario():
    """Configure et exécute un scénario prospectif.

    Corps attendu :
    {
      "scenario_id": str,
      "graph_id": str,
      "scenario_context": str,
      "mode": "tendanciel" | "retrospectif",
      "n_periods": int,
      "target_future": str  # requis si mode == "retrospectif"
      "ensemble_size": int?  # défaut 3
      "n_candidate_trajectories": int?  # défaut 3, mode rétrospectif uniquement
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    scenario_id = data.get('scenario_id')
    graph_id = data.get('graph_id')
    scenario_context = data.get('scenario_context', '')
    mode = data.get('mode', 'tendanciel')
    n_periods = int(data.get('n_periods', 5))

    if not scenario_id or not graph_id:
        return jsonify({"error": "scenario_id et graph_id requis"}), 400

    session = get_session()
    try:
        if mode == 'tendanciel':
            rounds_data = run_tendential_scenario_task.delay(
                scenario_context, graph_id, n_periods, data.get('ensemble_size', 3)
            ).get()
            for r in rounds_data:
                session.add(Round(
                    scenario_id=scenario_id, mode=TemporalMode.TENDANCIEL,
                    round_index=r['round_index'], label=r['label'],
                    indicators={i['name']: i for i in r['indicators']}, narrative=r['narrative'],
                ))
            session.commit()
            return jsonify({"mode": mode, "rounds": rounds_data}), 201

        elif mode == 'retrospectif':
            target_future = data.get('target_future')
            if not target_future:
                return jsonify({"error": "target_future requis en mode rétrospectif"}), 400
            trajectories = run_retrospective_scenario_task.delay(
                scenario_context, graph_id, target_future, n_periods,
                data.get('n_candidate_trajectories', 3),
            ).get()
            for rank, trajectory in enumerate(trajectories, start=1):
                for r in trajectory:
                    session.add(Round(
                        scenario_id=scenario_id, mode=TemporalMode.RETROSPECTIF,
                        round_index=r['round_index'], label=r['label'],
                        narrative=r['narrative'], trajectory_rank=rank,
                    ))
            session.commit()
            return jsonify({"mode": mode, "trajectories": trajectories}), 201

        else:
            return jsonify({"error": f"mode inconnu: {mode}"}), 400
    finally:
        session.close()


@temporal_bp.route('/scenario/<scenario_id>/rounds', methods=['GET'])
def get_temporal_rounds(scenario_id):
    session = get_session()
    try:
        rounds = (
            session.query(Round)
            .filter(Round.scenario_id == scenario_id)
            .order_by(Round.trajectory_rank, Round.round_index)
            .all()
        )
        return jsonify({
            "rounds": [
                {
                    "id": r.id,
                    "mode": r.mode.value if r.mode else None,
                    "round_index": r.round_index,
                    "label": r.label,
                    "indicators": r.indicators,
                    "narrative": r.narrative,
                    "trajectory_rank": r.trajectory_rank,
                }
                for r in rounds
            ]
        })
    finally:
        session.close()
