"""
Générateur intelligent de configuration de simulation
Utilise un LLM pour générer automatiquement des paramètres de simulation détaillés à partir du besoin
de simulation, du contenu du document et des informations du graphe.
Automatisation de bout en bout, aucun paramétrage manuel requis.

Stratégie de génération par étapes, pour éviter les échecs dus à une génération trop volumineuse en une fois :
1. Génération de la configuration temporelle
2. Génération de la configuration des événements
3. Génération par lots de la configuration des Agents
4. Génération de la configuration des plateformes
"""

import json
import math
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

from openai import OpenAI

from ..config import Config
from ..utils.logger import get_logger
from ..utils.locale import get_language_instruction, t
from .zep_entity_reader import EntityNode, ZepEntityReader

logger = get_logger('mirofish.simulation_config')

# Configuration des rythmes de vie (fuseau horaire de référence)
CHINA_TIMEZONE_CONFIG = {
    # Plage nocturne profonde (quasiment aucune activité)
    "dead_hours": [0, 1, 2, 3, 4, 5],
    # Plage matinale (réveil progressif)
    "morning_hours": [6, 7, 8],
    # Plage de travail
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    # Pic du soir (le plus actif)
    "peak_hours": [19, 20, 21, 22],
    # Plage nocturne (activité en baisse)
    "night_hours": [23],
    # Coefficients d'activité
    "activity_multipliers": {
        "dead": 0.05,      # Quasiment personne tôt le matin
        "morning": 0.4,    # Activité croissante le matin
        "work": 0.7,       # Activité moyenne en journée de travail
        "peak": 1.5,       # Pic du soir
        "night": 0.5       # Baisse en fin de soirée
    }
}


@dataclass
class AgentActivityConfig:
    """Configuration d'activité d'un Agent individuel"""
    agent_id: int
    entity_uuid: str
    entity_name: str
    entity_type: str

    # Configuration du niveau d'activité (0.0-1.0)
    activity_level: float = 0.5  # Activité globale

    # Fréquence de prise de parole (nombre attendu de publications par heure)
    posts_per_hour: float = 1.0
    comments_per_hour: float = 2.0

    # Plage d'heures actives (format 24h, 0-23)
    active_hours: List[int] = field(default_factory=lambda: list(range(8, 23)))

    # Vitesse de réponse (délai de réaction aux événements chauds, en minutes simulées)
    response_delay_min: int = 5
    response_delay_max: int = 60

    # Tendance émotionnelle (-1.0 à 1.0, négatif à positif)
    sentiment_bias: float = 0.0

    # Position (attitude envers un sujet donné)
    stance: str = "neutral"  # supportive, opposing, neutral, observer

    # Poids d'influence (détermine la probabilité que ses publications soient vues par d'autres Agents)
    influence_weight: float = 1.0


@dataclass
class TimeSimulationConfig:
    """Configuration temporelle de la simulation (basée sur des rythmes de vie réalistes)"""
    # Durée totale de la simulation (en heures simulées)
    total_simulation_hours: int = 72  # 72 heures (3 jours) par défaut

    # Temps représenté par round (minutes simulées) - 60 minutes (1 heure) par défaut, pour accélérer l'écoulement du temps
    minutes_per_round: int = 60

    # Plage du nombre d'Agents activés par heure
    agents_per_hour_min: int = 5
    agents_per_hour_max: int = 20

    # Plage de pic (19h-22h le soir, la période la plus active)
    peak_hours: List[int] = field(default_factory=lambda: [19, 20, 21, 22])
    peak_activity_multiplier: float = 1.5

    # Plage creuse (0h-5h du matin, quasiment aucune activité)
    off_peak_hours: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5])
    off_peak_activity_multiplier: float = 0.05  # Activité extrêmement faible tôt le matin

    # Plage matinale
    morning_hours: List[int] = field(default_factory=lambda: [6, 7, 8])
    morning_activity_multiplier: float = 0.4

    # Plage de travail
    work_hours: List[int] = field(default_factory=lambda: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18])
    work_activity_multiplier: float = 0.7


@dataclass
class EventConfig:
    """Configuration des événements"""
    # Événements initiaux (événements déclencheurs au début de la simulation)
    initial_posts: List[Dict[str, Any]] = field(default_factory=list)

    # Événements programmés (événements déclenchés à des moments précis)
    scheduled_events: List[Dict[str, Any]] = field(default_factory=list)

    # Mots-clés des sujets brûlants
    hot_topics: List[str] = field(default_factory=list)

    # Direction de l'opinion publique
    narrative_direction: str = ""


