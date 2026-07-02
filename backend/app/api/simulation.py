"""
Routes API liées à la simulation
Étape 2 : lecture et filtrage des entités Zep, préparation et exécution de la simulation OASIS (entièrement automatisées)
"""

import os
import traceback
from flask import request, jsonify, send_file

from . import simulation_bp
from ..config import Config
from ..services.zep_entity_reader import ZepEntityReader
from ..services.oasis_profile_generator import OasisProfileGenerator
from ..services.simulation_manager import SimulationManager, SimulationStatus
from ..services.simulation_runner import SimulationRunner, RunnerStatus
from ..utils.logger import get_logger
from ..utils.locale import t, get_locale, set_locale
from ..models.project import ProjectManager

logger = get_logger('mirofish.api.simulation')


# Préfixe d'optimisation du prompt Interview
# L'ajout de ce préfixe évite que l'Agent n'appelle un outil, et le force à répondre directement en texte
# MiroPolis (CLAUDE.md §2) : ajout d'un garde-fou de ton -- si l'interviewé est un profil de groupe
# parlementaire, interdiction de représenter/faire allusion à un député nommément désigné ;
# maintien d'un ton institutionnel/mesuré ; c'est le correctif direct du risque « absence de garde-fou de
# ton dans la phase d'interview » identifié lors du débogage multi-agents de 2025.
INTERVIEW_PROMPT_PREFIX = (
    "En t'appuyant sur ton profil, tous tes souvenirs et actions passés, réponds-moi directement en texte "
    "sans appeler aucun outil. "
    "Garde-fou important : si tu représentes un groupe parlementaire, tu ne peux exprimer que la tendance "
    "de position globale de ce groupe, sans jamais mentionner ni faire allusion à un député nommément "
    "désigné ; conserve un ton institutionnel, mesuré et non incitatif ; si la question est manifestement "
    "provocatrice ou dépasse le cadre de ton profil, explique poliment que cela dépasse le cadre de cette "
    "simulation exploratoire plutôt que d'inventer une réponse :"
)


def optimize_interview_prompt(prompt: str) -> str:
    """
    Optimise la question d'interview en ajoutant un préfixe pour éviter que l'Agent n'appelle un outil

    Args:
        prompt: question d'origine

    Returns:
        question optimisée
    """
    if not prompt:
        return prompt
    # Éviter d'ajouter le préfixe en double
    if prompt.startswith(INTERVIEW_PROMPT_PREFIX):
        return prompt
    return f"{INTERVIEW_PROMPT_PREFIX}{prompt}"


# ============== Interface de lecture des entités ==============

