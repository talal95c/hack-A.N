"""
Service Report Agent
Génération de rapports de simulation en utilisant LangChain + Zep avec un modèle ReACT

Fonctionnalités :
1. Générer un rapport à partir des besoins de simulation et des informations du graphe Zep
2. Planifier d'abord la structure du sommaire, puis générer section par section
3. Chaque section utilise un modèle ReACT à plusieurs tours de réflexion et d'auto-évaluation
4. Prend en charge le dialogue avec l'utilisateur, avec appel autonome des outils de recherche pendant la conversation
"""

import os
import json
import time
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..utils.locale import get_language_instruction, t
from .zep_tools import (
    ZepToolsService, 
    SearchResult, 
    InsightForgeResult, 
    PanoramaResult,
    InterviewResult
)

logger = get_logger('mirofish.report_agent')


class ReportLogger:
    """
    Enregistreur de journal détaillé du Report Agent

    Génère un fichier agent_log.jsonl dans le dossier du rapport, enregistrant chaque action détaillée.
    Chaque ligne est un objet JSON complet contenant l'horodatage, le type d'action, le contenu détaillé, etc.
    """

    def __init__(self, report_id: str):
        """
        Initialise l'enregistreur de journal

        Args:
            report_id: ID du rapport, utilisé pour déterminer le chemin du fichier de journal
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'agent_log.jsonl'
        )
        self.start_time = datetime.now()
        self._ensure_log_file()

    def _ensure_log_file(self):
        """S'assure que le répertoire du fichier de journal existe"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)

    def _get_elapsed_time(self) -> float:
        """Récupère le temps écoulé depuis le début (en secondes)"""
        return (datetime.now() - self.start_time).total_seconds()

    def log(
        self,
        action: str,
        stage: str,
        details: Dict[str, Any],
        section_title: str = None,
        section_index: int = None
    ):
        """
        Enregistre une entrée de journal

        Args:
            action: type d'action, ex. 'start', 'tool_call', 'llm_response', 'section_complete', etc.
            stage: étape actuelle, ex. 'planning', 'generating', 'completed'
            details: dictionnaire de détails, non tronqué
            section_title: titre de la section actuelle (optionnel)
            section_index: index de la section actuelle (optionnel)
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(self._get_elapsed_time(), 2),
            "report_id": self.report_id,
            "action": action,
            "stage": stage,
            "section_title": section_title,
            "section_index": section_index,
            "details": details
        }
        
        # Écrit en ajout dans le fichier JSONL
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    def log_start(self, simulation_id: str, graph_id: str, simulation_requirement: str):
        """Enregistre le début de la génération du rapport"""
        self.log(
            action="report_start",
            stage="pending",
            details={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "simulation_requirement": simulation_requirement,
                "message": t('report.taskStarted')
            }
        )
    
    def log_planning_start(self):
        """Enregistre le début de la planification du sommaire"""
        self.log(
            action="planning_start",
            stage="planning",
            details={"message": t('report.planningStart')}
        )

    def log_planning_context(self, context: Dict[str, Any]):
        """Enregistre les informations de contexte récupérées lors de la planification"""
        self.log(
            action="planning_context",
            stage="planning",
            details={
                "message": t('report.fetchSimContext'),
                "context": context
            }
        )

    def log_planning_complete(self, outline_dict: Dict[str, Any]):
        """Enregistre la fin de la planification du sommaire"""
        self.log(
            action="planning_complete",
            stage="planning",
            details={
                "message": t('report.planningComplete'),
                "outline": outline_dict
            }
        )

    def log_section_start(self, section_title: str, section_index: int):
        """Enregistre le début de la génération d'une section"""
        self.log(
            action="section_start",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={"message": t('report.sectionStart', title=section_title)}
        )
    
    def log_react_thought(self, section_title: str, section_index: int, iteration: int, thought: str):
        """Enregistre le processus de réflexion ReACT"""
        self.log(
            action="react_thought",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "thought": thought,
                "message": t('report.reactThought', iteration=iteration)
            }
        )
    
    def log_tool_call(
        self, 
        section_title: str, 
        section_index: int,
        tool_name: str, 
        parameters: Dict[str, Any],
        iteration: int
    ):
        """Enregistre un appel d'outil"""
        self.log(
            action="tool_call",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "parameters": parameters,
                "message": t('report.toolCall', toolName=tool_name)
            }
        )
    
    def log_tool_result(
        self,
        section_title: str,
        section_index: int,
        tool_name: str,
        result: str,
        iteration: int
    ):
        """Enregistre le résultat d'un appel d'outil (contenu complet, non tronqué)"""
        self.log(
            action="tool_result",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "result": result,  # résultat complet, non tronqué
                "result_length": len(result),
                "message": t('report.toolResult', toolName=tool_name)
            }
        )
    
    def log_llm_response(
        self,
        section_title: str,
        section_index: int,
        response: str,
        iteration: int,
        has_tool_calls: bool,
        has_final_answer: bool
    ):
        """Enregistre la réponse du LLM (contenu complet, non tronqué)"""
        self.log(
            action="llm_response",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "response": response,  # réponse complète, non tronquée
                "response_length": len(response),
                "has_tool_calls": has_tool_calls,
                "has_final_answer": has_final_answer,
                "message": t('report.llmResponse', hasToolCalls=has_tool_calls, hasFinalAnswer=has_final_answer)
            }
        )
    
    def log_section_content(
        self,
        section_title: str,
        section_index: int,
        content: str,
        tool_calls_count: int
    ):
        """Enregistre la fin de la génération du contenu d'une section (n'indique que le contenu, pas la fin complète de la section)"""
        self.log(
            action="section_content",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": content,  # contenu complet, non tronqué
                "content_length": len(content),
                "tool_calls_count": tool_calls_count,
                "message": t('report.sectionContentDone', title=section_title)
            }
        )
    
    def log_section_full_complete(
        self,
        section_title: str,
        section_index: int,
        full_content: str
    ):
        """
        Enregistre la fin de la génération d'une section

        Le frontend doit écouter ce journal pour déterminer si une section est réellement terminée et récupérer le contenu complet
        """
        self.log(
            action="section_complete",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": full_content,
                "content_length": len(full_content),
                "message": t('report.sectionComplete', title=section_title)
            }
        )
    
    def log_report_complete(self, total_sections: int, total_time_seconds: float):
        """Enregistre la fin de la génération du rapport"""
        self.log(
            action="report_complete",
            stage="completed",
            details={
                "total_sections": total_sections,
                "total_time_seconds": round(total_time_seconds, 2),
                "message": t('report.reportComplete')
            }
        )
    
    def log_error(self, error_message: str, stage: str, section_title: str = None):
        """Enregistre une erreur"""
        self.log(
            action="error",
            stage=stage,
            section_title=section_title,
            section_index=None,
            details={
                "error": error_message,
                "message": t('report.errorOccurred', error=error_message)
            }
        )


class ReportConsoleLogger:
    """
    Enregistreur de journal console du Report Agent

    Écrit les journaux de style console (INFO, WARNING, etc.) dans le fichier console_log.txt
    situé dans le dossier du rapport. Ces journaux diffèrent de agent_log.jsonl : il s'agit d'une
    sortie console au format texte brut.
    """

    def __init__(self, report_id: str):
        """
        Initialise l'enregistreur de journal console

        Args:
            report_id: ID du rapport, utilisé pour déterminer le chemin du fichier de journal
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'console_log.txt'
        )
        self._ensure_log_file()
        self._file_handler = None
        self._setup_file_handler()
    
    def _ensure_log_file(self):
        """S'assure que le répertoire du fichier de journal existe"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)

    def _setup_file_handler(self):
        """Configure le gestionnaire de fichier pour écrire aussi les journaux dans un fichier"""
        import logging

        # Création du gestionnaire de fichier
        self._file_handler = logging.FileHandler(
            self.log_file_path,
            mode='a',
            encoding='utf-8'
        )
        self._file_handler.setLevel(logging.INFO)

        # Utilise le même format concis que la console
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        self._file_handler.setFormatter(formatter)

        # Ajout aux loggers liés à report_agent
        loggers_to_attach = [
            'mirofish.report_agent',
            'mirofish.zep_tools',
        ]

        for logger_name in loggers_to_attach:
            target_logger = logging.getLogger(logger_name)
            # Évite les ajouts en double
            if self._file_handler not in target_logger.handlers:
                target_logger.addHandler(self._file_handler)

    def close(self):
        """Ferme le gestionnaire de fichier et le retire du logger"""
        import logging

        if self._file_handler:
            loggers_to_detach = [
                'mirofish.report_agent',
                'mirofish.zep_tools',
            ]

            for logger_name in loggers_to_detach:
                target_logger = logging.getLogger(logger_name)
                if self._file_handler in target_logger.handlers:
                    target_logger.removeHandler(self._file_handler)

            self._file_handler.close()
            self._file_handler = None

    def __del__(self):
        """S'assure de fermer le gestionnaire de fichier lors de la destruction"""
        self.close()


class ReportStatus(str, Enum):
    """Statut du rapport"""
    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportSection:
    """Section de rapport"""
    title: str
    content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content
        }

    def to_markdown(self, level: int = 2) -> str:
        """Convertit au format Markdown"""
        md = f"{'#' * level} {self.title}\n\n"
        if self.content:
            md += f"{self.content}\n\n"
        return md


@dataclass
class ReportOutline:
    """Sommaire du rapport"""
    title: str
    summary: str
    sections: List[ReportSection]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "sections": [s.to_dict() for s in self.sections]
        }

    def to_markdown(self) -> str:
        """Convertit au format Markdown"""
        md = f"# {self.title}\n\n"
        md += f"> {self.summary}\n\n"
        for section in self.sections:
            md += section.to_markdown()
        return md


@dataclass
class Report:
    """Rapport complet"""
    report_id: str
    simulation_id: str
    graph_id: str
    simulation_requirement: str
    status: ReportStatus
    outline: Optional[ReportOutline] = None
    markdown_content: str = ""
    created_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "status": self.status.value,
            "outline": self.outline.to_dict() if self.outline else None,
            "markdown_content": self.markdown_content,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error
        }


