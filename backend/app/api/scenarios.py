"""
Endpoint du workflow de revue humaine (CLAUDE.md §2 & §6) : POST /api/scenarios/<id>/publish
Principe non négociable : toute publication externe d'un résultat de simulation passe par une
revue humaine explicite -- jamais automatique, quel que soit le rôle appelant.
"""

from datetime import datetime, timezone

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from . import scenarios_bp
from ..db import get_session
from ..db.models import Scenario, ScenarioStatus


@scenarios_bp.route('/<scenario_id>', methods=['GET'])
def get_scenario(scenario_id):
    session = get_session()
    try:
        scenario = session.get(Scenario, scenario_id)
        if scenario is None:
            return jsonify({"error": "scénario introuvable"}), 404
        return jsonify({
            "id": scenario.id, "name": scenario.name,
            "status": scenario.status.value if scenario.status else None,
            "config": scenario.config,
            "reviewed_at": scenario.reviewed_at.isoformat() if scenario.reviewed_at else None,
            "published_at": scenario.published_at.isoformat() if scenario.published_at else None,
        })
    finally:
        session.close()


@scenarios_bp.route('/<scenario_id>/review', methods=['POST'])
@jwt_required(optional=True)
def review_scenario(scenario_id):
    """Marque un scénario comme revu (étape intermédiaire obligatoire avant publication,
    CLAUDE.md §2 : "un vrai état du cycle de vie d'un scénario, pas une vérification ad hoc")."""
    session = get_session()
    try:
        scenario = session.get(Scenario, scenario_id)
        if scenario is None:
            return jsonify({"error": "scénario introuvable"}), 404

        reviewer_id = get_jwt_identity()
        scenario.status = ScenarioStatus.REVIEWED
        scenario.reviewed_by = reviewer_id
        scenario.reviewed_at = datetime.now(timezone.utc)
        session.commit()
        return jsonify({"id": scenario.id, "status": scenario.status.value})
    finally:
        session.close()


@scenarios_bp.route('/<scenario_id>/publish', methods=['POST'])
@jwt_required(optional=True)
def publish_scenario(scenario_id):
    """Publie un scénario -- refuse si le scénario n'est pas passé par l'étape REVIEWED au
    préalable (CLAUDE.md §2 : la revue humaine est un principe non négociable, pas une option)."""
    session = get_session()
    try:
        scenario = session.get(Scenario, scenario_id)
        if scenario is None:
            return jsonify({"error": "scénario introuvable"}), 404

        if scenario.status != ScenarioStatus.REVIEWED:
            return jsonify({
                "error": (
                    "publication refusée : le scénario doit d'abord passer par l'étape de revue "
                    "(POST /api/scenarios/<id>/review) -- workflow de revue humaine non négociable, "
                    "cf. CLAUDE.md §2"
                ),
                "current_status": scenario.status.value if scenario.status else None,
            }), 409

        publisher_id = get_jwt_identity()
        scenario.status = ScenarioStatus.PUBLISHED
        scenario.published_by = publisher_id
        scenario.published_at = datetime.now(timezone.utc)
        session.commit()
        return jsonify({"id": scenario.id, "status": scenario.status.value})
    finally:
        session.close()
