"""
Endpoints de comparaison multi-lois (CLAUDE.md §6) :
POST /api/comparison/runs, GET /api/comparison/runs/<id>
Couche 4.
"""

from flask import request, jsonify

from . import comparison_bp
from ..tasks.comparison_tasks import run_comparison_task
from ..db import get_session
from ..db.models import ComparisonRun


@comparison_bp.route('/runs', methods=['POST'])
def create_comparison_run():
    """Corps attendu : {"name": str, "snapshots": [{"scenario_id", "scenario_name", "areas"}]}
    `areas` doit respecter le format du champ `areas` de GET /api/simulation/<id>/map-data."""
    data = request.get_json(force=True, silent=True) or {}
    name = data.get('name', 'Comparaison sans nom')
    snapshots = data.get('snapshots', [])

    if len(snapshots) < 2:
        return jsonify({"error": "au moins 2 scénarios sont nécessaires pour une comparaison"}), 400

    result = run_comparison_task.delay(name, snapshots).get()
    return jsonify(result), 201


@comparison_bp.route('/runs/<run_id>', methods=['GET'])
def get_comparison_run(run_id):
    session = get_session()
    try:
        run = session.get(ComparisonRun, run_id)
        if run is None:
            return jsonify({"error": "comparaison introuvable"}), 404
        return jsonify({
            "id": run.id,
            "name": run.name,
            "scenario_ids": run.scenario_ids,
            "status": run.status.value if run.status else None,
            "result": run.result,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        })
    finally:
        session.close()