# ═══════════════════════════════════════════════════════════════
# Constantes de templates de prompt
# ═══════════════════════════════════════════════════════════════

# ── Descriptions des outils ──

TOOL_DESC_INSIGHT_FORGE = """\
[RECHERCHE D'INSIGHTS APPROFONDIE - outil de recherche puissant]
C'est notre fonction de recherche la plus puissante, conçue pour l'analyse approfondie. Elle va :
1. Décomposer automatiquement votre question en plusieurs sous-questions
2. Rechercher les informations dans le graphe de simulation selon plusieurs dimensions
3. Combiner les résultats de recherche sémantique, d'analyse d'entités et de traçage de chaînes de relations
4. Retourner le contenu de recherche le plus complet et le plus approfondi

[CAS D'USAGE]
- Besoin d'analyser un sujet en profondeur
- Besoin de comprendre plusieurs aspects d'un événement
- Besoin d'obtenir une matière riche pour étayer une section du rapport

[CONTENU RETOURNÉ]
- Extraits de faits pertinents (citables directement)
- Insights sur les entités clés
- Analyse des chaînes de relations"""

TOOL_DESC_PANORAMA_SEARCH = """\
[RECHERCHE PANORAMIQUE - vue d'ensemble complète]
Cet outil permet d'obtenir une vue d'ensemble complète des résultats de simulation, particulièrement utile pour comprendre l'évolution d'un événement. Il va :
1. Récupérer tous les nœuds et relations pertinents
2. Distinguer les faits actuellement valides des faits historiques/obsolètes
3. Vous aider à comprendre comment l'opinion évolue

[CAS D'USAGE]
- Besoin de comprendre le déroulement complet d'un événement
- Besoin de comparer les évolutions de l'opinion entre différentes phases
- Besoin d'obtenir des informations complètes sur les entités et relations

[CONTENU RETOURNÉ]
- Faits actuellement valides (derniers résultats de simulation)
- Faits historiques/obsolètes (trace de l'évolution)
- Toutes les entités concernées"""

TOOL_DESC_QUICK_SEARCH = """\
[RECHERCHE SIMPLE - recherche rapide]
Outil de recherche léger et rapide, adapté aux requêtes d'information simples et directes.

[CAS D'USAGE]
- Besoin de trouver rapidement une information précise
- Besoin de vérifier un fait
- Recherche d'information simple

[CONTENU RETOURNÉ]
- Liste des faits les plus pertinents par rapport à la requête"""

TOOL_DESC_INTERVIEW_AGENTS = """\
[INTERVIEW APPROFONDIE - véritable interview d'agents (double plateforme)]
Appelle l'API d'interview de l'environnement de simulation OASIS pour interviewer réellement les agents de simulation en cours d'exécution !
Ce n'est pas une simulation par LLM, mais un véritable appel à l'interface d'interview pour obtenir les réponses brutes des agents simulés.
Par défaut, interviewe simultanément sur les plateformes Twitter et Reddit pour obtenir des points de vue plus complets.

Déroulement fonctionnel :
1. Lit automatiquement le fichier des personas pour connaître tous les agents simulés
2. Sélectionne intelligemment les agents les plus pertinents pour le sujet de l'interview (ex. étudiants, médias, officiels, etc.)
3. Génère automatiquement les questions d'interview
4. Appelle l'interface /api/simulation/interview/batch pour réaliser une véritable interview sur les deux plateformes
5. Combine tous les résultats d'interview pour fournir une analyse multi-perspective

[CAS D'USAGE]
- Besoin de comprendre le point de vue sur un événement selon différents rôles (Qu'en pensent les étudiants ? Les médias ? Que disent les officiels ?)
- Besoin de recueillir des opinions et positions de plusieurs parties
- Besoin d'obtenir les réponses réelles des agents simulés (provenant de l'environnement de simulation OASIS)
- Besoin de rendre le rapport plus vivant, en incluant un « compte-rendu d'interview »

[CONTENU RETOURNÉ]
- Informations d'identité des agents interviewés
- Réponses de chaque agent sur les plateformes Twitter et Reddit
- Citations clés (citables directement)
- Résumé de l'interview et comparaison des points de vue

[IMPORTANT] L'environnement de simulation OASIS doit être en cours d'exécution pour utiliser cette fonctionnalité !"""

# ── Prompt de planification du sommaire ──

PLAN_SYSTEM_PROMPT = """\
Tu es l'expert rédacteur du « rapport de prédiction d'impact législatif » de MiroPolis — un rapport
d'analyse exploratoire destiné aux décideurs (députés et leurs assistants) (CLAUDE.md §4.4). Tu disposes
d'une « vue divine » sur le monde simulé : les groupes parlementaires (jamais des députés nommés
individuellement) et les archétypes de profils citoyens (pondérés à partir des données INSEE) qui
débattent, proposent des amendements et réagissent dans la simulation.

[CONCEPT CENTRAL]
Nous avons construit un monde simulé du processus législatif et y avons injecté le texte de loi à
évaluer. Le résultat de l'évolution du monde simulé est une « prédiction exploratoire », pas un résultat
certain — il faut toujours employer une formulation prudente (« estimation », « probable »), jamais
présenter cela comme un futur certain.

[STRUCTURE FIXE DU RAPPORT — exactement 5 sections, dans cet ordre]
1. Synthèse pour décideurs : les points clés essentiels sur une page
2. Cartographie des parties prenantes : les groupes parlementaires et archétypes de profils citoyens concernés
3. Réactions et positions observées : réactions concrètes des différentes parties dans la simulation
4. Points de blocage / risques
5. Recommandations concrètes

Note : ce rapport est une synthèse rétrospective (recap) de la simulation déjà effectuée. La prédiction
prospective de trajectoire est gérée par un « Scenario Agent » indépendant (document séparé) ; ce rapport
ne comprend pas de section sur la trajectoire tendancielle/attendue.

[POSITIONNEMENT DU RAPPORT]
- Rapport de prédiction exploratoire : la formulation doit toujours refléter l'incertitude
- Ne jamais mentionner un député nommé individuellement — uniquement la tendance globale du groupe
- Ne jamais présenter les chiffres estimés par l'IA comme des résultats économétriques certains

Merci de produire un sommaire de rapport au format JSON, contenant exactement 5 sections, selon le format suivant :
{
    "title": "Titre du rapport",
    "summary": "Résumé du rapport (une phrase résumant la principale conclusion prédictive)",
    "sections": [
        {
            "title": "Titre de la section",
            "description": "Description du contenu de la section"
        }
    ]
}

Attention : le tableau sections doit contenir exactement 5 éléments, dans l'ordre fixe indiqué ci-dessus !"""

PLAN_USER_PROMPT_TEMPLATE = """\
[PARAMÉTRAGE DU SCÉNARIO PRÉDICTIF]
La variable injectée dans le monde simulé (besoin de simulation) : {simulation_requirement}

[ÉCHELLE DU MONDE SIMULÉ]
- Nombre d'entités participant à la simulation : {total_nodes}
- Nombre de relations générées entre les entités : {total_edges}
- Répartition des types d'entités : {entity_types}
- Nombre d'agents actifs : {total_entities}

[ÉCHANTILLON DE FAITS FUTURS PRÉDITS PAR LA SIMULATION]
{related_facts_json}

Merci d'examiner cette préfiguration du futur avec une « vue divine » :
1. Dans les conditions que nous avons définies, quel état futur se dessine-t-il ?
2. Comment les différents groupes de population (agents) réagissent-ils et agissent-ils ?
3. Quelles tendances futures notables cette simulation révèle-t-elle ?

En fonction des résultats de la prédiction, remplis la structure fixe à 5 sections de MiroPolis (synthèse
pour décideurs / cartographie des parties prenantes / réactions et positions observées / points de
blocage-risques / recommandations concrètes).

[RAPPEL] Nombre de sections du rapport : exactement 5, dans l'ordre fixe, contenu concis et centré sur les
principales conclusions prédictives."""

# ── Prompt de génération des sections ──