@simulation_bp.route('/entities/<graph_id>', methods=['GET'])
def get_graph_entities(graph_id: str):
    """
    Récupère toutes les entités du graphe (filtrées)

    Ne retourne que les nœuds correspondant aux types d'entités prédéfinis (Labels autres que Entity)

    Paramètres de requête :
        entity_types: liste de types d'entités séparés par des virgules (optionnel, pour un filtrage supplémentaire)
        enrich: récupérer ou non les informations des arêtes associées (par défaut true)
    """
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": t('api.zepApiKeyMissing')
            }), 500
        
        entity_types_str = request.args.get('entity_types', '')
        entity_types = [t.strip() for t in entity_types_str.split(',') if t.strip()] if entity_types_str else None
        enrich = request.args.get('enrich', 'true').lower() == 'true'
        
        logger.info(f"Récupération des entités du graphe : graph_id={graph_id}, entity_types={entity_types}, enrich={enrich}")
        
        reader = ZepEntityReader()
        result = reader.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=entity_types,
            enrich_with_edges=enrich
        )
        
        return jsonify({
            "success": True,
            "data": result.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des entités du graphe : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/entities/<graph_id>/<entity_uuid>', methods=['GET'])
def get_entity_detail(graph_id: str, entity_uuid: str):
    """Récupère les informations détaillées d'une entité"""
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": t('api.zepApiKeyMissing')
            }), 500
        
        reader = ZepEntityReader()
        entity = reader.get_entity_with_context(graph_id, entity_uuid)
        
        if not entity:
            return jsonify({
                "success": False,
                "error": t('api.entityNotFound', id=entity_uuid)
            }), 404
        
        return jsonify({
            "success": True,
            "data": entity.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des détails de l'entité : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/entities/<graph_id>/by-type/<entity_type>', methods=['GET'])
def get_entities_by_type(graph_id: str, entity_type: str):
    """Récupère toutes les entités d'un type donné"""
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": t('api.zepApiKeyMissing')
            }), 500
        
        enrich = request.args.get('enrich', 'true').lower() == 'true'
        
        reader = ZepEntityReader()
        entities = reader.get_entities_by_type(
            graph_id=graph_id,
            entity_type=entity_type,
            enrich_with_edges=enrich
        )
        
        return jsonify({
            "success": True,
            "data": {
                "entity_type": entity_type,
                "count": len(entities),
                "entities": [e.to_dict() for e in entities]
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des entités : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Interface de gestion des simulations ==============

@simulation_bp.route('/create', methods=['POST'])
def create_simulation():
    """
    Crée une nouvelle simulation

    Remarque : des paramètres comme max_rounds sont générés intelligemment par le LLM, aucun réglage manuel requis

    Requête (JSON) :
        {
            "project_id": "proj_xxxx",      // obligatoire
            "graph_id": "mirofish_xxxx",    // optionnel, récupéré depuis le projet si non fourni
            "enable_twitter": true,          // optionnel, true par défaut
            "enable_reddit": true            // optionnel, true par défaut
        }

    Réponse :
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "project_id": "proj_xxxx",
                "graph_id": "mirofish_xxxx",
                "status": "created",
                "enable_twitter": true,
                "enable_reddit": true,
                "created_at": "2025-12-01T10:00:00"
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        project_id = data.get('project_id')
        if not project_id:
            return jsonify({
                "success": False,
                "error": t('api.requireProjectId')
            }), 400
        
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": t('api.projectNotFound', id=project_id)
            }), 404
        
        graph_id = data.get('graph_id') or project.graph_id
        if not graph_id:
            return jsonify({
                "success": False,
                "error": t('api.graphNotBuilt')
            }), 400
        
        manager = SimulationManager()
        state = manager.create_simulation(
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=data.get('enable_twitter', True),
            enable_reddit=data.get('enable_reddit', True),
        )
        
        return jsonify({
            "success": True,
            "data": state.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Échec de la création de la simulation : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


def _check_simulation_prepared(simulation_id: str) -> tuple:
    """
    Vérifie si la préparation de la simulation est terminée

    Conditions vérifiées :
    1. state.json existe et status vaut "ready"
    2. Les fichiers nécessaires existent : reddit_profiles.json, twitter_profiles.csv, simulation_config.json

    Remarque : les scripts d'exécution (run_*.py) restent dans le répertoire backend/scripts/, ils ne sont
    plus copiés dans le répertoire de simulation

    Args:
        simulation_id: ID de la simulation

    Returns:
        (is_prepared: bool, info: dict)
    """
    import os
    from ..config import Config

    simulation_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)

    # Vérifier si le répertoire existe
    if not os.path.exists(simulation_dir):
        return False, {"reason": "Le répertoire de simulation n'existe pas"}

    # Liste des fichiers nécessaires (hors scripts, situés dans backend/scripts/)
    required_files = [
        "state.json",
        "simulation_config.json",
        "reddit_profiles.json",
        "twitter_profiles.csv"
    ]

    # Vérifier l'existence des fichiers
    existing_files = []
    missing_files = []
    for f in required_files:
        file_path = os.path.join(simulation_dir, f)
        if os.path.exists(file_path):
            existing_files.append(f)
        else:
            missing_files.append(f)

    if missing_files:
        return False, {
            "reason": "Fichiers nécessaires manquants",
            "missing_files": missing_files,
            "existing_files": existing_files
        }

    # Vérifier le statut dans state.json
    state_file = os.path.join(simulation_dir, "state.json")
    try:
        import json
        with open(state_file, 'r', encoding='utf-8') as f:
            state_data = json.load(f)

        status = state_data.get("status", "")
        config_generated = state_data.get("config_generated", False)

        # Log détaillé
        logger.debug(f"Détection du statut de préparation de la simulation : {simulation_id}, status={status}, config_generated={config_generated}")

        # Si config_generated=True et que les fichiers existent, on considère la préparation terminée
        # Les statuts suivants indiquent tous que la préparation est terminée :
        # - ready : préparation terminée, prêt à être exécuté
        # - preparing : si config_generated=True cela signifie que c'est déjà terminé
        # - running : en cours d'exécution, donc la préparation est forcément déjà terminée
        # - completed : exécution terminée, donc la préparation est forcément déjà terminée
        # - stopped : arrêté, donc la préparation est forcément déjà terminée
        # - failed : échec de l'exécution (mais la préparation, elle, est terminée)
        prepared_statuses = ["ready", "preparing", "running", "completed", "stopped", "failed"]
        if status in prepared_statuses and config_generated:
            # Récupérer les statistiques des fichiers
            profiles_file = os.path.join(simulation_dir, "reddit_profiles.json")
            config_file = os.path.join(simulation_dir, "simulation_config.json")

            profiles_count = 0
            if os.path.exists(profiles_file):
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    profiles_data = json.load(f)
                    profiles_count = len(profiles_data) if isinstance(profiles_data, list) else 0

            # Si le statut est preparing mais que les fichiers sont déjà complets, mettre à jour automatiquement vers ready
            if status == "preparing":
                try:
                    state_data["status"] = "ready"
                    from datetime import datetime
                    state_data["updated_at"] = datetime.now().isoformat()
                    with open(state_file, 'w', encoding='utf-8') as f:
                        json.dump(state_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"Mise à jour automatique du statut de la simulation : {simulation_id} preparing -> ready")
                    status = "ready"
                except Exception as e:
                    logger.warning(f"Échec de la mise à jour automatique du statut : {e}")

            logger.info(f"Résultat de la détection pour la simulation {simulation_id} : préparation terminée (status={status}, config_generated={config_generated})")
            return True, {
                "status": status,
                "entities_count": state_data.get("entities_count", 0),
                "profiles_count": profiles_count,
                "entity_types": state_data.get("entity_types", []),
                "config_generated": config_generated,
                "created_at": state_data.get("created_at"),
                "updated_at": state_data.get("updated_at"),
                "existing_files": existing_files
            }
        else:
            logger.warning(f"Résultat de la détection pour la simulation {simulation_id} : préparation non terminée (status={status}, config_generated={config_generated})")
            return False, {
                "reason": f"Le statut n'est pas dans la liste des statuts préparés, ou config_generated est false : status={status}, config_generated={config_generated}",
                "status": status,
                "config_generated": config_generated
            }

    except Exception as e:
        return False, {"reason": f"Échec de la lecture du fichier d'état : {str(e)}"}


@simulation_bp.route('/prepare', methods=['POST'])
def prepare_simulation():
    """
    Prépare l'environnement de simulation (tâche asynchrone, tous les paramètres sont générés intelligemment par le LLM)

    C'est une opération longue ; l'interface retourne immédiatement un task_id,
    utiliser GET /api/simulation/prepare/status pour consulter la progression

    Caractéristiques :
    - Détecte automatiquement une préparation déjà terminée, pour éviter une régénération inutile
    - Si la préparation est déjà terminée, retourne directement le résultat existant
    - Prend en charge la régénération forcée (force_regenerate=true)

    Étapes :
    1. Vérifier si une préparation est déjà terminée
    2. Lire et filtrer les entités depuis le graphe Zep
    3. Générer un Profile d'Agent OASIS pour chaque entité (avec mécanisme de nouvelle tentative)
    4. Générer intelligemment la configuration de simulation via le LLM (avec mécanisme de nouvelle tentative)
    5. Sauvegarder le fichier de configuration et les scripts prédéfinis

    Requête (JSON) :
        {
            "simulation_id": "sim_xxxx",                   // obligatoire, ID de la simulation
            "entity_types": ["Student", "PublicFigure"],  // optionnel, types d'entités spécifiques
            "use_llm_for_profiles": true,                 // optionnel, générer les profils via le LLM ou non
            "parallel_profile_count": 5,                  // optionnel, nombre de profils générés en parallèle, 5 par défaut
            "force_regenerate": false                     // optionnel, régénération forcée, false par défaut
        }

    Réponse :
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "task_id": "task_xxxx",           // retourné pour une nouvelle tâche
                "status": "preparing|ready",
                "message": "Tâche de préparation lancée|Préparation déjà terminée",
                "already_prepared": true|false    // préparation déjà terminée ou non
            }
        }
    """
    import threading
    import os
    from ..models.task import TaskManager, TaskStatus
    from ..config import Config
    
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400
        
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        
        if not state:
            return jsonify({
                "success": False,
                "error": t('api.simulationNotFound', id=simulation_id)
            }), 404
        
        # Vérifier si une régénération forcée est demandée
        force_regenerate = data.get('force_regenerate', False)
        logger.info(f"Début du traitement de la requête /prepare : simulation_id={simulation_id}, force_regenerate={force_regenerate}")

        # Vérifier si la préparation est déjà terminée (pour éviter une régénération inutile)
        if not force_regenerate:
            logger.debug(f"Vérification si la simulation {simulation_id} est déjà préparée...")
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
            logger.debug(f"Résultat de la vérification : is_prepared={is_prepared}, prepare_info={prepare_info}")
            if is_prepared:
                logger.info(f"La simulation {simulation_id} est déjà préparée, on saute la régénération")
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "status": "ready",
                        "message": t('api.alreadyPrepared'),
                        "already_prepared": True,
                        "prepare_info": prepare_info
                    }
                })
            else:
                logger.info(f"La simulation {simulation_id} n'est pas encore préparée, lancement de la tâche de préparation")

        # Récupérer les informations nécessaires depuis le projet
        project = ProjectManager.get_project(state.project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": t('api.projectNotFound', id=state.project_id)
            }), 404
        
        # Récupérer le besoin de simulation
        simulation_requirement = project.simulation_requirement or ""
        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": t('api.projectMissingRequirement')
            }), 400

        # Récupérer le texte du document
        document_text = ProjectManager.get_extracted_text(state.project_id) or ""

        entity_types_list = data.get('entity_types')
        use_llm_for_profiles = data.get('use_llm_for_profiles', True)
        parallel_profile_count = data.get('parallel_profile_count', 5)

        # ========== Récupération synchrone du nombre d'entités (avant le lancement de la tâche en arrière-plan) ==========
        # Cela permet au frontend d'obtenir immédiatement le nombre total d'Agents attendu après l'appel à prepare
        try:
            logger.info(f"Récupération synchrone du nombre d'entités : graph_id={state.graph_id}")
            reader = ZepEntityReader()
            # Lecture rapide des entités (pas besoin des informations d'arêtes, juste le comptage)
            filtered_preview = reader.filter_defined_entities(
                graph_id=state.graph_id,
                defined_entity_types=entity_types_list,
                enrich_with_edges=False  # Ne pas récupérer les informations d'arêtes, pour accélérer
            )
            # Sauvegarder le nombre d'entités dans l'état (pour récupération immédiate côté frontend)
            state.entities_count = filtered_preview.filtered_count
            state.entity_types = list(filtered_preview.entity_types)
            logger.info(f"Nombre d'entités attendu : {filtered_preview.filtered_count}, types : {filtered_preview.entity_types}")
        except Exception as e:
            logger.warning(f"Échec de la récupération synchrone du nombre d'entités (nouvelle tentative dans la tâche en arrière-plan) : {e}")
            # Un échec ici n'affecte pas la suite, la tâche en arrière-plan la récupérera à nouveau

        # Créer la tâche asynchrone
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="simulation_prepare",
            metadata={
                "simulation_id": simulation_id,
                "project_id": state.project_id
            }
        )
        
        # Mettre à jour l'état de la simulation (inclut le nombre d'entités récupéré à l'avance)
        state.status = SimulationStatus.PREPARING
        manager._save_simulation_state(state)

        # Capture locale before spawning background thread
        current_locale = get_locale()

        # Définition de la tâche en arrière-plan
        def run_prepare():
            set_locale(current_locale)
            try:
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.PROCESSING,
                    progress=0,
                    message=t('progress.startPreparingEnv')
                )

                # Préparer la simulation (avec callback de progression)
                # Stocker les détails de progression par étape
                stage_details = {}

                def progress_callback(stage, progress, message, **kwargs):
                    # Calculer la progression totale
                    stage_weights = {
                        "reading": (0, 20),           # 0-20%
                        "generating_profiles": (20, 70),  # 20-70%
                        "generating_config": (70, 90),    # 70-90%
                        "copying_scripts": (90, 100)       # 90-100%
                    }

                    start, end = stage_weights.get(stage, (0, 100))
                    current_progress = int(start + (end - start) * progress / 100)

                    # Construire les informations de progression détaillées
                    stage_names = {
                        "reading": t('progress.readingGraphEntities'),
                        "generating_profiles": t('progress.generatingProfiles'),
                        "generating_config": t('progress.generatingSimConfig'),
                        "copying_scripts": t('progress.preparingScripts')
                    }

                    stage_index = list(stage_weights.keys()).index(stage) + 1 if stage in stage_weights else 1
                    total_stages = len(stage_weights)

                    # Mettre à jour les détails de l'étape
                    stage_details[stage] = {
                        "stage_name": stage_names.get(stage, stage),
                        "stage_progress": progress,
                        "current": kwargs.get("current", 0),
                        "total": kwargs.get("total", 0),
                        "item_name": kwargs.get("item_name", "")
                    }

                    # Construire les informations de progression détaillées
                    detail = stage_details[stage]
                    progress_detail_data = {
                        "current_stage": stage,
                        "current_stage_name": stage_names.get(stage, stage),
                        "stage_index": stage_index,
                        "total_stages": total_stages,
                        "stage_progress": progress,
                        "current_item": detail["current"],
                        "total_items": detail["total"],
                        "item_description": message
                    }

                    # Construire un message concis
                    if detail["total"] > 0:
                        detailed_message = (
                            f"[{stage_index}/{total_stages}] {stage_names.get(stage, stage)}: "
                            f"{detail['current']}/{detail['total']} - {message}"
                        )
                    else:
                        detailed_message = f"[{stage_index}/{total_stages}] {stage_names.get(stage, stage)}: {message}"
                    
                    task_manager.update_task(
                        task_id,
                        progress=current_progress,
                        message=detailed_message,
                        progress_detail=progress_detail_data
                    )
                
                result_state = manager.prepare_simulation(
                    simulation_id=simulation_id,
                    simulation_requirement=simulation_requirement,
                    document_text=document_text,
                    defined_entity_types=entity_types_list,
                    use_llm_for_profiles=use_llm_for_profiles,
                    progress_callback=progress_callback,
                    parallel_profile_count=parallel_profile_count
                )

                # Tâche terminée
                task_manager.complete_task(
                    task_id,
                    result=result_state.to_simple_dict()
                )

            except Exception as e:
                logger.error(f"Échec de la préparation de la simulation : {str(e)}")
                task_manager.fail_task(task_id, str(e))

                # Mettre à jour l'état de la simulation en échec
                state = manager.get_simulation(simulation_id)
                if state:
                    state.status = SimulationStatus.FAILED
                    state.error = str(e)
                    manager._save_simulation_state(state)

        # Lancer le thread en arrière-plan
        thread = threading.Thread(target=run_prepare, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "task_id": task_id,
                "status": "preparing",
                "message": t('api.prepareStarted'),
                "already_prepared": False,
                "expected_entities_count": state.entities_count,  # nombre total d'Agents attendu
                "entity_types": state.entity_types  # liste des types d'entités
            }
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 404
        
    except Exception as e:
        logger.error(f"Échec du lancement de la tâche de préparation : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/prepare/status', methods=['POST'])
def get_prepare_status():
    """
    Interroge la progression de la tâche de préparation

    Prend en charge deux modes d'interrogation :
    1. Via task_id, pour interroger la progression d'une tâche en cours
    2. Via simulation_id, pour vérifier si une préparation est déjà terminée

    Requête (JSON) :
        {
            "task_id": "task_xxxx",          // optionnel, task_id retourné par prepare
            "simulation_id": "sim_xxxx"      // optionnel, ID de la simulation (pour vérifier une préparation déjà terminée)
        }

    Réponse :
        {
            "success": true,
            "data": {
                "task_id": "task_xxxx",
                "status": "processing|completed|ready",
                "progress": 45,
                "message": "...",
                "already_prepared": true|false,  // préparation déjà terminée ou non
                "prepare_info": {...}            // informations détaillées si déjà préparé
            }
        }
    """
    from ..models.task import TaskManager
    
    try:
        data = request.get_json() or {}
        
        task_id = data.get('task_id')
        simulation_id = data.get('simulation_id')
        
        # Si simulation_id est fourni, vérifier d'abord si la préparation est déjà terminée
        if simulation_id:
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
            if is_prepared:
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "status": "ready",
                        "progress": 100,
                        "message": t('api.alreadyPrepared'),
                        "already_prepared": True,
                        "prepare_info": prepare_info
                    }
                })
        
        # Si task_id n'est pas fourni, retourner une erreur
        if not task_id:
            if simulation_id:
                # simulation_id fourni mais préparation non terminée
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "status": "not_started",
                        "progress": 0,
                        "message": t('api.notStartedPrepare'),
                        "already_prepared": False
                    }
                })
            return jsonify({
                "success": False,
                "error": t('api.requireTaskOrSimId')
            }), 400
        
        task_manager = TaskManager()
        task = task_manager.get_task(task_id)
        
        if not task:
            # La tâche n'existe pas, mais si simulation_id est fourni, vérifier si la préparation est déjà terminée
            if simulation_id:
                is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
                if is_prepared:
                    return jsonify({
                        "success": True,
                        "data": {
                            "simulation_id": simulation_id,
                            "task_id": task_id,
                            "status": "ready",
                            "progress": 100,
                            "message": t('api.taskCompletedPrepared'),
                            "already_prepared": True,
                            "prepare_info": prepare_info
                        }
                    })
            
            return jsonify({
                "success": False,
                "error": t('api.taskNotFound', id=task_id)
            }), 404
        
        task_dict = task.to_dict()
        task_dict["already_prepared"] = False
        
        return jsonify({
            "success": True,
            "data": task_dict
        })
        
    except Exception as e:
        logger.error(f"Échec de l'interrogation du statut de la tâche : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@simulation_bp.route('/<simulation_id>', methods=['GET'])
def get_simulation(simulation_id: str):
    """Récupère l'état de la simulation"""
    try:
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        
        if not state:
            return jsonify({
                "success": False,
                "error": t('api.simulationNotFound', id=simulation_id)
            }), 404
        
        result = state.to_dict()

        # Si la simulation est prête, ajouter les instructions d'exécution
        if state.status == SimulationStatus.READY:
            result["run_instructions"] = manager.get_run_instructions(simulation_id)
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de l'état de la simulation : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/list', methods=['GET'])
def list_simulations():
    """
    Liste toutes les simulations

    Paramètres de requête :
        project_id: filtre par ID de projet (optionnel)
    """
    try:
        project_id = request.args.get('project_id')
        
        manager = SimulationManager()
        simulations = manager.list_simulations(project_id=project_id)
        
        return jsonify({
            "success": True,
            "data": [s.to_dict() for s in simulations],
            "count": len(simulations)
        })
        
    except Exception as e:
        logger.error(f"Échec du listage des simulations : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


def _get_report_id_for_simulation(simulation_id: str) -> str:
    """
    Récupère le report_id le plus récent correspondant à une simulation

    Parcourt le répertoire reports, trouve les reports dont le simulation_id correspond,
    et retourne le plus récent s'il y en a plusieurs (trié par created_at)

    Args:
        simulation_id: ID de la simulation

    Returns:
        report_id ou None
    """
    import json
    from datetime import datetime

    # Chemin du répertoire reports : backend/uploads/reports
    # __file__ est app/api/simulation.py, il faut remonter de deux niveaux jusqu'à backend/
    reports_dir = os.path.join(os.path.dirname(__file__), '../../uploads/reports')
    if not os.path.exists(reports_dir):
        return None

    matching_reports = []

    try:
        for report_folder in os.listdir(reports_dir):
            report_path = os.path.join(reports_dir, report_folder)
            if not os.path.isdir(report_path):
                continue

            meta_file = os.path.join(report_path, "meta.json")
            if not os.path.exists(meta_file):
                continue

            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)

                if meta.get("simulation_id") == simulation_id:
                    matching_reports.append({
                        "report_id": meta.get("report_id"),
                        "created_at": meta.get("created_at", ""),
                        "status": meta.get("status", "")
                    })
            except Exception:
                continue

        if not matching_reports:
            return None

        # Trier par date de création décroissante, retourner le plus récent
        matching_reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return matching_reports[0].get("report_id")

    except Exception as e:
        logger.warning(f"Échec de la recherche du report pour la simulation {simulation_id} : {e}")
        return None


