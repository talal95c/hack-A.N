"""
Endpoints de backtesting (CLAUDE.md §6) : GET/POST /api/backtesting/runs
Couche 7 -- tableau de bord de transparence méthodologique.
"""

from flask import request, jsonify

from . import backtesting_bp
from ..tasks.backtesting_tasks import run_backtest_task
from ..db import get_session
from ..db.models import BacktestRun


@backtesting_bp.route('/runs', methods=['GET'])
def list_backtest_runs():
    session = get_session()
    try:
        runs = session.query(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(50).all()
        return jsonify({
            "runs": [
                {
                    "id": r.id,
                    "law_reference": r.law_reference,
                    "law_label": r.law_label,
                    "agreement_score": r.agreement_score,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in runs
            ]
        })
    finally:
        session.close()


@backtesting_bp.route('/runs', methods=['POST'])
def create_backtest_run():
    """Lance un run de backtesting : rejoue un texte historique et compare au vote réel.

    Corps attendu : {"law_reference": str, "law_label": str?, "simulated_positions": {group: position}}
    `simulated_positions` doit provenir d'un run MiroPolis complet sur le texte historique rejoué.
    """
    data = request.get_json(force=True, silent=True) or {}
    law_reference = data.get('law_reference')
    simulated_positions = data.get('simulated_positions', {})
    law_label = data.get('law_label')

    if not law_reference:
        return jsonify({"error": "law_reference requis"}), 400

    result = run_backtest_task.delay(law_reference, simulated_positions, law_label)
    return jsonify(result.get()), 201