SECTION_SYSTEM_PROMPT_TEMPLATE = """\
Tu es un expert rédacteur de « rapport de prédiction du futur », en train de rédiger une section du rapport.

Titre du rapport : {report_title}
Résumé du rapport : {report_summary}
Scénario prédictif (besoin de simulation) : {simulation_requirement}

Section à rédiger actuellement : {section_title}

═══════════════════════════════════════════════════════════════
[CONCEPT CENTRAL]
═══════════════════════════════════════════════════════════════

Le monde simulé est une préfiguration du futur. Nous avons injecté des conditions spécifiques
(besoin de simulation) dans le monde simulé ; le comportement et les interactions des agents dans
la simulation constituent une prédiction du comportement futur des populations.

Ta mission est de :
- Révéler ce qui se passe dans le futur, dans les conditions définies
- Prédire comment les différents groupes de population (agents) réagissent et agissent
- Découvrir les tendances, risques et opportunités futurs notables

Ne rédige pas une analyse de la situation actuelle du monde réel.
Concentre-toi sur « ce que sera le futur » — le résultat de la simulation EST le futur prédit.

═══════════════════════════════════════════════════════════════
[RÈGLES LES PLUS IMPORTANTES - À RESPECTER IMPÉRATIVEMENT]
═══════════════════════════════════════════════════════════════

1. [Tu DOIS appeler des outils pour observer le monde simulé]
   - Tu observes une préfiguration du futur avec une « vue divine »
   - Tout le contenu doit provenir des événements et des propos/actions des agents dans le monde simulé
   - Il est interdit d'utiliser tes propres connaissances pour rédiger le contenu du rapport
   - Chaque section doit appeler au moins 3 outils (5 maximum) pour observer le monde simulé, qui représente le futur

2. [Tu DOIS citer les propos et actions originaux des agents]
   - Les propos et actions des agents constituent une prédiction du comportement futur des populations
   - Utilise un format de citation dans le rapport pour présenter ces prédictions, par exemple :
     > "Tel groupe de population déclarerait : contenu original..."
   - Ces citations sont la preuve centrale de la prédiction de simulation

3. [Cohérence linguistique - le contenu cité doit être traduit dans la langue du rapport]
   - Le contenu retourné par les outils peut contenir des formulations dans une langue différente de celle du rapport
   - Le rapport doit être rédigé entièrement dans la langue spécifiée par l'utilisateur
   - Lorsque tu cites un contenu retourné par un outil dans une autre langue, tu dois le traduire dans la langue du rapport avant de l'insérer
   - Lors de la traduction, conserve le sens original et assure-toi que la formulation reste naturelle et fluide
   - Cette règle s'applique à la fois au corps du texte et au contenu des blocs de citation (format >)

4. [Restitution fidèle des résultats de la prédiction]
   - Le contenu du rapport doit refléter les résultats de simulation représentant le futur dans le monde simulé
   - N'ajoute pas d'informations absentes de la simulation
   - Si les informations sont insuffisantes sur un aspect, indique-le honnêtement

═══════════════════════════════════════════════════════════════
[RÈGLES DE FORMATAGE - EXTRÊMEMENT IMPORTANT !]
═══════════════════════════════════════════════════════════════

[Une section = unité de contenu minimale]
- Chaque section est l'unité de découpage minimale du rapport
- Interdiction d'utiliser un quelconque titre Markdown dans la section (#, ##, ###, ####, etc.)
- Interdiction d'ajouter un titre principal de section au début du contenu
- Le titre de la section est ajouté automatiquement par le système, tu dois seulement rédiger le corps du texte
- Utilise **le gras**, la séparation en paragraphes, les citations et les listes pour organiser le contenu, mais sans titres

[Exemple correct]
```
Cette section analyse la dynamique de propagation de l'opinion sur l'événement. Une analyse approfondie
des données de simulation révèle que...

**Phase de déclenchement initial**

En tant que premier lieu de l'opinion publique, la plateforme a assuré la fonction centrale de
diffusion initiale de l'information :

> "La plateforme a généré 68 % du volume de publication initial..."

**Phase d'amplification émotionnelle**

La plateforme vidéo a encore amplifié l'impact de l'événement :

- Fort impact visuel
- Forte résonance émotionnelle
```

[Exemple incorrect]
```
## Résumé exécutif          ← Incorrect ! N'ajoute aucun titre
### I. Phase initiale       ← Incorrect ! N'utilise pas ### pour les sous-sections
#### 1.1 Analyse détaillée  ← Incorrect ! N'utilise pas #### pour subdiviser

Cette section analyse...
```

═══════════════════════════════════════════════════════════════
[OUTILS DE RECHERCHE DISPONIBLES] (3 à 5 appels par section)
═══════════════════════════════════════════════════════════════

{tools_description}

[CONSEIL D'UTILISATION DES OUTILS - mélange différents outils, n'utilise pas qu'un seul type]
- insight_forge : analyse d'insights approfondie, décompose automatiquement la question et recherche faits et relations selon plusieurs dimensions
- panorama_search : recherche panoramique grand angle, pour comprendre la vue d'ensemble, la chronologie et l'évolution d'un événement
- quick_search : vérification rapide d'un point d'information précis
- interview_agents : interview des agents simulés, pour obtenir des points de vue à la première personne et des réactions réelles selon différents rôles

═══════════════════════════════════════════════════════════════
[DÉROULEMENT DU TRAVAIL]
═══════════════════════════════════════════════════════════════

À chaque réponse, tu ne peux faire que l'une des deux actions suivantes (jamais les deux à la fois) :

Option A - Appeler un outil :
Exprime ta réflexion, puis appelle un outil selon le format suivant :
<tool_call>
{{"name": "nom_de_l_outil", "parameters": {{"nom_du_parametre": "valeur_du_parametre"}}}}
</tool_call>
Le système exécutera l'outil et te renverra le résultat. Tu n'as pas besoin, et tu ne dois pas, rédiger toi-même le résultat de l'outil.

Option B - Produire le contenu final :
Lorsque tu as obtenu suffisamment d'informations via les outils, commence par "Final Answer:" pour produire le contenu de la section.

Interdictions strictes :
- Interdiction d'inclure à la fois un appel d'outil et une Final Answer dans une même réponse
- Interdiction d'inventer toi-même le résultat d'un outil (Observation) ; tous les résultats d'outils sont injectés par le système
- Un seul appel d'outil maximum par réponse

═══════════════════════════════════════════════════════════════
[EXIGENCES SUR LE CONTENU DE LA SECTION]
═══════════════════════════════════════════════════════════════

1. Le contenu doit être basé sur les données de simulation obtenues via les outils
2. Cite abondamment le texte original pour illustrer les effets de la simulation
3. Utilise le format Markdown (mais sans titres) :
   - Utilise **le texte en gras** pour marquer les points importants (à la place des sous-titres)
   - Utilise des listes (- ou 1.2.3.) pour organiser les points
   - Utilise des lignes vides pour séparer les paragraphes
   - Interdiction d'utiliser #, ##, ###, #### ou toute autre syntaxe de titre
4. [Règles de formatage des citations - doivent former un paragraphe séparé]
   Les citations doivent former un paragraphe indépendant, avec une ligne vide avant et après, jamais mêlées au texte :

   Format correct :
   ```
   La réponse de l'établissement a été jugée manquant de contenu substantiel.

   > "Le mode de réponse de l'établissement semble rigide et lent face à un environnement de réseaux sociaux en évolution rapide."

   Cette évaluation reflète le mécontentement général du public.
   ```

   Format incorrect :
   ```
   La réponse de l'établissement a été jugée manquant de contenu substantiel.> "Le mode de réponse de l'établissement..." Cette évaluation reflète...
   ```
5. Maintiens la cohérence logique avec les autres sections
6. [Éviter les répétitions] Lis attentivement le contenu des sections déjà rédigées ci-dessous, ne répète pas les mêmes informations
7. [Rappel] N'ajoute aucun titre ! Utilise **le gras** à la place des titres de sous-section"""

SECTION_USER_PROMPT_TEMPLATE = """\
Contenu des sections déjà rédigées (lis attentivement pour éviter les répétitions) :
{previous_content}

═══════════════════════════════════════════════════════════════
[TÂCHE ACTUELLE] Rédiger la section : {section_title}
═══════════════════════════════════════════════════════════════

[RAPPELS IMPORTANTS]
1. Lis attentivement les sections déjà rédigées ci-dessus pour éviter de répéter le même contenu !
2. Tu dois d'abord appeler un outil pour obtenir des données de simulation avant de commencer
3. Mélange différents outils, n'utilise pas qu'un seul type
4. Le contenu du rapport doit provenir des résultats de recherche, n'utilise pas tes propres connaissances

[AVERTISSEMENT DE FORMAT - À RESPECTER IMPÉRATIVEMENT]
- N'écris aucun titre (#, ##, ###, #### sont tous interdits)
- N'écris pas "{section_title}" en début de texte
- Le titre de la section est ajouté automatiquement par le système
- Rédige directement le corps du texte, utilise **le gras** à la place des titres de sous-section

Pour commencer :
1. Réfléchis d'abord (Thought) aux informations nécessaires pour cette section
2. Puis appelle un outil (Action) pour obtenir des données de simulation
3. Une fois suffisamment d'informations recueillies, produis la Final Answer (texte pur, sans aucun titre)"""

# ── Templates de messages internes de la boucle ReACT ──

REACT_OBSERVATION_TEMPLATE = """\
Observation (résultat de la recherche) :

═══ Résultat de l'outil {tool_name} ═══
{result}

═══════════════════════════════════════════════════════════════
Outils appelés {tool_calls_count}/{max_tool_calls} fois (utilisés : {used_tools_str}){unused_hint}
- Si les informations sont suffisantes : commence par "Final Answer:" pour produire le contenu de la section (tu dois citer le texte original ci-dessus)
- Si davantage d'informations sont nécessaires : appelle un outil pour continuer la recherche
═══════════════════════════════════════════════════════════════"""

REACT_INSUFFICIENT_TOOLS_MSG = (
    "[ATTENTION] Tu n'as appelé les outils que {tool_calls_count} fois, alors qu'il en faut au moins {min_tool_calls}. "
    "Merci d'appeler à nouveau un outil pour obtenir plus de données de simulation avant de produire la Final Answer. {unused_hint}"
)

REACT_INSUFFICIENT_TOOLS_MSG_ALT = (
    "Actuellement, les outils n'ont été appelés que {tool_calls_count} fois, alors qu'il en faut au moins {min_tool_calls}. "
    "Merci d'appeler un outil pour obtenir des données de simulation. {unused_hint}"
)

REACT_TOOL_LIMIT_MSG = (
    "Le nombre maximal d'appels d'outils est atteint ({tool_calls_count}/{max_tool_calls}), tu ne peux plus appeler d'outil. "
    'Merci de produire immédiatement le contenu de la section en commençant par "Final Answer:", à partir des informations déjà obtenues.'
)

REACT_UNUSED_TOOLS_HINT = "\nTu n'as pas encore utilisé : {unused_list}, il est conseillé d'essayer différents outils pour obtenir des informations sous plusieurs angles"

REACT_FORCE_FINAL_MSG = "La limite d'appels d'outils est atteinte, merci de produire directement Final Answer: et de générer le contenu de la section."

# ── Prompt du chat ──

CHAT_SYSTEM_PROMPT_TEMPLATE = """\
Tu es un assistant de prédiction de simulation, concis et efficace.

[CONTEXTE]
Conditions de la prédiction : {simulation_requirement}

[RAPPORT D'ANALYSE DÉJÀ GÉNÉRÉ]
{report_content}

[RÈGLES]
1. Réponds en priorité à partir du contenu du rapport ci-dessus
2. Réponds directement à la question, évite les développements de réflexion trop longs
3. N'appelle un outil pour rechercher davantage de données que si le contenu du rapport est insuffisant pour répondre
4. La réponse doit être concise, claire et structurée

[OUTILS DISPONIBLES] (à utiliser uniquement si nécessaire, 1 à 2 appels maximum)
{tools_description}

[FORMAT D'APPEL D'OUTIL]
<tool_call>
{{"name": "nom_de_l_outil", "parameters": {{"nom_du_parametre": "valeur_du_parametre"}}}}
</tool_call>

[STYLE DE RÉPONSE]
- Concis et direct, évite les discours trop longs
- Utilise le format > pour citer le contenu clé
- Donne d'abord la conclusion, puis explique les raisons"""

