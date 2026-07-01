"""
Scenario Agent API 路由 (CLAUDE.md §6) -- agent de scénario tendanciel, en plus du ReportAgent
habituel. Même pattern que report.py (génération asynchrone via TaskManager, stockage fichier).
"""

import threading
import traceback

from flask import request, jsonify

from . import scenario_bp
from ..services.scenario_agent import ScenarioAgent, ScenarioManager, ScenarioStatus
from ..services.simulation_manager import SimulationManager
from ..models.project import ProjectManager
from ..models.task import TaskManager, TaskStatus
from ..utils.logger import get_logger
from ..utils.locale import t, get_locale, set_locale

logger = get_logger('mirofish.api.scenario')


@scenario_bp.route('/generate', methods=['POST'])
def generate_scenario():
    """Lance la génération du scénario tendanciel (asynchrone) -- même contrat que
    POST /api/report/generate."""
    try:
        data = request.get_json() or {}
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({"success": False, "error": t('api.requireSimulationId')}), 400

        force_regenerate = data.get('force_regenerate', False)

        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if not state:
            return jsonify({"success": False, "error": t('api.simulationNotFound', id=simulation_id)}), 404

        if not force_regenerate:
            existing = ScenarioManager.get_scenario_by_simulation(simulation_id)
            if existing and existing.status == ScenarioStatus.COMPLETED:
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id, "scenario_id": existing.scenario_id,
                        "status": "completed", "already_generated": True,
                    },
                })

        project = ProjectManager.get_project(state.project_id)
        if not project:
            return jsonify({"success": False, "error": t('api.projectNotFound', id=state.project_id)}), 404

        graph_id = state.graph_id or project.graph_id
        if not graph_id:
            return jsonify({"success": False, "error": t('api.missingGraphIdEnsure')}), 400

        simulation_requirement = project.simulation_requirement
        if not simulation_requirement:
            return jsonify({"success": False, "error": t('api.missingSimRequirement')}), 400

        import uuid
        scenario_id = f"scenario_{uuid.uuid4().hex[:12]}"

        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="scenario_generate",
            metadata={"simulation_id": simulation_id, "graph_id": graph_id, "scenario_id": scenario_id},
        )

        current_locale = get_locale()

        def run_generate():
            set_locale(current_locale)
            try:
                task_manager.update_task(task_id, status=TaskStatus.PROCESSING, progress=0)

                agent = ScenarioAgent(
                    graph_id=graph_id, simulation_id=simulation_id,
                    simulation_requirement=simulation_requirement,
                )

                def progress_callback(stage, progress, message):
                    task_manager.update_task(task_id, progress=progress, message=f"[{stage}] {message}")

                report = agent.generate_scenario(progress_callback=progress_callback, scenario_id=scenario_id)
                ScenarioManager.save_scenario(report)

                if report.status == ScenarioStatus.COMPLETED:
                    task_manager.complete_task(
                        task_id,
                        result={"scenario_id": report.scenario_id, "simulation_id": simulation_id, "status": "completed"},
                    )
                else:
                    task_manager.fail_task(task_id, report.error or "scenario generation failed")
            except Exception as e:
                logger.error(f"Génération du scénario échouée: {e}")
                task_manager.fail_task(task_id, str(e))

        threading.Thread(target=run_generate, daemon=True).start()

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id, "scenario_id": scenario_id, "task_id": task_id,
                "status": "generating", "already_generated": False,
            },
        })
    except Exception as e:
        logger.error(f"启动场景生成任务失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@scenario_bp.route('/generate/status', methods=['POST'])
def get_generate_status():
    """Même contrat que POST /api/report/generate/status."""
    try:
        data = request.get_json() or {}
        task_id = data.get('task_id')
        simulation_id = data.get('simulation_id')

        if simulation_id:
            existing = ScenarioManager.get_scenario_by_simulation(simulation_id)
            if existing and existing.status == ScenarioStatus.COMPLETED:
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id, "scenario_id": existing.scenario_id,
                        "status": "completed", "progress": 100, "already_completed": True,
                    },
                })

        if not task_id:
            return jsonify({"success": False, "error": t('api.requireTaskOrSimId')}), 400

        task = TaskManager().get_task(task_id)
        if not task:
            return jsonify({"success": False, "error": t('api.taskNotFound', id=task_id)}), 404

        return jsonify({"success": True, "data": task.to_dict()})
    except Exception as e:
        logger.error(f"查询场景任务状态失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@scenario_bp.route('/<scenario_id>', methods=['GET'])
def get_scenario(scenario_id: str):
    try:
        report = ScenarioManager.get_scenario(scenario_id)
        if not report:
            return jsonify({"success": False, "error": t('api.reportNotFound', id=scenario_id)}), 404
        return jsonify({"success": True, "data": report.to_dict()})
    except Exception as e:
        logger.error(f"获取场景失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@scenario_bp.route('/by-simulation/<simulation_id>', methods=['GET'])
def get_scenario_by_simulation(simulation_id: str):
    try:
        report = ScenarioManager.get_scenario_by_simulation(simulation_id)
        if not report:
            return jsonify({"success": False, "error": t('api.noReportForSim', id=simulation_id), "has_scenario": False}), 404
        return jsonify({"success": True, "data": report.to_dict(), "has_scenario": True})
    except Exception as e:
        logger.error(f"获取场景失败: {str(e)}")
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500