@simulation_bp.route('/history', methods=['GET'])
def get_simulation_history():
    """
    Récupère la liste des simulations passées (avec détails du projet)

    Utilisé pour l'affichage des projets historiques sur la page d'accueil ; retourne une liste de
    simulations enrichie d'informations comme le nom du projet, la description, etc.

    Paramètres de requête :
        limit: limite du nombre de résultats retournés (20 par défaut)

    Réponse :
        {
            "success": true,
            "data": [
                {
                    "simulation_id": "sim_xxxx",
                    "project_id": "proj_xxxx",
                    "project_name": "Analyse d'opinion sur le projet de loi X",
                    "simulation_requirement": "Si le texte de loi X était adopté...",
                    "status": "completed",
                    "entities_count": 68,
                    "profiles_count": 68,
                    "entity_types": ["Student", "Professor", ...],
                    "created_at": "2024-12-10",
                    "updated_at": "2024-12-10",
                    "total_rounds": 120,
                    "current_round": 120,
                    "report_id": "report_xxxx",
                    "version": "v1.0.2"
                },
                ...
            ],
            "count": 7
        }
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        
        manager = SimulationManager()
        simulations = manager.list_simulations()[:limit]
        
        # Enrichir les données de simulation, en lisant uniquement depuis les fichiers Simulation
        enriched_simulations = []
        for sim in simulations:
            sim_dict = sim.to_dict()

            # Récupérer les informations de configuration de simulation (lire simulation_requirement depuis simulation_config.json)
            config = manager.get_simulation_config(sim.simulation_id)
            if config:
                sim_dict["simulation_requirement"] = config.get("simulation_requirement", "")
                time_config = config.get("time_config", {})
                sim_dict["total_simulation_hours"] = time_config.get("total_simulation_hours", 0)
                # Nombre de tours recommandé (valeur de repli)
                recommended_rounds = int(
                    time_config.get("total_simulation_hours", 0) * 60 /
                    max(time_config.get("minutes_per_round", 60), 1)
                )
            else:
                sim_dict["simulation_requirement"] = ""
                sim_dict["total_simulation_hours"] = 0
                recommended_rounds = 0

            # Récupérer l'état d'exécution (lire depuis run_state.json le nombre de tours réel défini par l'utilisateur)
            run_state = SimulationRunner.get_run_state(sim.simulation_id)
            if run_state:
                sim_dict["current_round"] = run_state.current_round
                sim_dict["runner_status"] = run_state.runner_status.value
                # Utiliser le total_rounds défini par l'utilisateur, sinon utiliser le nombre recommandé
                sim_dict["total_rounds"] = run_state.total_rounds if run_state.total_rounds > 0 else recommended_rounds
            else:
                sim_dict["current_round"] = 0
                sim_dict["runner_status"] = "idle"
                sim_dict["total_rounds"] = recommended_rounds

            # Récupérer la liste des fichiers du projet associé (3 maximum)
            project = ProjectManager.get_project(sim.project_id)
            if project and hasattr(project, 'files') and project.files:
                sim_dict["files"] = [
                    {"filename": f.get("filename", "Fichier inconnu")}
                    for f in project.files[:3]
                ]
            else:
                sim_dict["files"] = []

            # Récupérer le report_id associé (chercher le report le plus récent pour cette simulation)
            sim_dict["report_id"] = _get_report_id_for_simulation(sim.simulation_id)

            # Ajouter le numéro de version
            sim_dict["version"] = "v1.0.2"

            # Formater la date
            try:
                created_date = sim_dict.get("created_at", "")[:10]
                sim_dict["created_date"] = created_date
            except:
                sim_dict["created_date"] = ""

            enriched_simulations.append(sim_dict)
        
        return jsonify({
            "success": True,
            "data": enriched_simulations,
            "count": len(enriched_simulations)
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de l'historique des simulations : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/profiles', methods=['GET'])
def get_simulation_profiles(simulation_id: str):
    """
    Récupère les Profiles d'Agent de la simulation

    Paramètres de requête :
        platform: type de plateforme (reddit/twitter, reddit par défaut)
    """
    try:
        platform = request.args.get('platform', 'reddit')
        
        manager = SimulationManager()
        profiles = manager.get_profiles(simulation_id, platform=platform)
        
        return jsonify({
            "success": True,
            "data": {
                "platform": platform,
                "count": len(profiles),
                "profiles": profiles
            }
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 404
        
    except Exception as e:
        logger.error(f"Échec de la récupération des Profiles : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/profiles/realtime', methods=['GET'])
def get_simulation_profiles_realtime(simulation_id: str):
    """
    Récupère en temps réel les Profiles d'Agent de la simulation (pour suivre la progression pendant la génération)

    Différence avec l'interface /profiles :
    - Lit directement le fichier, sans passer par SimulationManager
    - Adapté au suivi en temps réel pendant la génération
    - Retourne des métadonnées supplémentaires (heure de modification du fichier, génération en cours, etc.)

    Paramètres de requête :
        platform: type de plateforme (reddit/twitter, reddit par défaut)

    Réponse :
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "platform": "reddit",
                "count": 15,
                "total_expected": 93,  // total attendu (si disponible)
                "is_generating": true,  // génération en cours ou non
                "file_exists": true,
                "file_modified_at": "2025-12-04T18:20:00",
                "profiles": [...]
            }
        }
    """
    import json
    import csv
    from datetime import datetime
    
    try:
        platform = request.args.get('platform', 'reddit')
        
        # Récupérer le répertoire de simulation
        sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)

        if not os.path.exists(sim_dir):
            return jsonify({
                "success": False,
                "error": t('api.simulationNotFound', id=simulation_id)
            }), 404

        # Déterminer le chemin du fichier
        if platform == "reddit":
            profiles_file = os.path.join(sim_dir, "reddit_profiles.json")
        else:
            profiles_file = os.path.join(sim_dir, "twitter_profiles.csv")

        # Vérifier l'existence du fichier
        file_exists = os.path.exists(profiles_file)
        profiles = []
        file_modified_at = None

        if file_exists:
            # Récupérer l'heure de modification du fichier
            file_stat = os.stat(profiles_file)
            file_modified_at = datetime.fromtimestamp(file_stat.st_mtime).isoformat()

            try:
                if platform == "reddit":
                    with open(profiles_file, 'r', encoding='utf-8') as f:
                        profiles = json.load(f)
                else:
                    with open(profiles_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        profiles = list(reader)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Échec de la lecture du fichier profiles (peut-être en cours d'écriture) : {e}")
                profiles = []

        # Vérifier si une génération est en cours (via state.json)
        is_generating = False
        total_expected = None

        state_file = os.path.join(sim_dir, "state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    status = state_data.get("status", "")
                    is_generating = status == "preparing"
                    total_expected = state_data.get("entities_count")
            except Exception:
                pass
        
        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "platform": platform,
                "count": len(profiles),
                "total_expected": total_expected,
                "is_generating": is_generating,
                "file_exists": file_exists,
                "file_modified_at": file_modified_at,
                "profiles": profiles
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération en temps réel des Profiles : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/config/realtime', methods=['GET'])
def get_simulation_config_realtime(simulation_id: str):
    """
    Récupère en temps réel la configuration de simulation (pour suivre la progression pendant la génération)

    Différence avec l'interface /config :
    - Lit directement le fichier, sans passer par SimulationManager
    - Adapté au suivi en temps réel pendant la génération
    - Retourne des métadonnées supplémentaires (heure de modification du fichier, génération en cours, etc.)
    - Peut retourner des informations partielles même si la configuration n'est pas encore entièrement générée

    Réponse :
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "file_exists": true,
                "file_modified_at": "2025-12-04T18:20:00",
                "is_generating": true,  // génération en cours ou non
                "generation_stage": "generating_config",  // étape de génération actuelle
                "config": {...}  // contenu de la configuration (si présent)
            }
        }
    """
    import json
    from datetime import datetime
    
    try:
        # Récupérer le répertoire de simulation
        sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)

        if not os.path.exists(sim_dir):
            return jsonify({
                "success": False,
                "error": t('api.simulationNotFound', id=simulation_id)
            }), 404

        # Chemin du fichier de configuration
        config_file = os.path.join(sim_dir, "simulation_config.json")

        # Vérifier l'existence du fichier
        file_exists = os.path.exists(config_file)
        config = None
        file_modified_at = None

        if file_exists:
            # Récupérer l'heure de modification du fichier
            file_stat = os.stat(config_file)
            file_modified_at = datetime.fromtimestamp(file_stat.st_mtime).isoformat()

            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Échec de la lecture du fichier config (peut-être en cours d'écriture) : {e}")
                config = None

        # Vérifier si une génération est en cours (via state.json)
        is_generating = False
        generation_stage = None
        config_generated = False

        state_file = os.path.join(sim_dir, "state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    status = state_data.get("status", "")
                    is_generating = status == "preparing"
                    config_generated = state_data.get("config_generated", False)

                    # Déterminer l'étape actuelle
                    if is_generating:
                        if state_data.get("profiles_generated", False):
                            generation_stage = "generating_config"
                        else:
                            generation_stage = "generating_profiles"
                    elif status == "ready":
                        generation_stage = "completed"
            except Exception:
                pass

        # Construire les données de réponse
        response_data = {
            "simulation_id": simulation_id,
            "file_exists": file_exists,
            "file_modified_at": file_modified_at,
            "is_generating": is_generating,
            "generation_stage": generation_stage,
            "config_generated": config_generated,
            "config": config
        }

        # Si la configuration existe, extraire quelques statistiques clés
        if config:
            response_data["summary"] = {
                "total_agents": len(config.get("agent_configs", [])),
                "simulation_hours": config.get("time_config", {}).get("total_simulation_hours"),
                "initial_posts_count": len(config.get("event_config", {}).get("initial_posts", [])),
                "hot_topics_count": len(config.get("event_config", {}).get("hot_topics", [])),
                "has_twitter_config": "twitter_config" in config,
                "has_reddit_config": "reddit_config" in config,
                "generated_at": config.get("generated_at"),
                "llm_model": config.get("llm_model")
            }
        
        return jsonify({
            "success": True,
            "data": response_data
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération en temps réel de la Config : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/config', methods=['GET'])
def get_simulation_config(simulation_id: str):
    """
    Récupère la configuration de simulation (configuration complète générée intelligemment par le LLM)

    La réponse contient :
        - time_config : configuration temporelle (durée de simulation, tours, périodes de pointe/creuses)
        - agent_configs : configuration d'activité de chaque Agent (niveau d'activité, fréquence de prise de parole, position, etc.)
        - event_config : configuration des événements (posts initiaux, sujets brûlants)
        - platform_configs : configuration des plateformes
        - generation_reasoning : explication du raisonnement du LLM pour la configuration
    """
    try:
        manager = SimulationManager()
        config = manager.get_simulation_config(simulation_id)
        
        if not config:
            return jsonify({
                "success": False,
                "error": t('api.configNotFound')
            }), 404
        
        return jsonify({
            "success": True,
            "data": config
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de la configuration : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/config/download', methods=['GET'])
def download_simulation_config(simulation_id: str):
    """Télécharge le fichier de configuration de simulation"""
    try:
        manager = SimulationManager()
        sim_dir = manager._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        
        if not os.path.exists(config_path):
            return jsonify({
                "success": False,
                "error": t('api.configFileNotFound')
            }), 404
        
        return send_file(
            config_path,
            as_attachment=True,
            download_name="simulation_config.json"
        )
        
    except Exception as e:
        logger.error(f"Échec du téléchargement de la configuration : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/script/<script_name>/download', methods=['GET'])
def download_simulation_script(script_name: str):
    """
    Télécharge un fichier de script d'exécution de simulation (script générique, situé dans backend/scripts/)

    Valeurs possibles pour script_name :
        - run_twitter_simulation.py
        - run_reddit_simulation.py
        - run_parallel_simulation.py
        - action_logger.py
    """
    try:
        # Le script se trouve dans le répertoire backend/scripts/
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts'))

        # Valider le nom du script
        allowed_scripts = [
            "run_twitter_simulation.py",
            "run_reddit_simulation.py", 
            "run_parallel_simulation.py",
            "action_logger.py"
        ]
        
        if script_name not in allowed_scripts:
            return jsonify({
                "success": False,
                "error": t('api.unknownScript', name=script_name, allowed=allowed_scripts)
            }), 400
        
        script_path = os.path.join(scripts_dir, script_name)
        
        if not os.path.exists(script_path):
            return jsonify({
                "success": False,
                "error": t('api.scriptFileNotFound', name=script_name)
            }), 404
        
        return send_file(
            script_path,
            as_attachment=True,
            download_name=script_name
        )
        
    except Exception as e:
        logger.error(f"Échec du téléchargement du script : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Interface de génération de Profile (usage autonome) ==============

@simulation_bp.route('/generate-profiles', methods=['POST'])
def generate_profiles():
    """
    Génère directement des Profiles d'Agent OASIS à partir du graphe (sans créer de simulation)

    Requête (JSON) :
        {
            "graph_id": "mirofish_xxxx",     // obligatoire
            "entity_types": ["Student"],      // optionnel
            "use_llm": true,                  // optionnel
            "platform": "reddit"              // optionnel
        }
    """
    try:
        data = request.get_json() or {}
        
        graph_id = data.get('graph_id')
        if not graph_id:
            return jsonify({
                "success": False,
                "error": t('api.requireGraphId')
            }), 400
        
        entity_types = data.get('entity_types')
        use_llm = data.get('use_llm', True)
        platform = data.get('platform', 'reddit')
        
        reader = ZepEntityReader()
        filtered = reader.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=entity_types,
            enrich_with_edges=True
        )
        
        if filtered.filtered_count == 0:
            return jsonify({
                "success": False,
                "error": t('api.noMatchingEntities')
            }), 400
        
        generator = OasisProfileGenerator()
        profiles = generator.generate_profiles_from_entities(
            entities=filtered.entities,
            use_llm=use_llm
        )
        
        if platform == "reddit":
            profiles_data = [p.to_reddit_format() for p in profiles]
        elif platform == "twitter":
            profiles_data = [p.to_twitter_format() for p in profiles]
        else:
            profiles_data = [p.to_dict() for p in profiles]
        
        return jsonify({
            "success": True,
            "data": {
                "platform": platform,
                "entity_types": list(filtered.entity_types),
                "count": len(profiles_data),
                "profiles": profiles_data
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la génération des Profiles : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Interface de contrôle d'exécution de la simulation ==============

@simulation_bp.route('/start', methods=['POST'])
def start_simulation():
    """
    Démarre l'exécution de la simulation

    Requête (JSON) :
        {
            "simulation_id": "sim_xxxx",          // obligatoire, ID de la simulation
            "platform": "parallel",                // optionnel : twitter / reddit / parallel (par défaut)
            "max_rounds": 100,                     // optionnel : nombre maximal de tours de simulation, pour tronquer les simulations trop longues
            "enable_graph_memory_update": false,   // optionnel : mettre à jour dynamiquement ou non la mémoire du graphe Zep avec l'activité des Agents
            "force": false                         // optionnel : redémarrage forcé (arrête la simulation en cours et nettoie les logs)
        }

    À propos du paramètre force :
        - Une fois activé, si la simulation est en cours d'exécution ou déjà terminée, elle est d'abord arrêtée puis les logs d'exécution sont nettoyés
        - Le nettoyage inclut : run_state.json, actions.jsonl, simulation.log, etc.
        - Le fichier de configuration (simulation_config.json) et les fichiers profile ne sont pas nettoyés
        - Adapté aux scénarios nécessitant de relancer la simulation

    À propos de enable_graph_memory_update :
        - Une fois activé, toute l'activité des Agents dans la simulation (publications, commentaires, likes, etc.) est mise à jour en temps réel dans le graphe Zep
        - Cela permet au graphe de « se souvenir » du déroulement de la simulation, pour une analyse ultérieure ou un dialogue avec l'IA
        - Nécessite que le projet associé à la simulation ait un graph_id valide
        - Utilise un mécanisme de mise à jour par lots pour réduire le nombre d'appels API

    Réponse :
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "runner_status": "running",
                "process_pid": 12345,
                "twitter_running": true,
                "reddit_running": true,
                "started_at": "2025-12-01T10:00:00",
                "graph_memory_update_enabled": true,  // mise à jour de la mémoire du graphe activée ou non
                "force_restarted": true               // redémarrage forcé ou non
            }
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        platform = data.get('platform', 'parallel')
        max_rounds = data.get('max_rounds')  # optionnel : nombre maximal de tours de simulation
        enable_graph_memory_update = data.get('enable_graph_memory_update', False)  # optionnel : activer ou non la mise à jour de la mémoire du graphe
        force = data.get('force', False)  # optionnel : redémarrage forcé

        # Valider le paramètre max_rounds
        if max_rounds is not None:
            try:
                max_rounds = int(max_rounds)
                if max_rounds <= 0:
                    return jsonify({
                        "success": False,
                        "error": t('api.maxRoundsPositive')
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    "success": False,
                    "error": t('api.maxRoundsInvalid')
                }), 400

        if platform not in ['twitter', 'reddit', 'parallel']:
            return jsonify({
                "success": False,
                "error": t('api.invalidPlatform', platform=platform)
            }), 400

        # Vérifier si la simulation est prête
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)

        if not state:
            return jsonify({
                "success": False,
                "error": t('api.simulationNotFound', id=simulation_id)
            }), 404

        force_restarted = False

        # Traitement intelligent de l'état : si la préparation est terminée, autoriser le redémarrage
        if state.status != SimulationStatus.READY:
            # Vérifier si la préparation est terminée
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)

            if is_prepared:
                # Préparation terminée, vérifier s'il y a un processus en cours d'exécution
                if state.status == SimulationStatus.RUNNING:
                    # Vérifier si le processus de simulation est réellement en cours d'exécution
                    run_state = SimulationRunner.get_run_state(simulation_id)
                    if run_state and run_state.runner_status.value == "running":
                        # Le processus est bien en cours d'exécution
                        if force:
                            # Mode forcé : arrêter la simulation en cours
                            logger.info(f"Mode forcé : arrêt de la simulation en cours {simulation_id}")
                            try:
                                SimulationRunner.stop_simulation(simulation_id)
                            except Exception as e:
                                logger.warning(f"Avertissement lors de l'arrêt de la simulation : {str(e)}")
                        else:
                            return jsonify({
                                "success": False,
                                "error": t('api.simRunningForceHint')
                            }), 400

                # En mode forcé, nettoyer les logs d'exécution
                if force:
                    logger.info(f"Mode forcé : nettoyage des logs de simulation {simulation_id}")
                    cleanup_result = SimulationRunner.cleanup_simulation_logs(simulation_id)
                    if not cleanup_result.get("success"):
                        logger.warning(f"Avertissement lors du nettoyage des logs : {cleanup_result.get('errors')}")
                    force_restarted = True

                # Le processus n'existe pas ou est terminé, réinitialiser l'état à ready
                logger.info(f"Préparation de la simulation {simulation_id} terminée, réinitialisation de l'état à ready (état précédent : {state.status.value})")
                state.status = SimulationStatus.READY
                manager._save_simulation_state(state)
            else:
                # Préparation non terminée
                return jsonify({
                    "success": False,
                    "error": t('api.simNotReady', status=state.status.value)
                }), 400

        # Récupérer l'ID du graphe (pour la mise à jour de la mémoire du graphe)
        graph_id = None
        if enable_graph_memory_update:
            # Récupérer le graph_id depuis l'état de la simulation ou le projet
            graph_id = state.graph_id
            if not graph_id:
                # Tenter de le récupérer depuis le projet
                project = ProjectManager.get_project(state.project_id)
                if project:
                    graph_id = project.graph_id

            if not graph_id:
                return jsonify({
                    "success": False,
                    "error": t('api.graphIdRequiredForMemory')
                }), 400

            logger.info(f"Activation de la mise à jour de la mémoire du graphe : simulation_id={simulation_id}, graph_id={graph_id}")

        # Démarrer la simulation
        run_state = SimulationRunner.start_simulation(
            simulation_id=simulation_id,
            platform=platform,
            max_rounds=max_rounds,
            enable_graph_memory_update=enable_graph_memory_update,
            graph_id=graph_id
        )
        
        # Mettre à jour l'état de la simulation
        state.status = SimulationStatus.RUNNING
        manager._save_simulation_state(state)

        response_data = run_state.to_dict()
        if max_rounds:
            response_data['max_rounds_applied'] = max_rounds
        response_data['graph_memory_update_enabled'] = enable_graph_memory_update
        response_data['force_restarted'] = force_restarted
        if enable_graph_memory_update:
            response_data['graph_id'] = graph_id
        
        return jsonify({
            "success": True,
            "data": response_data
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Échec du démarrage de la simulation : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/stop', methods=['POST'])
def stop_simulation():
    """
    Arrête la simulation

    Requête (JSON) :
        {
            "simulation_id": "sim_xxxx"  // obligatoire, ID de la simulation
        }

    Réponse :
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "runner_status": "stopped",
                "completed_at": "2025-12-01T12:00:00"
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400
        
        run_state = SimulationRunner.stop_simulation(simulation_id)

        # Mettre à jour l'état de la simulation
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if state:
            state.status = SimulationStatus.PAUSED
            manager._save_simulation_state(state)
        
        return jsonify({
            "success": True,
            "data": run_state.to_dict()
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Échec de l'arrêt de la simulation : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Interface de suivi de l'état en temps réel ==============

@simulation_bp.route('/<simulation_id>/run-status', methods=['GET'])
def get_run_status(simulation_id: str):
    """
    Récupère l'état d'exécution en temps réel de la simulation (pour le polling côté frontend)

    Réponse :
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "runner_status": "running",
                "current_round": 5,
                "total_rounds": 144,
                "progress_percent": 3.5,
                "simulated_hours": 2,
                "total_simulation_hours": 72,
                "twitter_running": true,
                "reddit_running": true,
                "twitter_actions_count": 150,
                "reddit_actions_count": 200,
                "total_actions_count": 350,
                "started_at": "2025-12-01T10:00:00",
                "updated_at": "2025-12-01T10:30:00"
            }
        }
    """
    try:
        run_state = SimulationRunner.get_run_state(simulation_id)
        
        if not run_state:
            return jsonify({
                "success": True,
                "data": {
                    "simulation_id": simulation_id,
                    "runner_status": "idle",
                    "current_round": 0,
                    "total_rounds": 0,
                    "progress_percent": 0,
                    "twitter_actions_count": 0,
                    "reddit_actions_count": 0,
                    "total_actions_count": 0,
                }
            })
        
        return jsonify({
            "success": True,
            "data": run_state.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de l'état d'exécution : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/run-status/detail', methods=['GET'])
def get_run_status_detail(simulation_id: str):
    """
    Récupère l'état d'exécution détaillé de la simulation (inclut toutes les actions)

    Utilisé pour afficher l'activité en temps réel côté frontend

    Paramètres de requête :
        platform: filtre par plateforme (twitter/reddit, optionnel)

    Réponse :
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "runner_status": "running",
                "current_round": 5,
                ...
                "all_actions": [
                    {
                        "round_num": 5,
                        "timestamp": "2025-12-01T10:30:00",
                        "platform": "twitter",
                        "agent_id": 3,
                        "agent_name": "Agent Name",
                        "action_type": "CREATE_POST",
                        "action_args": {"content": "..."},
                        "result": null,
                        "success": true
                    },
                    ...
                ],
                "twitter_actions": [...],  # toutes les actions de la plateforme Twitter
                "reddit_actions": [...]    # toutes les actions de la plateforme Reddit
            }
        }
    """
    try:
        run_state = SimulationRunner.get_run_state(simulation_id)
        platform_filter = request.args.get('platform')
        
        if not run_state:
            return jsonify({
                "success": True,
                "data": {
                    "simulation_id": simulation_id,
                    "runner_status": "idle",
                    "all_actions": [],
                    "twitter_actions": [],
                    "reddit_actions": []
                }
            })
        
        # Récupérer la liste complète des actions
        all_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform=platform_filter
        )

        # Récupérer les actions par plateforme
        twitter_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform="twitter"
        ) if not platform_filter or platform_filter == "twitter" else []

        reddit_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform="reddit"
        ) if not platform_filter or platform_filter == "reddit" else []

        # Récupérer les actions du tour actuel (recent_actions n'affiche que le tour le plus récent)
        current_round = run_state.current_round
        recent_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform=platform_filter,
            round_num=current_round
        ) if current_round > 0 else []

        # Récupérer les informations d'état de base
        result = run_state.to_dict()
        result["all_actions"] = [a.to_dict() for a in all_actions]
        result["twitter_actions"] = [a.to_dict() for a in twitter_actions]
        result["reddit_actions"] = [a.to_dict() for a in reddit_actions]
        result["rounds_count"] = len(run_state.rounds)
        # recent_actions n'affiche que le contenu des deux plateformes pour le tour le plus récent
        result["recent_actions"] = [a.to_dict() for a in recent_actions]

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        logger.error(f"Échec de la récupération de l'état détaillé : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/actions', methods=['GET'])
def get_simulation_actions(simulation_id: str):
    """
    Récupère l'historique des actions des Agents dans la simulation

    Paramètres de requête :
        limit: nombre de résultats retournés (100 par défaut)
        offset: décalage (0 par défaut)
        platform: filtre par plateforme (twitter/reddit)
        agent_id: filtre par ID d'Agent
        round_num: filtre par tour

    Réponse :
        {
            "success": true,
            "data": {
                "count": 100,
                "actions": [...]
            }
        }
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        platform = request.args.get('platform')
        agent_id = request.args.get('agent_id', type=int)
        round_num = request.args.get('round_num', type=int)
        
        actions = SimulationRunner.get_actions(
            simulation_id=simulation_id,
            limit=limit,
            offset=offset,
            platform=platform,
            agent_id=agent_id,
            round_num=round_num
        )
        
        return jsonify({
            "success": True,
            "data": {
                "count": len(actions),
                "actions": [a.to_dict() for a in actions]
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de l'historique des actions : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/timeline', methods=['GET'])
def get_simulation_timeline(simulation_id: str):
    """
    Récupère la chronologie de la simulation (agrégée par tour)

    Utilisé pour afficher la barre de progression et la vue chronologique côté frontend

    Paramètres de requête :
        start_round: tour de départ (0 par défaut)
        end_round: tour de fin (tous par défaut)

    Retourne les informations agrégées de chaque tour
    """
    try:
        start_round = request.args.get('start_round', 0, type=int)
        end_round = request.args.get('end_round', type=int)
        
        timeline = SimulationRunner.get_timeline(
            simulation_id=simulation_id,
            start_round=start_round,
            end_round=end_round
        )
        
        return jsonify({
            "success": True,
            "data": {
                "rounds_count": len(timeline),
                "timeline": timeline
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de la chronologie : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/agent-stats', methods=['GET'])
def get_agent_stats(simulation_id: str):
    """
    Récupère les statistiques de chaque Agent

    Utilisé pour afficher le classement d'activité des Agents, la répartition des actions, etc. côté frontend
    """
    try:
        stats = SimulationRunner.get_agent_stats(simulation_id)
        
        return jsonify({
            "success": True,
            "data": {
                "agents_count": len(stats),
                "stats": stats
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des statistiques Agent : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Interface de requête à la base de données ==============

@simulation_bp.route('/<simulation_id>/posts', methods=['GET'])
def get_simulation_posts(simulation_id: str):
    """
    Récupère les publications de la simulation

    Paramètres de requête :
        platform: type de plateforme (twitter/reddit)
        limit: nombre de résultats retournés (50 par défaut)
        offset: décalage

    Retourne la liste des publications (lue depuis la base de données SQLite)
    """
    try:
        platform = request.args.get('platform', 'reddit')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        sim_dir = os.path.join(
            os.path.dirname(__file__),
            f'../../uploads/simulations/{simulation_id}'
        )
        
        db_file = f"{platform}_simulation.db"
        db_path = os.path.join(sim_dir, db_file)
        
        if not os.path.exists(db_path):
            return jsonify({
                "success": True,
                "data": {
                    "platform": platform,
                    "count": 0,
                    "posts": [],
                    "message": t('api.dbNotExist')
                }
            })
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM post 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            posts = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute("SELECT COUNT(*) FROM post")
            total = cursor.fetchone()[0]
            
        except sqlite3.OperationalError:
            posts = []
            total = 0
        
        conn.close()
        
        return jsonify({
            "success": True,
            "data": {
                "platform": platform,
                "total": total,
                "count": len(posts),
                "posts": posts
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des publications : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/<simulation_id>/comments', methods=['GET'])
def get_simulation_comments(simulation_id: str):
    """
    Récupère les commentaires de la simulation (Reddit uniquement)

    Paramètres de requête :
        post_id: filtre par ID de publication (optionnel)
        limit: nombre de résultats retournés
        offset: décalage
    """
    try:
        post_id = request.args.get('post_id')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        sim_dir = os.path.join(
            os.path.dirname(__file__),
            f'../../uploads/simulations/{simulation_id}'
        )
        
        db_path = os.path.join(sim_dir, "reddit_simulation.db")
        
        if not os.path.exists(db_path):
            return jsonify({
                "success": True,
                "data": {
                    "count": 0,
                    "comments": []
                }
            })
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            if post_id:
                cursor.execute("""
                    SELECT * FROM comment 
                    WHERE post_id = ?
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """, (post_id, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM comment 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            comments = [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.OperationalError:
            comments = []
        
        conn.close()
        
        return jsonify({
            "success": True,
            "data": {
                "count": len(comments),
                "comments": comments
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des commentaires : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Interface Interview ==============

@simulation_bp.route('/interview', methods=['POST'])
def interview_agent():
    """
    Interview d'un seul Agent

    Remarque : cette fonctionnalité nécessite que l'environnement de simulation soit en cours d'exécution
    (après la fin de la boucle de simulation, il passe en mode d'attente de commande)

    Requête (JSON) :
        {
            "simulation_id": "sim_xxxx",       // obligatoire, ID de la simulation
            "agent_id": 0,                     // obligatoire, ID de l'Agent
            "prompt": "Que pensez-vous de cette situation ?",  // obligatoire, question d'interview
            "platform": "twitter",             // optionnel, plateforme spécifique (twitter/reddit)
                                               // si non précisé : simulation double plateforme, interview simultanée sur les deux
            "timeout": 60                      // optionnel, délai d'expiration (secondes), 60 par défaut
        }

    Réponse (platform non précisé, mode double plateforme) :
        {
            "success": true,
            "data": {
                "agent_id": 0,
                "prompt": "Que pensez-vous de cette situation ?",
                "result": {
                    "agent_id": 0,
                    "prompt": "...",
                    "platforms": {
                        "twitter": {"agent_id": 0, "response": "...", "platform": "twitter"},
                        "reddit": {"agent_id": 0, "response": "...", "platform": "reddit"}
                    }
                },
                "timestamp": "2025-12-08T10:00:01"
            }
        }

    Réponse (platform précisé) :
        {
            "success": true,
            "data": {
                "agent_id": 0,
                "prompt": "Que pensez-vous de cette situation ?",
                "result": {
                    "agent_id": 0,
                    "response": "Je pense que...",
                    "platform": "twitter",
                    "timestamp": "2025-12-08T10:00:00"
                },
                "timestamp": "2025-12-08T10:00:01"
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        agent_id = data.get('agent_id')
        prompt = data.get('prompt')
        platform = data.get('platform')  # optionnel : twitter/reddit/None
        timeout = data.get('timeout', 60)

        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        if agent_id is None:
            return jsonify({
                "success": False,
                "error": t('api.requireAgentId')
            }), 400

        if not prompt:
            return jsonify({
                "success": False,
                "error": t('api.requirePrompt')
            }), 400

        # Valider le paramètre platform
        if platform and platform not in ("twitter", "reddit"):
            return jsonify({
                "success": False,
                "error": t('api.invalidInterviewPlatform')
            }), 400

        # Vérifier l'état de l'environnement
        if not SimulationRunner.check_env_alive(simulation_id):
            return jsonify({
                "success": False,
                "error": t('api.envNotRunning')
            }), 400

        # Optimiser le prompt, ajouter un préfixe pour éviter que l'Agent n'appelle un outil
        optimized_prompt = optimize_interview_prompt(prompt)
        
        result = SimulationRunner.interview_agent(
            simulation_id=simulation_id,
            agent_id=agent_id,
            prompt=optimized_prompt,
            platform=platform,
            timeout=timeout
        )

        return jsonify({
            "success": result.get("success", False),
            "data": result
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
        
    except TimeoutError as e:
        return jsonify({
            "success": False,
            "error": t('api.interviewTimeout', error=str(e))
        }), 504
        
    except Exception as e:
        logger.error(f"Échec de l'Interview : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/interview/batch', methods=['POST'])
def interview_agents_batch():
    """
    Interview par lots de plusieurs Agents

    Remarque : cette fonctionnalité nécessite que l'environnement de simulation soit en cours d'exécution

    Requête (JSON) :
        {
            "simulation_id": "sim_xxxx",       // obligatoire, ID de la simulation
            "interviews": [                    // obligatoire, liste d'interviews
                {
                    "agent_id": 0,
                    "prompt": "Que pensez-vous de A ?",
                    "platform": "twitter"      // optionnel, plateforme d'interview spécifique à cet Agent
                },
                {
                    "agent_id": 1,
                    "prompt": "Que pensez-vous de B ?"  // si platform non précisé, la valeur par défaut est utilisée
                }
            ],
            "platform": "reddit",              // optionnel, plateforme par défaut (écrasée par le platform de chaque élément)
                                               // si non précisé : simulation double plateforme, interview simultanée des deux pour chaque Agent
            "timeout": 120                     // optionnel, délai d'expiration (secondes), 120 par défaut
        }

    Réponse :
        {
            "success": true,
            "data": {
                "interviews_count": 2,
                "result": {
                    "interviews_count": 4,
                    "results": {
                        "twitter_0": {"agent_id": 0, "response": "...", "platform": "twitter"},
                        "reddit_0": {"agent_id": 0, "response": "...", "platform": "reddit"},
                        "twitter_1": {"agent_id": 1, "response": "...", "platform": "twitter"},
                        "reddit_1": {"agent_id": 1, "response": "...", "platform": "reddit"}
                    }
                },
                "timestamp": "2025-12-08T10:00:01"
            }
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        interviews = data.get('interviews')
        platform = data.get('platform')  # optionnel : twitter/reddit/None
        timeout = data.get('timeout', 120)

        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        if not interviews or not isinstance(interviews, list):
            return jsonify({
                "success": False,
                "error": t('api.requireInterviews')
            }), 400

        # Valider le paramètre platform
        if platform and platform not in ("twitter", "reddit"):
            return jsonify({
                "success": False,
                "error": t('api.invalidInterviewPlatform')
            }), 400

        # Valider chaque élément d'interview
        for i, interview in enumerate(interviews):
            if 'agent_id' not in interview:
                return jsonify({
                    "success": False,
                    "error": t('api.interviewListMissingAgentId', index=i+1)
                }), 400
            if 'prompt' not in interview:
                return jsonify({
                    "success": False,
                    "error": t('api.interviewListMissingPrompt', index=i+1)
                }), 400
            # Valider le platform de chaque élément (si présent)
            item_platform = interview.get('platform')
            if item_platform and item_platform not in ("twitter", "reddit"):
                return jsonify({
                    "success": False,
                    "error": t('api.interviewListInvalidPlatform', index=i+1)
                }), 400

        # Vérifier l'état de l'environnement
        if not SimulationRunner.check_env_alive(simulation_id):
            return jsonify({
                "success": False,
                "error": t('api.envNotRunning')
            }), 400

        # Optimiser le prompt de chaque élément d'interview, ajouter un préfixe pour éviter que l'Agent n'appelle un outil
        optimized_interviews = []
        for interview in interviews:
            optimized_interview = interview.copy()
            optimized_interview['prompt'] = optimize_interview_prompt(interview.get('prompt', ''))
            optimized_interviews.append(optimized_interview)

        result = SimulationRunner.interview_agents_batch(
            simulation_id=simulation_id,
            interviews=optimized_interviews,
            platform=platform,
            timeout=timeout
        )

        return jsonify({
            "success": result.get("success", False),
            "data": result
        })

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    except TimeoutError as e:
        return jsonify({
            "success": False,
            "error": t('api.batchInterviewTimeout', error=str(e))
        }), 504

    except Exception as e:
        logger.error(f"Échec de l'Interview par lots : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/interview/all', methods=['POST'])
def interview_all_agents():
    """
    Interview global - interroge tous les Agents avec la même question

    Remarque : cette fonctionnalité nécessite que l'environnement de simulation soit en cours d'exécution

    Requête (JSON) :
        {
            "simulation_id": "sim_xxxx",            // obligatoire, ID de la simulation
            "prompt": "Quel est votre avis global sur cette situation ?",  // obligatoire, question d'interview (identique pour tous les Agents)
            "platform": "reddit",                   // optionnel, plateforme spécifique (twitter/reddit)
                                                    // si non précisé : simulation double plateforme, interview simultanée des deux pour chaque Agent
            "timeout": 180                          // optionnel, délai d'expiration (secondes), 180 par défaut
        }

    Réponse :
        {
            "success": true,
            "data": {
                "interviews_count": 50,
                "result": {
                    "interviews_count": 100,
                    "results": {
                        "twitter_0": {"agent_id": 0, "response": "...", "platform": "twitter"},
                        "reddit_0": {"agent_id": 0, "response": "...", "platform": "reddit"},
                        ...
                    }
                },
                "timestamp": "2025-12-08T10:00:01"
            }
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        prompt = data.get('prompt')
        platform = data.get('platform')  # optionnel : twitter/reddit/None
        timeout = data.get('timeout', 180)

        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        if not prompt:
            return jsonify({
                "success": False,
                "error": t('api.requirePrompt')
            }), 400

        # Valider le paramètre platform
        if platform and platform not in ("twitter", "reddit"):
            return jsonify({
                "success": False,
                "error": t('api.invalidInterviewPlatform')
            }), 400

        # Vérifier l'état de l'environnement
        if not SimulationRunner.check_env_alive(simulation_id):
            return jsonify({
                "success": False,
                "error": t('api.envNotRunning')
            }), 400

        # Optimiser le prompt, ajouter un préfixe pour éviter que l'Agent n'appelle un outil
        optimized_prompt = optimize_interview_prompt(prompt)

        result = SimulationRunner.interview_all_agents(
            simulation_id=simulation_id,
            prompt=optimized_prompt,
            platform=platform,
            timeout=timeout
        )

        return jsonify({
            "success": result.get("success", False),
            "data": result
        })

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    except TimeoutError as e:
        return jsonify({
            "success": False,
            "error": t('api.globalInterviewTimeout', error=str(e))
        }), 504

    except Exception as e:
        logger.error(f"Échec de l'Interview global : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/interview/history', methods=['POST'])
def get_interview_history():
    """
    Récupère l'historique des Interviews

    Lit tous les enregistrements d'Interview depuis la base de données de la simulation

    Requête (JSON) :
        {
            "simulation_id": "sim_xxxx",  // obligatoire, ID de la simulation
            "platform": "reddit",          // optionnel, type de plateforme (reddit/twitter)
                                           // si non précisé, retourne l'historique complet des deux plateformes
            "agent_id": 0,                 // optionnel, ne récupérer que l'historique d'interview de cet Agent
            "limit": 100                   // optionnel, nombre de résultats retournés, 100 par défaut
        }

    Réponse :
        {
            "success": true,
            "data": {
                "count": 10,
                "history": [
                    {
                        "agent_id": 0,
                        "response": "Je pense que...",
                        "prompt": "Que pensez-vous de cette situation ?",
                        "timestamp": "2025-12-08T10:00:00",
                        "platform": "reddit"
                    },
                    ...
                ]
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        platform = data.get('platform')  # si non précisé, retourne l'historique des deux plateformes
        agent_id = data.get('agent_id')
        limit = data.get('limit', 100)
        
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        history = SimulationRunner.get_interview_history(
            simulation_id=simulation_id,
            platform=platform,
            agent_id=agent_id,
            limit=limit
        )

        return jsonify({
            "success": True,
            "data": {
                "count": len(history),
                "history": history
            }
        })

    except Exception as e:
        logger.error(f"Échec de la récupération de l'historique des Interviews : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/env-status', methods=['POST'])
def get_env_status():
    """
    Récupère l'état de l'environnement de simulation

    Vérifie si l'environnement de simulation est actif (peut recevoir des commandes d'Interview)

    Requête (JSON) :
        {
            "simulation_id": "sim_xxxx"  // obligatoire, ID de la simulation
        }

    Réponse :
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "env_alive": true,
                "twitter_available": true,
                "reddit_available": true,
                "message": "L'environnement est en cours d'exécution, prêt à recevoir des commandes d'Interview"
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        env_alive = SimulationRunner.check_env_alive(simulation_id)

        # Récupérer des informations d'état plus détaillées
        env_status = SimulationRunner.get_env_status_detail(simulation_id)

        if env_alive:
            message = t('api.envRunning')
        else:
            message = t('api.envNotRunningShort')

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "env_alive": env_alive,
                "twitter_available": env_status.get("twitter_available", False),
                "reddit_available": env_status.get("reddit_available", False),
                "message": message
            }
        })

    except Exception as e:
        logger.error(f"Échec de la récupération de l'état de l'environnement : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@simulation_bp.route('/close-env', methods=['POST'])
def close_simulation_env():
    """
    Ferme l'environnement de simulation

    Envoie une commande de fermeture d'environnement à la simulation, pour qu'elle quitte proprement
    le mode d'attente de commande.

    Remarque : ceci diffère de l'interface /stop, qui termine le processus de force,
    alors que cette interface permet à la simulation de fermer l'environnement et de quitter proprement.

    Requête (JSON) :
        {
            "simulation_id": "sim_xxxx",  // obligatoire, ID de la simulation
            "timeout": 30                  // optionnel, délai d'expiration (secondes), 30 par défaut
        }

    Réponse :
        {
            "success": true,
            "data": {
                "message": "Commande de fermeture de l'environnement envoyée",
                "result": {...},
                "timestamp": "2025-12-08T10:00:01"
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        timeout = data.get('timeout', 30)
        
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400
        
        result = SimulationRunner.close_simulation_env(
            simulation_id=simulation_id,
            timeout=timeout
        )
        
        # Mettre à jour l'état de la simulation
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if state:
            state.status = SimulationStatus.COMPLETED
            manager._save_simulation_state(state)

        return jsonify({
            "success": result.get("success", False),
            "data": result
        })

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    except Exception as e:
        logger.error(f"Échec de la fermeture de l'environnement : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