CHAT_OBSERVATION_SUFFIX = "\n\nMerci de répondre à la question de façon concise."


# ═══════════════════════════════════════════════════════════════
# Classe principale ReportAgent
# ═══════════════════════════════════════════════════════════════


class ReportAgent:
    """
    Report Agent - Agent de génération de rapport de simulation

    Utilise le modèle ReACT (Reasoning + Acting) :
    1. Phase de planification : analyse les besoins de simulation, planifie la structure du sommaire du rapport
    2. Phase de génération : génère le contenu section par section, chaque section peut appeler l'outil plusieurs fois pour obtenir des informations
    3. Phase d'auto-évaluation : vérifie l'exhaustivité et l'exactitude du contenu
    """

    # Nombre maximal d'appels d'outils (par section)
    MAX_TOOL_CALLS_PER_SECTION = 5

    # Nombre maximal de tours d'auto-évaluation
    MAX_REFLECTION_ROUNDS = 3

    # Nombre maximal d'appels d'outils dans une conversation
    MAX_TOOL_CALLS_PER_CHAT = 2

    def __init__(
        self,
        graph_id: str,
        simulation_id: str,
        simulation_requirement: str,
        llm_client: Optional[LLMClient] = None,
        zep_tools: Optional[ZepToolsService] = None
    ):
        """
        Initialise le Report Agent

        Args:
            graph_id: ID du graphe
            simulation_id: ID de la simulation
            simulation_requirement: description des besoins de simulation
            llm_client: client LLM (optionnel)
            zep_tools: service d'outils Zep (optionnel)
        """
        self.graph_id = graph_id
        self.simulation_id = simulation_id
        self.simulation_requirement = simulation_requirement

        self.llm = llm_client or LLMClient()
        self.zep_tools = zep_tools or ZepToolsService()

        # Définition des outils
        self.tools = self._define_tools()

        # Enregistreur de journal (initialisé dans generate_report)
        self.report_logger: Optional[ReportLogger] = None
        # Enregistreur de journal console (initialisé dans generate_report)
        self.console_logger: Optional[ReportConsoleLogger] = None

        logger.info(t('report.agentInitDone', graphId=graph_id, simulationId=simulation_id))

    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """Définit les outils disponibles"""
        return {
            "insight_forge": {
                "name": "insight_forge",
                "description": TOOL_DESC_INSIGHT_FORGE,
                "parameters": {
                    "query": "la question ou le sujet que tu souhaites analyser en profondeur",
                    "report_context": "contexte de la section actuelle du rapport (optionnel, aide à générer des sous-questions plus précises)"
                }
            },
            "panorama_search": {
                "name": "panorama_search",
                "description": TOOL_DESC_PANORAMA_SEARCH,
                "parameters": {
                    "query": "requête de recherche, utilisée pour le tri par pertinence",
                    "include_expired": "inclure ou non le contenu périmé/historique (True par défaut)"
                }
            },
            "quick_search": {
                "name": "quick_search",
                "description": TOOL_DESC_QUICK_SEARCH,
                "parameters": {
                    "query": "chaîne de requête de recherche",
                    "limit": "nombre de résultats à retourner (optionnel, 10 par défaut)"
                }
            },
            "interview_agents": {
                "name": "interview_agents",
                "description": TOOL_DESC_INTERVIEW_AGENTS,
                "parameters": {
                    "interview_topic": "sujet ou besoin de l'interview (ex. : 'comprendre l'avis des étudiants sur l'incident de formaldéhyde dans les dortoirs')",
                    "max_agents": "nombre maximal d'agents à interviewer (optionnel, 5 par défaut, 10 au maximum)"
                }
            }
        }

    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], report_context: str = "") -> str:
        """
        Exécute un appel d'outil

        Args:
            tool_name: nom de l'outil
            parameters: paramètres de l'outil
            report_context: contexte du rapport (utilisé pour InsightForge)

        Returns:
            résultat de l'exécution de l'outil (format texte)
        """
        logger.info(t('report.executingTool', toolName=tool_name, params=parameters))

        try:
            if tool_name == "insight_forge":
                query = parameters.get("query", "")
                ctx = parameters.get("report_context", "") or report_context
                result = self.zep_tools.insight_forge(
                    graph_id=self.graph_id,
                    query=query,
                    simulation_requirement=self.simulation_requirement,
                    report_context=ctx
                )
                return result.to_text()

            elif tool_name == "panorama_search":
                # Recherche panoramique - obtenir la vue d'ensemble
                query = parameters.get("query", "")
                include_expired = parameters.get("include_expired", True)
                if isinstance(include_expired, str):
                    include_expired = include_expired.lower() in ['true', '1', 'yes']
                result = self.zep_tools.panorama_search(
                    graph_id=self.graph_id,
                    query=query,
                    include_expired=include_expired
                )
                return result.to_text()

            elif tool_name == "quick_search":
                # Recherche simple - récupération rapide
                query = parameters.get("query", "")
                limit = parameters.get("limit", 10)
                if isinstance(limit, str):
                    limit = int(limit)
                result = self.zep_tools.quick_search(
                    graph_id=self.graph_id,
                    query=query,
                    limit=limit
                )
                return result.to_text()
            
            elif tool_name == "interview_agents":
                # Interview approfondie - appelle la véritable API d'interview OASIS pour obtenir les réponses des agents simulés (double plateforme)
                interview_topic = parameters.get("interview_topic", parameters.get("query", ""))
                max_agents = parameters.get("max_agents", 5)
                if isinstance(max_agents, str):
                    max_agents = int(max_agents)
                max_agents = min(max_agents, 10)
                result = self.zep_tools.interview_agents(
                    simulation_id=self.simulation_id,
                    interview_requirement=interview_topic,
                    simulation_requirement=self.simulation_requirement,
                    max_agents=max_agents
                )
                return result.to_text()
            
            # ========== Anciens outils conservés pour compatibilité (redirection interne vers les nouveaux outils) ==========

            elif tool_name == "search_graph":
                # Redirection vers quick_search
                logger.info(t('report.redirectToQuickSearch'))
                return self._execute_tool("quick_search", parameters, report_context)
            
            elif tool_name == "get_graph_statistics":
                result = self.zep_tools.get_graph_statistics(self.graph_id)
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_entity_summary":
                entity_name = parameters.get("entity_name", "")
                result = self.zep_tools.get_entity_summary(
                    graph_id=self.graph_id,
                    entity_name=entity_name
                )
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_simulation_context":
                # Redirection vers insight_forge, qui est plus puissant
                logger.info(t('report.redirectToInsightForge'))
                query = parameters.get("query", self.simulation_requirement)
                return self._execute_tool("insight_forge", {"query": query}, report_context)
            
            elif tool_name == "get_entities_by_type":
                entity_type = parameters.get("entity_type", "")
                nodes = self.zep_tools.get_entities_by_type(
                    graph_id=self.graph_id,
                    entity_type=entity_type
                )
                result = [n.to_dict() for n in nodes]
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            else:
                return f"Outil inconnu : {tool_name}. Merci d'utiliser l'un des outils suivants : insight_forge, panorama_search, quick_search"

        except Exception as e:
            logger.error(t('report.toolExecFailed', toolName=tool_name, error=str(e)))
            return f"Échec de l'exécution de l'outil : {str(e)}"

    # Ensemble des noms d'outils valides, utilisé pour la validation lors de l'analyse de secours en JSON brut
    VALID_TOOL_NAMES = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        Analyse les appels d'outils dans la réponse du LLM

        Formats pris en charge (par ordre de priorité) :
        1. <tool_call>{"name": "tool_name", "parameters": {...}}</tool_call>
        2. JSON brut (la réponse entière ou une seule ligne est directement un JSON d'appel d'outil)
        """
        tool_calls = []

        # Format 1 : style XML (format standard)
        xml_pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        for match in re.finditer(xml_pattern, response, re.DOTALL):
            try:
                call_data = json.loads(match.group(1))
                tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        if tool_calls:
            return tool_calls

        # Format 2 : secours - le LLM produit directement un JSON brut (sans balise <tool_call>)
        # N'est tenté que si le format 1 n'a rien trouvé, pour éviter de faire correspondre par erreur un JSON présent dans le corps du texte
        stripped = response.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            try:
                call_data = json.loads(stripped)
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
                    return tool_calls
            except json.JSONDecodeError:
                pass

        # La réponse peut contenir du texte de réflexion + un JSON brut ; on tente d'extraire le dernier objet JSON
        json_pattern = r'(\{"(?:name|tool)"\s*:.*?\})\s*$'
        match = re.search(json_pattern, stripped, re.DOTALL)
        if match:
            try:
                call_data = json.loads(match.group(1))
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        return tool_calls

    def _is_valid_tool_call(self, data: dict) -> bool:
        """Vérifie si le JSON analysé constitue un appel d'outil valide"""
        # Prend en charge deux jeux de clés : {"name": ..., "parameters": ...} et {"tool": ..., "params": ...}
        tool_name = data.get("name") or data.get("tool")
        if tool_name and tool_name in self.VALID_TOOL_NAMES:
            # Uniformise les noms de clés en name / parameters
            if "tool" in data:
                data["name"] = data.pop("tool")
            if "params" in data and "parameters" not in data:
                data["parameters"] = data.pop("params")
            return True
        return False

    def _get_tools_description(self) -> str:
        """Génère le texte de description des outils"""
        desc_parts = ["Outils disponibles :"]
        for name, tool in self.tools.items():
            params_desc = ", ".join([f"{k}: {v}" for k, v in tool["parameters"].items()])
            desc_parts.append(f"- {name}: {tool['description']}")
            if params_desc:
                desc_parts.append(f"  Paramètres: {params_desc}")
        return "\n".join(desc_parts)

    def plan_outline(
        self,
        progress_callback: Optional[Callable] = None
    ) -> ReportOutline:
        """
        Planifie le sommaire du rapport

        Utilise le LLM pour analyser le besoin de simulation et planifier la structure du sommaire du rapport

        Args:
            progress_callback: fonction de rappel de progression

        Returns:
            ReportOutline: sommaire du rapport
        """
        logger.info(t('report.startPlanningOutline'))

        if progress_callback:
            progress_callback("planning", 0, t('progress.analyzingRequirements'))

        # Récupère d'abord le contexte de la simulation
        context = self.zep_tools.get_simulation_context(
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement
        )

        if progress_callback:
            progress_callback("planning", 30, t('progress.generatingOutline'))
        
        system_prompt = f"{PLAN_SYSTEM_PROMPT}\n\n{get_language_instruction()}"
        user_prompt = PLAN_USER_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            total_nodes=context.get('graph_statistics', {}).get('total_nodes', 0),
            total_edges=context.get('graph_statistics', {}).get('total_edges', 0),
            entity_types=list(context.get('graph_statistics', {}).get('entity_types', {}).keys()),
            total_entities=context.get('total_entities', 0),
            related_facts_json=json.dumps(context.get('related_facts', [])[:10], ensure_ascii=False, indent=2),
        )

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            if progress_callback:
                progress_callback("planning", 80, t('progress.parsingOutline'))

            # Analyse du sommaire
            sections = []
            for section_data in response.get("sections", []):
                sections.append(ReportSection(
                    title=section_data.get("title", ""),
                    content=""
                ))

            outline = ReportOutline(
                title=response.get("title", "Rapport d'analyse de simulation"),
                summary=response.get("summary", ""),
                sections=sections
            )

            if progress_callback:
                progress_callback("planning", 100, t('progress.outlinePlanComplete'))

            logger.info(t('report.outlinePlanDone', count=len(sections)))
            return outline

        except Exception as e:
            logger.error(t('report.outlinePlanFailed', error=str(e)))
            # Retourne un sommaire par défaut (3 sections, en secours)
            return ReportOutline(
                title="Rapport de prédiction du futur",
                summary="Analyse des tendances futures et des risques fondée sur la prédiction de simulation",
                sections=[
                    ReportSection(title="Scénario de prédiction et principales conclusions"),
                    ReportSection(title="Analyse prédictive du comportement des populations"),
                    ReportSection(title="Perspectives de tendances et signaux de risque")
                ]
            )

    def _generate_section_react(
        self,
        section: ReportSection,
        outline: ReportOutline,
        previous_sections: List[str],
        progress_callback: Optional[Callable] = None,
        section_index: int = 0
    ) -> str:
        """
        Génère le contenu d'une section en utilisant le modèle ReACT

        Boucle ReACT :
        1. Thought (réflexion) - analyse les informations nécessaires
        2. Action (action) - appelle un outil pour obtenir des informations
        3. Observation (observation) - analyse le résultat retourné par l'outil
        4. Répète jusqu'à ce que les informations soient suffisantes ou que le nombre maximal soit atteint
        5. Final Answer (réponse finale) - génère le contenu de la section

        Args:
            section: la section à générer
            outline: le sommaire complet
            previous_sections: contenu des sections précédentes (pour préserver la cohérence)
            progress_callback: rappel de progression
            section_index: index de la section (utilisé pour la journalisation)


        Returns:
            contenu de la section (format Markdown)
        """
        logger.info(t('report.reactGenerateSection', title=section.title))

        # Enregistre le journal de début de section
        if self.report_logger:
            self.report_logger.log_section_start(section.title, section_index)
        
        system_prompt = SECTION_SYSTEM_PROMPT_TEMPLATE.format(
            report_title=outline.title,
            report_summary=outline.summary,
            simulation_requirement=self.simulation_requirement,
            section_title=section.title,
            tools_description=self._get_tools_description(),
        )
        system_prompt = f"{system_prompt}\n\n{get_language_instruction()}"

        # Construction du prompt utilisateur - chaque section déjà terminée est transmise avec un maximum de 4000 caractères
        if previous_sections:
            previous_parts = []
            for sec in previous_sections:
                # Maximum 4000 caractères par section
                truncated = sec[:4000] + "..." if len(sec) > 4000 else sec
                previous_parts.append(truncated)
            previous_content = "\n\n---\n\n".join(previous_parts)
        else:
            previous_content = "(ceci est la première section)"


        user_prompt = SECTION_USER_PROMPT_TEMPLATE.format(
            previous_content=previous_content,
            section_title=section.title,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Boucle ReACT
        tool_calls_count = 0
        max_iterations = 5  # Nombre maximal de tours d'itération
        min_tool_calls = 3  # Nombre minimal d'appels d'outils
        conflict_retries = 0  # Nombre de conflits consécutifs où appel d'outil et Final Answer apparaissent ensemble
        used_tools = set()  # Enregistre les noms des outils déjà appelés
        all_tools = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

        # Contexte du rapport, utilisé pour la génération de sous-questions par InsightForge
        report_context = f"Titre de la section : {section.title}\nBesoin de simulation : {self.simulation_requirement}"
        
        for iteration in range(max_iterations):
            if progress_callback:
                progress_callback(
                    "generating", 
                    int((iteration / max_iterations) * 100),
                    t('progress.deepSearchAndWrite', current=tool_calls_count, max=self.MAX_TOOL_CALLS_PER_SECTION)
                )
            
            # Appel du LLM
            response = self.llm.chat(
                messages=messages,
                temperature=0.5,
                max_tokens=4096
            )

            # Vérifie si le retour du LLM est None (anomalie de l'API ou contenu vide)
            if response is None:
                logger.warning(t('report.sectionIterNone', title=section.title, iteration=iteration + 1))
                # S'il reste des itérations, ajoute un message et réessaie
                if iteration < max_iterations - 1:
                    messages.append({"role": "assistant", "content": "(réponse vide)"})
                    messages.append({"role": "user", "content": "Merci de continuer à générer le contenu."})
                    continue
                # La dernière itération retourne aussi None, on sort de la boucle pour la clôture forcée
                break

            logger.debug(f"Réponse LLM: {response[:200]}...")

            # Analyse une seule fois, réutilise le résultat
            tool_calls = self._parse_tool_calls(response)
            has_tool_calls = bool(tool_calls)
            has_final_answer = "Final Answer:" in response

            # ── Gestion des conflits : le LLM a produit à la fois un appel d'outil et une Final Answer ──
            if has_tool_calls and has_final_answer:
                conflict_retries += 1
                logger.warning(
                    t('report.sectionConflict', title=section.title, iteration=iteration+1, conflictCount=conflict_retries)
                )

                if conflict_retries <= 2:
                    # Les deux premières fois : on écarte cette réponse et on demande au LLM de répondre à nouveau
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            "[ERREUR DE FORMAT] Tu as inclus à la fois un appel d'outil et une Final Answer dans une même réponse, ce qui n'est pas autorisé.\n"
                            "À chaque réponse, tu ne peux faire que l'une des deux actions suivantes :\n"
                            "- Appeler un outil (produire un bloc <tool_call>, sans écrire de Final Answer)\n"
                            "- Produire le contenu final (commence par 'Final Answer:', sans inclure de <tool_call>)\n"
                            "Merci de répondre à nouveau en ne faisant qu'une seule de ces deux actions."
                        ),
                    })
                    continue
                else:
                    # Troisième fois : traitement dégradé, on tronque jusqu'au premier appel d'outil et on l'exécute de force
                    logger.warning(
                        t('report.sectionConflictDowngrade', title=section.title, conflictCount=conflict_retries)
                    )
                    first_tool_end = response.find('</tool_call>')
                    if first_tool_end != -1:
                        response = response[:first_tool_end + len('</tool_call>')]
                        tool_calls = self._parse_tool_calls(response)
                        has_tool_calls = bool(tool_calls)
                    has_final_answer = False
                    conflict_retries = 0

            # Enregistre le journal de la réponse LLM
            if self.report_logger:
                self.report_logger.log_llm_response(
                    section_title=section.title,
                    section_index=section_index,
                    response=response,
                    iteration=iteration + 1,
                    has_tool_calls=has_tool_calls,
                    has_final_answer=has_final_answer
                )

            # ── Cas 1 : le LLM a produit une Final Answer ──
            if has_final_answer:
                # Nombre d'appels d'outils insuffisant, on refuse et on demande de continuer à appeler des outils
                if tool_calls_count < min_tool_calls:
                    messages.append({"role": "assistant", "content": response})
                    unused_tools = all_tools - used_tools
                    unused_hint = f"(ces outils n'ont pas encore été utilisés, il est conseillé de les essayer : {', '.join(unused_tools)})" if unused_tools else ""
                    messages.append({
                        "role": "user",
                        "content": REACT_INSUFFICIENT_TOOLS_MSG.format(
                            tool_calls_count=tool_calls_count,
                            min_tool_calls=min_tool_calls,
                            unused_hint=unused_hint,
                        ),
                    })
                    continue

                # Fin normale
                final_answer = response.split("Final Answer:")[-1].strip()
                logger.info(t('report.sectionGenDone', title=section.title, count=tool_calls_count))

                if self.report_logger:
                    self.report_logger.log_section_content(
                        section_title=section.title,
                        section_index=section_index,
                        content=final_answer,
                        tool_calls_count=tool_calls_count
                    )
                return final_answer

            # ── Cas 2 : le LLM tente d'appeler un outil ──
            if has_tool_calls:
                # Le quota d'outils est épuisé → informer explicitement et demander de produire une Final Answer
                if tool_calls_count >= self.MAX_TOOL_CALLS_PER_SECTION:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": REACT_TOOL_LIMIT_MSG.format(
                            tool_calls_count=tool_calls_count,
                            max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        ),
                    })
                    continue

                # N'exécute que le premier appel d'outil
                call = tool_calls[0]
                if len(tool_calls) > 1:
                    logger.info(t('report.multiToolOnlyFirst', total=len(tool_calls), toolName=call['name']))

                if self.report_logger:
                    self.report_logger.log_tool_call(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        parameters=call.get("parameters", {}),
                        iteration=iteration + 1
                    )

                result = self._execute_tool(
                    call["name"],
                    call.get("parameters", {}),
                    report_context=report_context
                )

                if self.report_logger:
                    self.report_logger.log_tool_result(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        result=result,
                        iteration=iteration + 1
                    )

                tool_calls_count += 1
                used_tools.add(call['name'])

                # Construit l'indication des outils non utilisés
                unused_tools = all_tools - used_tools
                unused_hint = ""
                if unused_tools and tool_calls_count < self.MAX_TOOL_CALLS_PER_SECTION:
                    unused_hint = REACT_UNUSED_TOOLS_HINT.format(unused_list=", ".join(unused_tools))

                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": REACT_OBSERVATION_TEMPLATE.format(
                        tool_name=call["name"],
                        result=result,
                        tool_calls_count=tool_calls_count,
                        max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        used_tools_str=", ".join(used_tools),
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # ── Cas 3 : ni appel d'outil, ni Final Answer ──
            messages.append({"role": "assistant", "content": response})

            if tool_calls_count < min_tool_calls:
                # Nombre d'appels d'outils insuffisant, recommande les outils non utilisés
                unused_tools = all_tools - used_tools
                unused_hint = f"(ces outils n'ont pas encore été utilisés, il est conseillé de les essayer : {', '.join(unused_tools)})" if unused_tools else ""

                messages.append({
                    "role": "user",
                    "content": REACT_INSUFFICIENT_TOOLS_MSG_ALT.format(
                        tool_calls_count=tool_calls_count,
                        min_tool_calls=min_tool_calls,
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # Le nombre d'appels d'outils est suffisant, le LLM a produit du contenu mais sans le préfixe "Final Answer:"
            # On utilise directement ce contenu comme réponse finale, sans itération supplémentaire
            logger.info(t('report.sectionNoPrefix', title=section.title, count=tool_calls_count))
            final_answer = response.strip()

            if self.report_logger:
                self.report_logger.log_section_content(
                    section_title=section.title,
                    section_index=section_index,
                    content=final_answer,
                    tool_calls_count=tool_calls_count
                )
            return final_answer

        # Nombre maximal d'itérations atteint, génération forcée du contenu
        logger.warning(t('report.sectionMaxIter', title=section.title))
        messages.append({"role": "user", "content": REACT_FORCE_FINAL_MSG})

        response = self.llm.chat(
            messages=messages,
            temperature=0.5,
            max_tokens=4096
        )

        # Vérifie si le retour du LLM est None lors de la clôture forcée
        if response is None:
            logger.error(t('report.sectionForceFailed', title=section.title))
            final_answer = t('report.sectionGenFailedContent')
        elif "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[-1].strip()
        else:
            final_answer = response

        # Enregistre le journal de fin de génération du contenu de la section
        if self.report_logger:
            self.report_logger.log_section_content(
                section_title=section.title,
                section_index=section_index,
                content=final_answer,
                tool_calls_count=tool_calls_count
            )
        
        return final_answer
    
    def generate_report(
        self, 
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        report_id: Optional[str] = None
    ) -> Report:
        """
        Génère le rapport complet (sortie en temps réel, section par section)

        Chaque section est sauvegardée dans le dossier dès qu'elle est terminée, sans attendre la fin du rapport entier.
        Structure des fichiers :
        reports/{report_id}/
            meta.json       - métadonnées du rapport
            outline.json    - sommaire du rapport
            progress.json   - progression de la génération
            section_01.md   - section 1
            section_02.md   - section 2
            ...
            full_report.md  - rapport complet

        Args:
            progress_callback: fonction de rappel de progression (stage, progress, message)
            report_id: ID du rapport (optionnel, généré automatiquement si non fourni)

        Returns:
            Report: rapport complet
        """
        import uuid

        # Génère automatiquement le report_id s'il n'est pas fourni
        if not report_id:
            report_id = f"report_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()

        report = Report(
            report_id=report_id,
            simulation_id=self.simulation_id,
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement,
            status=ReportStatus.PENDING,
            created_at=datetime.now().isoformat()
        )

        # Liste des titres de sections déjà terminées (pour le suivi de progression)
        completed_section_titles = []

        try:
            # Initialisation : création du dossier du rapport et sauvegarde de l'état initial
            ReportManager._ensure_report_folder(report_id)

            # Initialisation de l'enregistreur de journal (journal structuré agent_log.jsonl)
            self.report_logger = ReportLogger(report_id)
            self.report_logger.log_start(
                simulation_id=self.simulation_id,
                graph_id=self.graph_id,
                simulation_requirement=self.simulation_requirement
            )

            # Initialisation de l'enregistreur de journal console (console_log.txt)
            self.console_logger = ReportConsoleLogger(report_id)

            ReportManager.update_progress(
                report_id, "pending", 0, t('progress.initReport'),
                completed_sections=[]
            )
            ReportManager.save_report(report)

            # Étape 1 : planification du sommaire
            report.status = ReportStatus.PLANNING
            ReportManager.update_progress(
                report_id, "planning", 5, t('progress.startPlanningOutline'),
                completed_sections=[]
            )

            # Enregistre le journal de début de planification
            self.report_logger.log_planning_start()

            if progress_callback:
                progress_callback("planning", 0, t('progress.startPlanningOutline'))

            outline = self.plan_outline(
                progress_callback=lambda stage, prog, msg:
                    progress_callback(stage, prog // 5, msg) if progress_callback else None
            )
            report.outline = outline

            # Enregistre le journal de fin de planification
            self.report_logger.log_planning_complete(outline.to_dict())

            # Sauvegarde le sommaire dans un fichier
            ReportManager.save_outline(report_id, outline)
            ReportManager.update_progress(
                report_id, "planning", 15, t('progress.outlineDone', count=len(outline.sections)),
                completed_sections=[]
            )
            ReportManager.save_report(report)

            logger.info(t('report.outlineSavedToFile', reportId=report_id))

            # Étape 2 : génération section par section (sauvegarde par section)
            report.status = ReportStatus.GENERATING

            total_sections = len(outline.sections)
            generated_sections = []  # Sauvegarde du contenu pour le contexte

            for i, section in enumerate(outline.sections):
                section_num = i + 1
                base_progress = 20 + int((i / total_sections) * 70)

                # Mise à jour de la progression
                ReportManager.update_progress(
                    report_id, "generating", base_progress,
                    t('progress.generatingSection', title=section.title, current=section_num, total=total_sections),
                    current_section=section.title,
                    completed_sections=completed_section_titles
                )

                if progress_callback:
                    progress_callback(
                        "generating",
                        base_progress,
                        t('progress.generatingSection', title=section.title, current=section_num, total=total_sections)
                    )

                # Génère le contenu principal de la section
                section_content = self._generate_section_react(
                    section=section,
                    outline=outline,
                    previous_sections=generated_sections,
                    progress_callback=lambda stage, prog, msg:
                        progress_callback(
                            stage, 
                            base_progress + int(prog * 0.7 / total_sections),
                            msg
                        ) if progress_callback else None,
                    section_index=section_num
                )
                
                section.content = section_content
                generated_sections.append(f"## {section.title}\n\n{section_content}")

                # Sauvegarde la section
                ReportManager.save_section(report_id, section_num, section)
                completed_section_titles.append(section.title)

                # Enregistre le journal de fin de section
                full_section_content = f"## {section.title}\n\n{section_content}"

                if self.report_logger:
                    self.report_logger.log_section_full_complete(
                        section_title=section.title,
                        section_index=section_num,
                        full_content=full_section_content.strip()
                    )

                logger.info(t('report.sectionSaved', reportId=report_id, sectionNum=f"{section_num:02d}"))

                # Mise à jour de la progression
                ReportManager.update_progress(
                    report_id, "generating", 
                    base_progress + int(70 / total_sections),
                    t('progress.sectionDone', title=section.title),
                    current_section=None,
                    completed_sections=completed_section_titles
                )
            
            # Étape 3 : assemblage du rapport complet
            if progress_callback:
                progress_callback("generating", 95, t('progress.assemblingReport'))

            ReportManager.update_progress(
                report_id, "generating", 95, t('progress.assemblingReport'),
                completed_sections=completed_section_titles
            )

            # Utilise ReportManager pour assembler le rapport complet
            report.markdown_content = ReportManager.assemble_full_report(report_id, outline)
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now().isoformat()

            # Calcule le temps total écoulé
            total_time_seconds = (datetime.now() - start_time).total_seconds()

            # Enregistre le journal de fin de rapport
            if self.report_logger:
                self.report_logger.log_report_complete(
                    total_sections=total_sections,
                    total_time_seconds=total_time_seconds
                )

            # Enregistre le rapport final
            ReportManager.save_report(report)
            ReportManager.update_progress(
                report_id, "completed", 100, t('progress.reportComplete'),
                completed_sections=completed_section_titles
            )

            if progress_callback:
                progress_callback("completed", 100, t('progress.reportComplete'))

            logger.info(t('report.reportGenDone', reportId=report_id))

            # Ferme l'enregistreur de journal console
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None

            return report

        except Exception as e:
            logger.error(t('report.reportGenFailed', error=str(e)))
            report.status = ReportStatus.FAILED
            report.error = str(e)

            # Enregistre le journal d'erreur
            if self.report_logger:
                self.report_logger.log_error(str(e), "failed")

            # Enregistre l'état d'échec
            try:
                ReportManager.save_report(report)
                ReportManager.update_progress(
                    report_id, "failed", -1, t('progress.reportFailed', error=str(e)),
                    completed_sections=completed_section_titles
                )
            except Exception:
                pass  # Ignore les erreurs d'enregistrement de l'échec

            # Ferme l'enregistreur de journal console
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None

            return report

    def chat(
        self,
        message: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Dialogue avec le Report Agent

        Pendant la conversation, l'agent peut appeler de façon autonome des outils de recherche pour répondre aux questions

        Args:
            message: message de l'utilisateur
            chat_history: historique de la conversation

        Returns:
            {
                "response": "réponse de l'agent",
                "tool_calls": [liste des outils appelés],
                "sources": [sources d'information]
            }
        """
        logger.info(t('report.agentChat', message=message[:50]))
        
        chat_history = chat_history or []

        # Récupère le contenu du rapport déjà généré
        report_content = ""
        try:
            report = ReportManager.get_report_by_simulation(self.simulation_id)
            if report and report.markdown_content:
                # Limite la longueur du rapport pour éviter un contexte trop long
                report_content = report.markdown_content[:15000]
                if len(report.markdown_content) > 15000:
                    report_content += "\n\n... [contenu du rapport tronqué] ..."
        except Exception as e:
            logger.warning(t('report.fetchReportFailed', error=e))

        system_prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            report_content=report_content if report_content else "(aucun rapport pour l'instant)",
            tools_description=self._get_tools_description(),
        )
        system_prompt = f"{system_prompt}\n\n{get_language_instruction()}"

        # Construction des messages
        messages = [{"role": "system", "content": system_prompt}]

        # Ajout de l'historique de conversation
        for h in chat_history[-10:]:  # Limite la longueur de l'historique
            messages.append(h)

        # Ajout du message utilisateur
        messages.append({
            "role": "user",
            "content": message
        })

        # Boucle ReACT (version simplifiée)
        tool_calls_made = []
        max_iterations = 2  # Nombre d'itérations réduit

        for iteration in range(max_iterations):
            response = self.llm.chat(
                messages=messages,
                temperature=0.5
            )

            # Analyse des appels d'outils
            tool_calls = self._parse_tool_calls(response)

            if not tool_calls:
                # Aucun appel d'outil, on retourne directement la réponse
                clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', response, flags=re.DOTALL)
                clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)

                return {
                    "response": clean_response.strip(),
                    "tool_calls": tool_calls_made,
                    "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
                }
            
            # Exécute les appels d'outils (nombre limité)
            tool_results = []
            for call in tool_calls[:1]:  # Maximum 1 appel d'outil exécuté par tour
                if len(tool_calls_made) >= self.MAX_TOOL_CALLS_PER_CHAT:
                    break
                result = self._execute_tool(call["name"], call.get("parameters", {}))
                tool_results.append({
                    "tool": call["name"],
                    "result": result[:1500]  # Limite la longueur du résultat
                })
                tool_calls_made.append(call)

            # Ajoute les résultats aux messages
            messages.append({"role": "assistant", "content": response})
            observation = "\n".join([f"[Résultat de {r['tool']}]\n{r['result']}" for r in tool_results])
            messages.append({
                "role": "user",
                "content": observation + CHAT_OBSERVATION_SUFFIX
            })

        # Nombre maximal d'itérations atteint, récupère la réponse finale
        final_response = self.llm.chat(
            messages=messages,
            temperature=0.5
        )

        # Nettoie la réponse
        clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', final_response, flags=re.DOTALL)
        clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)

        return {
            "response": clean_response.strip(),
            "tool_calls": tool_calls_made,
            "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
        }


class ReportManager:
    """
    Gestionnaire de rapport

    Responsable du stockage persistant et de la récupération des rapports

    Structure des fichiers (sortie par section) :
    reports/
      {report_id}/
        meta.json          - métadonnées et statut du rapport
        outline.json       - sommaire du rapport
        progress.json      - progression de la génération
        section_01.md      - section 1
        section_02.md      - section 2
        ...
        full_report.md     - rapport complet
    """

    # Répertoire de stockage des rapports
    REPORTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'reports')

    @classmethod
    def _ensure_reports_dir(cls):
        """S'assure que le répertoire racine des rapports existe"""
        os.makedirs(cls.REPORTS_DIR, exist_ok=True)

    @classmethod
    def _get_report_folder(cls, report_id: str) -> str:
        """Récupère le chemin du dossier du rapport"""
        return os.path.join(cls.REPORTS_DIR, report_id)

    @classmethod
    def _ensure_report_folder(cls, report_id: str) -> str:
        """S'assure que le dossier du rapport existe et retourne son chemin"""
        folder = cls._get_report_folder(report_id)
        os.makedirs(folder, exist_ok=True)
        return folder

    @classmethod
    def _get_report_path(cls, report_id: str) -> str:
        """Récupère le chemin du fichier de métadonnées du rapport"""
        return os.path.join(cls._get_report_folder(report_id), "meta.json")
    
    @classmethod
    def _get_report_markdown_path(cls, report_id: str) -> str:
        """Récupère le chemin du fichier Markdown du rapport complet"""
        return os.path.join(cls._get_report_folder(report_id), "full_report.md")

    @classmethod
    def _get_outline_path(cls, report_id: str) -> str:
        """Récupère le chemin du fichier de sommaire"""
        return os.path.join(cls._get_report_folder(report_id), "outline.json")

    @classmethod
    def _get_progress_path(cls, report_id: str) -> str:
        """Récupère le chemin du fichier de progression"""
        return os.path.join(cls._get_report_folder(report_id), "progress.json")

    @classmethod
    def _get_section_path(cls, report_id: str, section_index: int) -> str:
        """Récupère le chemin du fichier Markdown de la section"""
        return os.path.join(cls._get_report_folder(report_id), f"section_{section_index:02d}.md")

    @classmethod
    def _get_agent_log_path(cls, report_id: str) -> str:
        """Récupère le chemin du fichier de journal de l'agent"""
        return os.path.join(cls._get_report_folder(report_id), "agent_log.jsonl")

    @classmethod
    def _get_console_log_path(cls, report_id: str) -> str:
        """Récupère le chemin du fichier de journal console"""
        return os.path.join(cls._get_report_folder(report_id), "console_log.txt")

    @classmethod
    def get_console_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        Récupère le contenu du journal console

        Il s'agit du journal de sortie console (INFO, WARNING, etc.) produit pendant la génération du rapport,
        distinct du journal structuré agent_log.jsonl.

        Args:
            report_id: ID du rapport
            from_line: ligne à partir de laquelle lire (pour une récupération incrémentale, 0 signifie depuis le début)

        Returns:
            {
                "logs": [liste des lignes de journal],
                "total_lines": nombre total de lignes,
                "from_line": numéro de ligne de départ,
                "has_more": s'il reste des journaux supplémentaires
            }
        """
        log_path = cls._get_console_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    # Conserve la ligne de journal d'origine, en retirant le saut de ligne final
                    logs.append(line.rstrip('\n\r'))

        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # Lecture jusqu'à la fin déjà effectuée
        }

    @classmethod
    def get_console_log_stream(cls, report_id: str) -> List[str]:
        """
        Récupère l'intégralité du journal console (récupération en une seule fois)

        Args:
            report_id: ID du rapport

        Returns:
            liste des lignes de journal
        """
        result = cls.get_console_log(report_id, from_line=0)
        return result["logs"]

    @classmethod
    def get_agent_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        Récupère le contenu du journal de l'agent

        Args:
            report_id: ID du rapport
            from_line: ligne à partir de laquelle lire (pour une récupération incrémentale, 0 signifie depuis le début)

        Returns:
            {
                "logs": [liste des entrées de journal],
                "total_lines": nombre total de lignes,
                "from_line": numéro de ligne de départ,
                "has_more": s'il reste des journaux supplémentaires
            }
        """
        log_path = cls._get_agent_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        # Ignore les lignes dont l'analyse a échoué
                        continue

        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # Lecture jusqu'à la fin déjà effectuée
        }

    @classmethod
    def get_agent_log_stream(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        Récupère le journal complet de l'Agent (pour une récupération en une seule fois)

        Args:
            report_id: ID du rapport

        Returns:
            liste des entrées de journal
        """
        result = cls.get_agent_log(report_id, from_line=0)
        return result["logs"]

    @classmethod
    def save_outline(cls, report_id: str, outline: ReportOutline) -> None:
        """
        Enregistre le sommaire du rapport

        Appelé immédiatement après la fin de la phase de planification
        """
        cls._ensure_report_folder(report_id)
        
        with open(cls._get_outline_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(outline.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(t('report.outlineSaved', reportId=report_id))
    
    @classmethod
    def save_section(
        cls,
        report_id: str,
        section_index: int,
        section: ReportSection
    ) -> str:
        """
        Enregistre une section unique

        Appelé immédiatement après la fin de génération de chaque section, pour permettre une sortie par section

        Args:
            report_id: ID du rapport
            section_index: index de la section (à partir de 1)
            section: objet section

        Returns:
            chemin du fichier enregistré
        """
        cls._ensure_report_folder(report_id)

        # Construit le contenu Markdown de la section - nettoie les éventuels titres dupliqués
        cleaned_content = cls._clean_section_content(section.content, section.title)
        md_content = f"## {section.title}\n\n"
        if cleaned_content:
            md_content += f"{cleaned_content}\n\n"

        # Enregistre le fichier
        file_suffix = f"section_{section_index:02d}.md"
        file_path = os.path.join(cls._get_report_folder(report_id), file_suffix)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(t('report.sectionFileSaved', reportId=report_id, fileSuffix=file_suffix))
        return file_path

    @classmethod
    def _clean_section_content(cls, content: str, section_title: str) -> str:
        """
        Nettoie le contenu de la section

        1. Retire les lignes de titre Markdown en début de contenu qui dupliquent le titre de la section
        2. Convertit tous les titres de niveau ### et inférieur en texte en gras

        Args:
            content: contenu original
            section_title: titre de la section

        Returns:
            contenu nettoyé
        """
        import re

        if not content:
            return content

        content = content.strip()
        lines = content.split('\n')
        cleaned_lines = []
        skip_next_empty = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Vérifie s'il s'agit d'une ligne de titre Markdown
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)

            if heading_match:
                level = len(heading_match.group(1))
                title_text = heading_match.group(2).strip()

                # Vérifie s'il s'agit d'un titre dupliquant le titre de la section (ne vérifie que dans les 5 premières lignes)
                if i < 5:
                    if title_text == section_title or title_text.replace(' ', '') == section_title.replace(' ', ''):
                        skip_next_empty = True
                        continue

                # Convertit les titres de tous niveaux (#, ##, ###, ####, etc.) en gras
                # Car le titre de la section est ajouté par le système, le contenu ne doit contenir aucun titre
                cleaned_lines.append(f"**{title_text}**")
                cleaned_lines.append("")  # Ajoute une ligne vide
                continue

            # Si la ligne précédente était un titre ignoré et que la ligne actuelle est vide, on l'ignore aussi
            if skip_next_empty and stripped == '':
                skip_next_empty = False
                continue

            skip_next_empty = False
            cleaned_lines.append(line)

        # Retire les lignes vides en début de contenu
        while cleaned_lines and cleaned_lines[0].strip() == '':
            cleaned_lines.pop(0)

        # Retire les lignes de séparation en début de contenu
        while cleaned_lines and cleaned_lines[0].strip() in ['---', '***', '___']:
            cleaned_lines.pop(0)
            # Retire également les lignes vides après la ligne de séparation
            while cleaned_lines and cleaned_lines[0].strip() == '':
                cleaned_lines.pop(0)

        return '\n'.join(cleaned_lines)

    @classmethod
    def update_progress(
        cls,
        report_id: str,
        status: str,
        progress: int,
        message: str,
        current_section: str = None,
        completed_sections: List[str] = None
    ) -> None:
        """
        Met à jour la progression de la génération du rapport

        Le frontend peut lire progress.json pour obtenir la progression en temps réel
        """
        cls._ensure_report_folder(report_id)
        
        progress_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "current_section": current_section,
            "completed_sections": completed_sections or [],
            "updated_at": datetime.now().isoformat()
        }
        
        with open(cls._get_progress_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def get_progress(cls, report_id: str) -> Optional[Dict[str, Any]]:
        """Récupère la progression de la génération du rapport"""
        path = cls._get_progress_path(report_id)

        if not os.path.exists(path):
            return None

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @classmethod
    def get_generated_sections(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        Récupère la liste des sections déjà générées

        Retourne les informations de tous les fichiers de section déjà enregistrés
        """
        folder = cls._get_report_folder(report_id)

        if not os.path.exists(folder):
            return []

        sections = []
        for filename in sorted(os.listdir(folder)):
            if filename.startswith('section_') and filename.endswith('.md'):
                file_path = os.path.join(folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Analyse l'index de la section à partir du nom de fichier
                parts = filename.replace('.md', '').split('_')
                section_index = int(parts[1])

                sections.append({
                    "filename": filename,
                    "section_index": section_index,
                    "content": content
                })

        return sections

    @classmethod
    def assemble_full_report(cls, report_id: str, outline: ReportOutline) -> str:
        """
        Assemble le rapport complet

        Assemble le rapport complet à partir des fichiers de section déjà enregistrés, avec nettoyage des titres
        """
        folder = cls._get_report_folder(report_id)

        # Construit l'en-tête du rapport
        md_content = f"# {outline.title}\n\n"
        md_content += f"> {outline.summary}\n\n"
        md_content += f"---\n\n"

        # Lit tous les fichiers de section dans l'ordre
        sections = cls.get_generated_sections(report_id)
        for section_info in sections:
            md_content += section_info["content"]

        # Post-traitement : nettoie les problèmes de titres dans l'ensemble du rapport
        md_content = cls._post_process_report(md_content, outline)

        # Enregistre le rapport complet
        full_path = cls._get_report_markdown_path(report_id)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(t('report.fullReportAssembled', reportId=report_id))
        return md_content

    @classmethod
    def _post_process_report(cls, content: str, outline: ReportOutline) -> str:
        """
        Post-traite le contenu du rapport

        1. Retire les titres dupliqués
        2. Conserve le titre principal du rapport (#) et les titres de section (##), retire les titres des autres niveaux (###, ####, etc.)
        3. Nettoie les lignes vides et lignes de séparation superflues

        Args:
            content: contenu original du rapport
            outline: sommaire du rapport

        Returns:
            contenu traité
        """
        import re

        lines = content.split('\n')
        processed_lines = []
        prev_was_heading = False

        # Collecte tous les titres de section du sommaire
        section_titles = set()
        for section in outline.sections:
            section_titles.add(section.title)

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Vérifie s'il s'agit d'une ligne de titre
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)

            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()

                # Vérifie s'il s'agit d'un titre dupliqué (titre au contenu identique apparaissant dans les 5 lignes précédentes)
                is_duplicate = False
                for j in range(max(0, len(processed_lines) - 5), len(processed_lines)):
                    prev_line = processed_lines[j].strip()
                    prev_match = re.match(r'^(#{1,6})\s+(.+)$', prev_line)
                    if prev_match:
                        prev_title = prev_match.group(2).strip()
                        if prev_title == title:
                            is_duplicate = True
                            break

                if is_duplicate:
                    # Ignore le titre dupliqué et les lignes vides qui suivent
                    i += 1
                    while i < len(lines) and lines[i].strip() == '':
                        i += 1
                    continue

                # Traitement des niveaux de titre :
                # - # (level=1) ne conserve que le titre principal du rapport
                # - ## (level=2) conserve les titres de section
                # - ### et en dessous (level>=3) convertis en texte en gras

                if level == 1:
                    if title == outline.title:
                        # Conserve le titre principal du rapport
                        processed_lines.append(line)
                        prev_was_heading = True
                    elif title in section_titles:
                        # Titre de section utilisant # par erreur, corrigé en ##
                        processed_lines.append(f"## {title}")
                        prev_was_heading = True
                    else:
                        # Les autres titres de niveau 1 sont convertis en gras
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                elif level == 2:
                    if title in section_titles or title == outline.title:
                        # Conserve le titre de section
                        processed_lines.append(line)
                        prev_was_heading = True
                    else:
                        # Les titres de niveau 2 qui ne sont pas des sections sont convertis en gras
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                else:
                    # Les titres de niveau ### et en dessous sont convertis en texte en gras
                    processed_lines.append(f"**{title}**")
                    processed_lines.append("")
                    prev_was_heading = False

                i += 1
                continue

            elif stripped == '---' and prev_was_heading:
                # Ignore la ligne de séparation qui suit immédiatement un titre
                i += 1
                continue

            elif stripped == '' and prev_was_heading:
                # Ne conserve qu'une seule ligne vide après un titre
                if processed_lines and processed_lines[-1].strip() != '':
                    processed_lines.append(line)
                prev_was_heading = False

            else:
                processed_lines.append(line)
                prev_was_heading = False

            i += 1

        # Nettoie les lignes vides consécutives (conserve un maximum de 2)
        result_lines = []
        empty_count = 0
        for line in processed_lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:
                    result_lines.append(line)
            else:
                empty_count = 0
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @classmethod
    def save_report(cls, report: Report) -> None:
        """保存报告元信息和完整报告"""
        cls._ensure_report_folder(report.report_id)
        
        # 保存元信息JSON
        with open(cls._get_report_path(report.report_id), 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 保存大纲
        if report.outline:
            cls.save_outline(report.report_id, report.outline)
        
        # 保存完整Markdown报告
        if report.markdown_content:
            with open(cls._get_report_markdown_path(report.report_id), 'w', encoding='utf-8') as f:
                f.write(report.markdown_content)
        
        logger.info(t('report.reportSaved', reportId=report.report_id))
    
    @classmethod
    def get_report(cls, report_id: str) -> Optional[Report]:
        """获取报告"""
        path = cls._get_report_path(report_id)
        
        if not os.path.exists(path):
            # 兼容旧格式：检查直接存储在reports目录下的文件
            old_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
            if os.path.exists(old_path):
                path = old_path
            else:
                return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 重建Report对象
        outline = None
        if data.get('outline'):
            outline_data = data['outline']
            sections = []
            for s in outline_data.get('sections', []):
                sections.append(ReportSection(
                    title=s['title'],
                    content=s.get('content', '')
                ))
            outline = ReportOutline(
                title=outline_data['title'],
                summary=outline_data['summary'],
                sections=sections
            )
        
        # 如果markdown_content为空，尝试从full_report.md读取
        markdown_content = data.get('markdown_content', '')
        if not markdown_content:
            full_report_path = cls._get_report_markdown_path(report_id)
            if os.path.exists(full_report_path):
                with open(full_report_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
        
        return Report(
            report_id=data['report_id'],
            simulation_id=data['simulation_id'],
            graph_id=data['graph_id'],
            simulation_requirement=data['simulation_requirement'],
            status=ReportStatus(data['status']),
            outline=outline,
            markdown_content=markdown_content,
            created_at=data.get('created_at', ''),
            completed_at=data.get('completed_at', ''),
            error=data.get('error')
        )
    
    @classmethod
    def get_report_by_simulation(cls, simulation_id: str) -> Optional[Report]:
        """根据模拟ID获取报告"""
        cls._ensure_reports_dir()
        
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # 新格式：文件夹
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report and report.simulation_id == simulation_id:
                    return report
            # 兼容旧格式：JSON文件
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report and report.simulation_id == simulation_id:
                    return report
        
        return None
    
    @classmethod
    def list_reports(cls, simulation_id: Optional[str] = None, limit: int = 50) -> List[Report]:
        """列出报告"""
        cls._ensure_reports_dir()
        
        reports = []
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # 新格式：文件夹
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
            # 兼容旧格式：JSON文件
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
        
        # 按创建时间倒序
        reports.sort(key=lambda r: r.created_at, reverse=True)
        
        return reports[:limit]
    
    @classmethod
    def delete_report(cls, report_id: str) -> bool:
        """删除报告（整个文件夹）"""
        import shutil
        
        folder_path = cls._get_report_folder(report_id)
        
        # 新格式：删除整个文件夹
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            logger.info(t('report.reportFolderDeleted', reportId=report_id))
            return True
        
        # 兼容旧格式：删除单独的文件
        deleted = False
        old_json_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
        old_md_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.md")
        
        if os.path.exists(old_json_path):
            os.remove(old_json_path)
            deleted = True
        if os.path.exists(old_md_path):
            os.remove(old_md_path)
            deleted = True
        
        return deleted