@dataclass
class PlatformConfig:
    """Configuration spécifique à la plateforme"""
    platform: str  # twitter or reddit

    # Poids de l'algorithme de recommandation
    recency_weight: float = 0.4  # Fraîcheur temporelle
    popularity_weight: float = 0.3  # Popularité
    relevance_weight: float = 0.3  # Pertinence

    # Seuil de propagation virale (nombre d'interactions déclenchant la diffusion)
    viral_threshold: int = 10

    # Intensité de l'effet de chambre d'écho (degré d'agrégation des opinions similaires)
    echo_chamber_strength: float = 0.5


@dataclass
class SimulationParameters:
    """Configuration complète des paramètres de simulation"""
    # Informations de base
    simulation_id: str
    project_id: str
    graph_id: str
    simulation_requirement: str

    # Configuration temporelle
    time_config: TimeSimulationConfig = field(default_factory=TimeSimulationConfig)

    # Liste des configurations d'Agents
    agent_configs: List[AgentActivityConfig] = field(default_factory=list)

    # Configuration des événements
    event_config: EventConfig = field(default_factory=EventConfig)

    # Configuration des plateformes
    twitter_config: Optional[PlatformConfig] = None
    reddit_config: Optional[PlatformConfig] = None

    # Configuration LLM
    llm_model: str = ""
    llm_base_url: str = ""

    # Métadonnées de génération
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_reasoning: str = ""  # Explication du raisonnement du LLM

    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        time_dict = asdict(self.time_config)
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "time_config": time_dict,
            "agent_configs": [asdict(a) for a in self.agent_configs],
            "event_config": asdict(self.event_config),
            "twitter_config": asdict(self.twitter_config) if self.twitter_config else None,
            "reddit_config": asdict(self.reddit_config) if self.reddit_config else None,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "generated_at": self.generated_at,
            "generation_reasoning": self.generation_reasoning,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Conversion en chaîne JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class SimulationConfigGenerator:
    """
    Générateur intelligent de configuration de simulation

    Utilise un LLM pour analyser le besoin de simulation, le contenu du document et les
    informations des entités du graphe, et génère automatiquement la configuration de
    paramètres de simulation la plus adaptée

    Stratégie de génération par étapes :
    1. Génération de la configuration temporelle et des événements (léger)
    2. Génération par lots de la configuration des Agents (10 à 20 par lot)
    3. Génération de la configuration des plateformes
    """

    # Nombre maximal de caractères du contexte
    MAX_CONTEXT_LENGTH = 50000
    # Nombre d'Agents générés par lot
    AGENTS_PER_BATCH = 15

    # Longueur de troncature du contexte pour chaque étape (nombre de caractères)
    TIME_CONFIG_CONTEXT_LENGTH = 10000   # Configuration temporelle
    EVENT_CONFIG_CONTEXT_LENGTH = 8000   # Configuration des événements
    ENTITY_SUMMARY_LENGTH = 300          # Résumé d'entité
    AGENT_SUMMARY_LENGTH = 300           # Résumé d'entité dans la configuration des Agents
    ENTITIES_PER_TYPE_DISPLAY = 20       # Nombre d'entités affichées par type

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model_name = model_name or Config.LLM_MODEL_NAME

        if not self.api_key:
            raise ValueError("LLM_API_KEY non configurée")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def generate_config(
        self,
        simulation_id: str,
        project_id: str,
        graph_id: str,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> SimulationParameters:
        """
        Génère intelligemment la configuration complète de la simulation (génération par étapes)

        Args:
            simulation_id: ID de la simulation
            project_id: ID du projet
            graph_id: ID du graphe
            simulation_requirement: Description du besoin de simulation
            document_text: Contenu du document original
            entities: Liste des entités filtrées
            enable_twitter: Indique si Twitter doit être activé
            enable_reddit: Indique si Reddit doit être activé
            progress_callback: Fonction de rappel de progression (current_step, total_steps, message)

        Returns:
            SimulationParameters : Paramètres complets de la simulation
        """
        logger.info(f"Début de la génération intelligente de la configuration de simulation : simulation_id={simulation_id}, nombre d'entités={len(entities)}")

        # Calcule le nombre total d'étapes
        num_batches = math.ceil(len(entities) / self.AGENTS_PER_BATCH)
        total_steps = 3 + num_batches  # Configuration temporelle + configuration des événements + N lots d'Agents + configuration des plateformes
        current_step = 0

        def report_progress(step: int, message: str):
            nonlocal current_step
            current_step = step
            if progress_callback:
                progress_callback(step, total_steps, message)
            logger.info(f"[{step}/{total_steps}] {message}")

        # 1. Construit les informations de contexte de base
        context = self._build_context(
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            entities=entities
        )

        reasoning_parts = []

        # ========== Étape 1 : génération de la configuration temporelle ==========
        report_progress(1, t('progress.generatingTimeConfig'))
        num_entities = len(entities)
        time_config_result = self._generate_time_config(context, num_entities)
        time_config = self._parse_time_config(time_config_result, num_entities)
        reasoning_parts.append(f"{t('progress.timeConfigLabel')}: {time_config_result.get('reasoning', t('common.success'))}")
        
        # ========== Étape 2 : génération de la configuration des événements ==========
        report_progress(2, t('progress.generatingEventConfig'))
        event_config_result = self._generate_event_config(context, simulation_requirement, entities)
        event_config = self._parse_event_config(event_config_result)
        reasoning_parts.append(f"{t('progress.eventConfigLabel')}: {event_config_result.get('reasoning', t('common.success'))}")

        # ========== Étapes 3 à N : génération par lots de la configuration des Agents ==========
        all_agent_configs = []
        for batch_idx in range(num_batches):
            start_idx = batch_idx * self.AGENTS_PER_BATCH
            end_idx = min(start_idx + self.AGENTS_PER_BATCH, len(entities))
            batch_entities = entities[start_idx:end_idx]
            
            report_progress(
                3 + batch_idx,
                t('progress.generatingAgentConfig', start=start_idx + 1, end=end_idx, total=len(entities))
            )
            
            batch_configs = self._generate_agent_configs_batch(
                context=context,
                entities=batch_entities,
                start_idx=start_idx,
                simulation_requirement=simulation_requirement
            )
            all_agent_configs.extend(batch_configs)
        
        reasoning_parts.append(t('progress.agentConfigResult', count=len(all_agent_configs)))

        # ========== Attribution des Agents publicateurs pour les posts initiaux ==========
        logger.info("Attribution des Agents publicateurs appropriés pour les posts initiaux...")
        event_config = self._assign_initial_post_agents(event_config, all_agent_configs)
        assigned_count = len([p for p in event_config.initial_posts if p.get("poster_agent_id") is not None])
        reasoning_parts.append(t('progress.postAssignResult', count=assigned_count))

        # ========== Étape finale : génération de la configuration des plateformes ==========
        report_progress(total_steps, t('progress.generatingPlatformConfig'))
        twitter_config = None
        reddit_config = None
        
        if enable_twitter:
            twitter_config = PlatformConfig(
                platform="twitter",
                recency_weight=0.4,
                popularity_weight=0.3,
                relevance_weight=0.3,
                viral_threshold=10,
                echo_chamber_strength=0.5
            )
        
        if enable_reddit:
            reddit_config = PlatformConfig(
                platform="reddit",
                recency_weight=0.3,
                popularity_weight=0.4,
                relevance_weight=0.3,
                viral_threshold=15,
                echo_chamber_strength=0.6
            )
        
        # Construction des paramètres finaux
        params = SimulationParameters(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            time_config=time_config,
            agent_configs=all_agent_configs,
            event_config=event_config,
            twitter_config=twitter_config,
            reddit_config=reddit_config,
            llm_model=self.model_name,
            llm_base_url=self.base_url,
            generation_reasoning=" | ".join(reasoning_parts)
        )
        
        logger.info(f"Génération de la configuration de simulation terminée : {len(params.agent_configs)} configurations d'Agent")

        return params

    def _build_context(
        self,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode]
    ) -> str:
        """Construit le contexte pour le LLM, tronqué à la longueur maximale"""

        # Résumé des entités
        entity_summary = self._summarize_entities(entities)

        # Construction du contexte
        context_parts = [
            f"## Besoin de simulation\n{simulation_requirement}",
            f"\n## Informations sur les entités ({len(entities)})\n{entity_summary}",
        ]

        current_length = sum(len(p) for p in context_parts)
        remaining_length = self.MAX_CONTEXT_LENGTH - current_length - 500  # Marge de 500 caractères

        if remaining_length > 0 and document_text:
            doc_text = document_text[:remaining_length]
            if len(document_text) > remaining_length:
                doc_text += "\n...(document tronqué)"
            context_parts.append(f"\n## Contenu du document original\n{doc_text}")

        return "\n".join(context_parts)

    def _summarize_entities(self, entities: List[EntityNode]) -> str:
        """Génère un résumé des entités"""
        lines = []

        # Regroupement par type
        by_type: Dict[str, List[EntityNode]] = {}
        for e in entities:
            t = e.get_entity_type() or "Unknown"
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(e)

        for entity_type, type_entities in by_type.items():
            lines.append(f"\n### {entity_type} ({len(type_entities)})")
            # Utilise le nombre d'affichage et la longueur de résumé configurés
            display_count = self.ENTITIES_PER_TYPE_DISPLAY
            summary_len = self.ENTITY_SUMMARY_LENGTH
            for e in type_entities[:display_count]:
                summary_preview = (e.summary[:summary_len] + "...") if len(e.summary) > summary_len else e.summary
                lines.append(f"- {e.name}: {summary_preview}")
            if len(type_entities) > display_count:
                lines.append(f"  ... et {len(type_entities) - display_count} autres")

        return "\n".join(lines)

    def _call_llm_with_retry(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        """Appel LLM avec nouvelles tentatives, incluant la logique de réparation JSON"""
        import re

        max_attempts = 3
        last_error = None

        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1)  # Baisse de la température à chaque nouvelle tentative
                    # Pas de max_tokens défini, pour laisser le LLM s'exprimer librement
                )

                content = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason

                # Vérifie si la sortie a été tronquée
                if finish_reason == 'length':
                    logger.warning(f"Sortie LLM tronquée (tentative {attempt+1})")
                    content = self._fix_truncated_json(content)

                # Tentative de parsing du JSON
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.warning(f"Échec du parsing JSON (tentative {attempt+1}) : {str(e)[:80]}")

                    # Tentative de réparation du JSON
                    fixed = self._try_fix_config_json(content)
                    if fixed:
                        return fixed

                    last_error = e

            except Exception as e:
                logger.warning(f"Échec de l'appel LLM (tentative {attempt+1}) : {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(2 * (attempt + 1))

        raise last_error or Exception("Échec de l'appel LLM")

    def _fix_truncated_json(self, content: str) -> str:
        """Répare un JSON tronqué"""
        content = content.strip()

        # Calcul des accolades non fermées
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')

        # Vérifie s'il y a une chaîne non fermée
        if content and content[-1] not in '",}]':
            content += '"'

        # Fermeture des accolades/crochets
        content += ']' * open_brackets
        content += '}' * open_braces

        return content

    def _try_fix_config_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Tente de réparer un JSON de configuration"""
        import re

        # Réparation du cas tronqué
        content = self._fix_truncated_json(content)

        # Extraction de la partie JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()

            # Suppression des sauts de ligne dans les chaînes
            def fix_string(match):
                s = match.group(0)
                s = s.replace('\n', ' ').replace('\r', ' ')
                s = re.sub(r'\s+', ' ', s)
                return s

            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string, json_str)

            try:
                return json.loads(json_str)
            except:
                # Tentative de suppression de tous les caractères de contrôle
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                json_str = re.sub(r'\s+', ' ', json_str)
                try:
                    return json.loads(json_str)
                except:
                    pass

        return None
    
    def _generate_time_config(self, context: str, num_entities: int) -> Dict[str, Any]:
        """Génère la configuration temporelle"""
        # Utilise la longueur de troncature de contexte configurée
        context_truncated = context[:self.TIME_CONFIG_CONTEXT_LENGTH]

        # Calcule la valeur maximale autorisée (90% du nombre d'agents)
        max_agents_allowed = max(1, int(num_entities * 0.9))

        prompt = f"""À partir du besoin de simulation suivant, génère une configuration de simulation temporelle.

{context_truncated}

## Tâche
Génère un JSON de configuration temporelle.

### Principes de base (à titre indicatif uniquement, à ajuster librement selon l'événement et le groupe concerné) :
- Déduis, à partir du scénario de simulation, le fuseau horaire et les habitudes de vie du groupe d'utilisateurs cible ; l'exemple ci-dessous est donné pour le fuseau UTC+8 à titre de référence
- 0h-5h du matin : quasiment aucune activité (coefficient d'activité 0,05)
- 6h-8h du matin : activité progressivement croissante (coefficient d'activité 0,4)
- 9h-18h (heures de travail) : activité moyenne (coefficient d'activité 0,7)
- 19h-22h le soir : période de pic (coefficient d'activité 1,5)
- Après 23h : activité en baisse (coefficient d'activité 0,5)
- Tendance générale : faible activité tôt le matin, croissance en matinée, activité moyenne en journée de travail, pic en soirée
- **Important** : les valeurs d'exemple ci-dessus sont indicatives seulement, tu dois ajuster les plages horaires précises selon la nature de l'événement et les caractéristiques du groupe concerné
  - Exemple : pour un groupe d'étudiants, le pic peut être entre 21h et 23h ; les médias peuvent être actifs toute la journée ; les institutions officielles ne sont actives qu'aux heures de travail
  - Exemple : un sujet d'actualité soudain peut entraîner des discussions même tard dans la nuit, off_peak_hours peut alors être raccourci

### Format JSON à retourner (pas de markdown)

Exemple :
{{
    "total_simulation_hours": 72,
    "minutes_per_round": 60,
    "agents_per_hour_min": 5,
    "agents_per_hour_max": 50,
    "peak_hours": [19, 20, 21, 22],
    "off_peak_hours": [0, 1, 2, 3, 4, 5],
    "morning_hours": [6, 7, 8],
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    "reasoning": "explication de la configuration temporelle pour cet événement"
}}

Description des champs :
- total_simulation_hours (int) : durée totale de la simulation, 24-168 heures ; courte pour un événement soudain, longue pour un sujet durable
- minutes_per_round (int) : durée de chaque round, 30-120 minutes, 60 minutes recommandé
- agents_per_hour_min (int) : nombre minimal d'Agents activés par heure (plage : 1-{max_agents_allowed})
- agents_per_hour_max (int) : nombre maximal d'Agents activés par heure (plage : 1-{max_agents_allowed})
- peak_hours (tableau d'int) : plage de pic, à ajuster selon le groupe concerné par l'événement
- off_peak_hours (tableau d'int) : plage creuse, généralement tard dans la nuit / tôt le matin
- morning_hours (tableau d'int) : plage matinale
- work_hours (tableau d'int) : plage de travail
- reasoning (string) : brève explication du choix de cette configuration"""

        system_prompt = "Tu es un expert en simulation de réseaux sociaux. Retourne un JSON pur, la configuration temporelle doit correspondre aux habitudes de vie du groupe d'utilisateurs cible du scénario de simulation."
        system_prompt = f"{system_prompt}\n\n{get_language_instruction()}"

        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Échec de la génération de la configuration temporelle par le LLM : {e}, utilisation de la configuration par défaut")
            return self._get_default_time_config(num_entities)

    def _get_default_time_config(self, num_entities: int) -> Dict[str, Any]:
        """Récupère la configuration temporelle par défaut (rythme de vie de référence)"""
        return {
            "total_simulation_hours": 72,
            "minutes_per_round": 60,  # 1 heure par round, pour accélérer l'écoulement du temps
            "agents_per_hour_min": max(1, num_entities // 15),
            "agents_per_hour_max": max(5, num_entities // 5),
            "peak_hours": [19, 20, 21, 22],
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "morning_hours": [6, 7, 8],
            "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            "reasoning": "Utilisation de la configuration de rythme de vie par défaut (1 heure par round)"
        }

    def _parse_time_config(self, result: Dict[str, Any], num_entities: int) -> TimeSimulationConfig:
        """Analyse le résultat de la configuration temporelle, et vérifie que agents_per_hour ne dépasse pas le nombre total d'agents"""
        # Récupère les valeurs brutes
        agents_per_hour_min = result.get("agents_per_hour_min", max(1, num_entities // 15))
        agents_per_hour_max = result.get("agents_per_hour_max", max(5, num_entities // 5))

        # Vérification et correction : s'assurer que la valeur ne dépasse pas le nombre total d'agents
        if agents_per_hour_min > num_entities:
            logger.warning(f"agents_per_hour_min ({agents_per_hour_min}) dépasse le nombre total d'Agents ({num_entities}), correction appliquée")
            agents_per_hour_min = max(1, num_entities // 10)

        if agents_per_hour_max > num_entities:
            logger.warning(f"agents_per_hour_max ({agents_per_hour_max}) dépasse le nombre total d'Agents ({num_entities}), correction appliquée")
            agents_per_hour_max = max(agents_per_hour_min + 1, num_entities // 2)

        # S'assure que min < max
        if agents_per_hour_min >= agents_per_hour_max:
            agents_per_hour_min = max(1, agents_per_hour_max // 2)
            logger.warning(f"agents_per_hour_min >= max, corrigé à {agents_per_hour_min}")

        return TimeSimulationConfig(
            total_simulation_hours=result.get("total_simulation_hours", 72),
            minutes_per_round=result.get("minutes_per_round", 60),  # 1 heure par round par défaut
            agents_per_hour_min=agents_per_hour_min,
            agents_per_hour_max=agents_per_hour_max,
            peak_hours=result.get("peak_hours", [19, 20, 21, 22]),
            off_peak_hours=result.get("off_peak_hours", [0, 1, 2, 3, 4, 5]),
            off_peak_activity_multiplier=0.05,  # Quasiment personne tôt le matin
            morning_hours=result.get("morning_hours", [6, 7, 8]),
            morning_activity_multiplier=0.4,
            work_hours=result.get("work_hours", list(range(9, 19))),
            work_activity_multiplier=0.7,
            peak_activity_multiplier=1.5
        )
    
    def _generate_event_config(
        self, 
        context: str, 
        simulation_requirement: str,
        entities: List[EntityNode]
    ) -> Dict[str, Any]:
        """生成事件配置"""
        
        # 获取可用的实体类型列表，供 LLM 参考
        entity_types_available = list(set(
            e.get_entity_type() or "Unknown" for e in entities
        ))
        
        # 为每种类型列出代表性实体名称
        type_examples = {}
        for e in entities:
            etype = e.get_entity_type() or "Unknown"
            if etype not in type_examples:
                type_examples[etype] = []
            if len(type_examples[etype]) < 3:
                type_examples[etype].append(e.name)
        
        type_info = "\n".join([
            f"- {t}: {', '.join(examples)}" 
            for t, examples in type_examples.items()
        ])
        
        # 使用配置的上下文截断长度
        context_truncated = context[:self.EVENT_CONFIG_CONTEXT_LENGTH]
        
        prompt = f"""基于以下模拟需求，生成事件配置。

模拟需求: {simulation_requirement}

{context_truncated}

## 可用实体类型及示例
{type_info}

## 任务
请生成事件配置JSON：
- 提取热点话题关键词
- 描述舆论发展方向
- 设计初始帖子内容，**每个帖子必须指定 poster_type（发布者类型）**

**重要**: poster_type 必须从上面的"可用实体类型"中选择，这样初始帖子才能分配给合适的 Agent 发布。
例如：官方声明应由 Official/University 类型发布，新闻由 MediaOutlet 发布，学生观点由 Student 发布。

返回JSON格式（不要markdown）：
{{
    "hot_topics": ["关键词1", "关键词2", ...],
    "narrative_direction": "<舆论发展方向描述>",
    "initial_posts": [
        {{"content": "帖子内容", "poster_type": "实体类型（必须从可用类型中选择）"}},
        ...
    ],
    "reasoning": "<简要说明>"
}}"""

        system_prompt = "你是舆论分析专家。返回纯JSON格式。注意 poster_type 必须精确匹配可用实体类型。"
        system_prompt = f"{system_prompt}\n\n{get_language_instruction()}\nIMPORTANT: The 'poster_type' field value MUST be in English PascalCase exactly matching the available entity types. Only 'content', 'narrative_direction', 'hot_topics' and 'reasoning' fields should use the specified language."

        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"事件配置LLM生成失败: {e}, 使用默认配置")
            return {
                "hot_topics": [],
                "narrative_direction": "",
                "initial_posts": [],
                "reasoning": "使用默认配置"
            }
    
    def _parse_event_config(self, result: Dict[str, Any]) -> EventConfig:
        """解析事件配置结果"""
        return EventConfig(
            initial_posts=result.get("initial_posts", []),
            scheduled_events=[],
            hot_topics=result.get("hot_topics", []),
            narrative_direction=result.get("narrative_direction", "")
        )
    
    def _assign_initial_post_agents(
        self,
        event_config: EventConfig,
        agent_configs: List[AgentActivityConfig]
    ) -> EventConfig:
        """
        为初始帖子分配合适的发布者 Agent
        
        根据每个帖子的 poster_type 匹配最合适的 agent_id
        """
        if not event_config.initial_posts:
            return event_config
        
        # 按实体类型建立 agent 索引
        agents_by_type: Dict[str, List[AgentActivityConfig]] = {}
        for agent in agent_configs:
            etype = agent.entity_type.lower()
            if etype not in agents_by_type:
                agents_by_type[etype] = []
            agents_by_type[etype].append(agent)
        
        # 类型映射表（处理 LLM 可能输出的不同格式）
        type_aliases = {
            "official": ["official", "university", "governmentagency", "government"],
            "university": ["university", "official"],
            "mediaoutlet": ["mediaoutlet", "media"],
            "student": ["student", "person"],
            "professor": ["professor", "expert", "teacher"],
            "alumni": ["alumni", "person"],
            "organization": ["organization", "ngo", "company", "group"],
            "person": ["person", "student", "alumni"],
        }
        
        # 记录每种类型已使用的 agent 索引，避免重复使用同一个 agent
        used_indices: Dict[str, int] = {}
        
        updated_posts = []
        for post in event_config.initial_posts:
            poster_type = post.get("poster_type", "").lower()
            content = post.get("content", "")
            
            # 尝试找到匹配的 agent
            matched_agent_id = None
            
            # 1. 直接匹配
            if poster_type in agents_by_type:
                agents = agents_by_type[poster_type]
                idx = used_indices.get(poster_type, 0) % len(agents)
                matched_agent_id = agents[idx].agent_id
                used_indices[poster_type] = idx + 1
            else:
                # 2. 使用别名匹配
                for alias_key, aliases in type_aliases.items():
                    if poster_type in aliases or alias_key == poster_type:
                        for alias in aliases:
                            if alias in agents_by_type:
                                agents = agents_by_type[alias]
                                idx = used_indices.get(alias, 0) % len(agents)
                                matched_agent_id = agents[idx].agent_id
                                used_indices[alias] = idx + 1
                                break
                    if matched_agent_id is not None:
                        break
            
            # 3. 如果仍未找到，使用影响力最高的 agent
            if matched_agent_id is None:
                logger.warning(f"未找到类型 '{poster_type}' 的匹配 Agent，使用影响力最高的 Agent")
                if agent_configs:
                    # 按影响力排序，选择影响力最高的
                    sorted_agents = sorted(agent_configs, key=lambda a: a.influence_weight, reverse=True)
                    matched_agent_id = sorted_agents[0].agent_id
                else:
                    matched_agent_id = 0
            
            updated_posts.append({
                "content": content,
                "poster_type": post.get("poster_type", "Unknown"),
                "poster_agent_id": matched_agent_id
            })
            
            logger.info(f"初始帖子分配: poster_type='{poster_type}' -> agent_id={matched_agent_id}")
        
        event_config.initial_posts = updated_posts
        return event_config
    
    def _generate_agent_configs_batch(
        self,
        context: str,
        entities: List[EntityNode],
        start_idx: int,
        simulation_requirement: str
    ) -> List[AgentActivityConfig]:
        """分批生成Agent配置"""
        
        # 构建实体信息（使用配置的摘要长度）
        entity_list = []
        summary_len = self.AGENT_SUMMARY_LENGTH
        for i, e in enumerate(entities):
            entity_list.append({
                "agent_id": start_idx + i,
                "entity_name": e.name,
                "entity_type": e.get_entity_type() or "Unknown",
                "summary": e.summary[:summary_len] if e.summary else ""
            })
        
        prompt = f"""基于以下信息，为每个实体生成社交媒体活动配置。

模拟需求: {simulation_requirement}

## 实体列表
```json
{json.dumps(entity_list, ensure_ascii=False, indent=2)}
```

## 任务
为每个实体生成活动配置，注意：
- **时间符合目标用户群体作息**：以下为参考（东八区），请根据模拟场景调整
- **官方机构**（University/GovernmentAgency）：活跃度低(0.1-0.3)，工作时间(9-17)活动，响应慢(60-240分钟)，影响力高(2.5-3.0)
- **媒体**（MediaOutlet）：活跃度中(0.4-0.6)，全天活动(8-23)，响应快(5-30分钟)，影响力高(2.0-2.5)
- **个人**（Student/Person/Alumni）：活跃度高(0.6-0.9)，主要晚间活动(18-23)，响应快(1-15分钟)，影响力低(0.8-1.2)
- **公众人物/专家**：活跃度中(0.4-0.6)，影响力中高(1.5-2.0)

返回JSON格式（不要markdown）：
{{
    "agent_configs": [
        {{
            "agent_id": <必须与输入一致>,
            "activity_level": <0.0-1.0>,
            "posts_per_hour": <发帖频率>,
            "comments_per_hour": <评论频率>,
            "active_hours": [<活跃小时列表，考虑中国人作息>],
            "response_delay_min": <最小响应延迟分钟>,
            "response_delay_max": <最大响应延迟分钟>,
            "sentiment_bias": <-1.0到1.0>,
            "stance": "<supportive/opposing/neutral/observer>",
            "influence_weight": <影响力权重>
        }},
        ...
    ]
}}"""

        system_prompt = "你是社交媒体行为分析专家。返回纯JSON，配置需符合模拟场景中目标用户群体的作息习惯。"
        system_prompt = f"{system_prompt}\n\n{get_language_instruction()}\nIMPORTANT: The 'stance' field value MUST be one of the English strings: 'supportive', 'opposing', 'neutral', 'observer'. All JSON field names and numeric values must remain unchanged. Only natural language text fields should use the specified language."

        try:
            result = self._call_llm_with_retry(prompt, system_prompt)
            llm_configs = {cfg["agent_id"]: cfg for cfg in result.get("agent_configs", [])}
        except Exception as e:
            logger.warning(f"Agent配置批次LLM生成失败: {e}, 使用规则生成")
            llm_configs = {}
        
        # 构建AgentActivityConfig对象
        configs = []
        for i, entity in enumerate(entities):
            agent_id = start_idx + i
            cfg = llm_configs.get(agent_id, {})
            
            # 如果LLM没有生成，使用规则生成
            if not cfg:
                cfg = self._generate_agent_config_by_rule(entity)
            
            config = AgentActivityConfig(
                agent_id=agent_id,
                entity_uuid=entity.uuid,
                entity_name=entity.name,
                entity_type=entity.get_entity_type() or "Unknown",
                activity_level=cfg.get("activity_level", 0.5),
                posts_per_hour=cfg.get("posts_per_hour", 0.5),
                comments_per_hour=cfg.get("comments_per_hour", 1.0),
                active_hours=cfg.get("active_hours", list(range(9, 23))),
                response_delay_min=cfg.get("response_delay_min", 5),
                response_delay_max=cfg.get("response_delay_max", 60),
                sentiment_bias=cfg.get("sentiment_bias", 0.0),
                stance=cfg.get("stance", "neutral"),
                influence_weight=cfg.get("influence_weight", 1.0)
            )
            configs.append(config)
        
        return configs
    
    def _generate_agent_config_by_rule(self, entity: EntityNode) -> Dict[str, Any]:
        """基于规则生成单个Agent配置（中国人作息）"""
        entity_type = (entity.get_entity_type() or "Unknown").lower()
        
        if entity_type in ["university", "governmentagency", "ngo"]:
            # 官方机构：工作时间活动，低频率，高影响力
            return {
                "activity_level": 0.2,
                "posts_per_hour": 0.1,
                "comments_per_hour": 0.05,
                "active_hours": list(range(9, 18)),  # 9:00-17:59
                "response_delay_min": 60,
                "response_delay_max": 240,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 3.0
            }
        elif entity_type in ["mediaoutlet"]:
            # 媒体：全天活动，中等频率，高影响力
            return {
                "activity_level": 0.5,
                "posts_per_hour": 0.8,
                "comments_per_hour": 0.3,
                "active_hours": list(range(7, 24)),  # 7:00-23:59
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "observer",
                "influence_weight": 2.5
            }
        elif entity_type in ["professor", "expert", "official"]:
            # 专家/教授：工作+晚间活动，中等频率
            return {
                "activity_level": 0.4,
                "posts_per_hour": 0.3,
                "comments_per_hour": 0.5,
                "active_hours": list(range(8, 22)),  # 8:00-21:59
                "response_delay_min": 15,
                "response_delay_max": 90,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 2.0
            }
        elif entity_type in ["student"]:
            # 学生：晚间为主，高频率
            return {
                "activity_level": 0.8,
                "posts_per_hour": 0.6,
                "comments_per_hour": 1.5,
                "active_hours": [8, 9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],  # 上午+晚间
                "response_delay_min": 1,
                "response_delay_max": 15,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 0.8
            }
        elif entity_type in ["alumni"]:
            # 校友：晚间为主
            return {
                "activity_level": 0.6,
                "posts_per_hour": 0.4,
                "comments_per_hour": 0.8,
                "active_hours": [12, 13, 19, 20, 21, 22, 23],  # 午休+晚间
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            }
        else:
            # 普通人：晚间高峰
            return {
                "activity_level": 0.7,
                "posts_per_hour": 0.5,
                "comments_per_hour": 1.2,
                "active_hours": [9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],  # 白天+晚间
                "response_delay_min": 2,
                "response_delay_max": 20,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            }
    

