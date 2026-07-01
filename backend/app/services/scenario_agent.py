"""
Agent de scénario tendanciel (CLAUDE.md §6) — construit sur le même modèle que `report_agent.py`
(recherche outillée sur le graphe Zep de la simulation via `zep_tools.py`) mais agent **séparé**,
avec un plan de sections dédié et resserré : là où `ReportAgent` fait un recap de ce qui s'est
passé pendant la simulation, `ScenarioAgent` projette la situation dans le temps.

Stockage fichier (comme MiroFish, pas de DB) sous
`backend/uploads/scenarios/<scenario_id>/scenario.json`.
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.locale import get_language_instruction
from .regulatory_data.tricoteuses_client import fetch_parliamentary_groups
from .vote_aggregation import GroupPosition, GroupSeats, aggregate_vote
from .zep_tools import ZepToolsService

logger = logging.getLogger(__name__)


class ScenarioStatus(str, Enum):
    PLANNING = "planning"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ScenarioSection:
    title: str
    content: str = ""

    def to_dict(self) -> dict:
        return {"title": self.title, "content": self.content}


@dataclass
class ScenarioReport:
    scenario_id: str
    simulation_id: str
    status: ScenarioStatus
    title: str = ""
    sections: list[ScenarioSection] = field(default_factory=list)
    # Résultat du vote simulé, pondéré par les sièges réels des groupes parlementaires (cf.
    # description du produit : "Ils débattent, proposent des amendements et votent sur le texte
    # soumis") -- voir vote_aggregation.aggregate_vote(). None si le calcul a échoué (dégradation
    # propre, jamais une exception qui casse toute la génération du scénario).
    vote_outcome: Optional[dict] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "simulation_id": self.simulation_id,
            "status": self.status.value,
            "title": self.title,
            "sections": [s.to_dict() for s in self.sections],
            "vote_outcome": self.vote_outcome,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScenarioReport":
        return cls(
            scenario_id=data["scenario_id"],
            simulation_id=data["simulation_id"],
            status=ScenarioStatus(data.get("status", "planning")),
            title=data.get("title", ""),
            sections=[ScenarioSection(**s) for s in data.get("sections", [])],
            vote_outcome=data.get("vote_outcome"),
            error=data.get("error"),
            created_at=data.get("created_at", ""),
            completed_at=data.get("completed_at"),
        )


# Plan de sections fixe et resserré (CLAUDE.md §6) — pas d'invention par le LLM, contrairement au
# plan de ReportAgent : la structure du scénario tendanciel est toujours la même.
SECTION_SPECS = [
    {
        "title": "État actuel observé",
        "search_query": "positions et réactions des groupes parlementaires et des citoyens pendant la simulation",
    },
    {
        "title": "Trajectoire tendancielle",
        "search_query": "évolution des positions, tensions, points de blocage et dynamique du débat au fil de la simulation",
    },
    {
        "title": "Points de bascule",
        "search_query": "désaccords, revirements ou signaux faibles qui pourraient faire évoluer la situation",
    },
]

SECTION_WRITER_SYSTEM_PROMPT = """Tu es l'agent de scénario tendanciel de MiroPolis. Tu rédiges une
section d'un scénario prospectif exploratoire à partir d'éléments réellement observés pendant une
simulation multi-agents (Députés = groupes parlementaires, Citoyens = archétypes démographiques).

Règles impératives :
- Ceci est une estimation exploratoire, jamais une prédiction certaine -- reste prudent et nuancé.
- Ne mentionne jamais un élu nommé individuellement, seulement des groupes parlementaires.
- Base-toi sur les éléments de recherche fournis ; si l'information manque, dis-le plutôt que
  d'inventer.
- 3 à 5 phrases, style clair et direct pour un décideur (élu ou collaborateur parlementaire)."""

VOTE_EXTRACTION_SYSTEM_PROMPT = """Tu analyses la mémoire d'une simulation législative multi-agents
pour en extraire la position de vote de chaque groupe parlementaire réel sur le texte débattu.
Réponds en JSON strict : {"positions": {"NomAbrégéDuGroupe": "support"|"oppose"|"abstain"|"undecided", ...}}
Une entrée par groupe listé, jamais plus, jamais moins. Si l'information est insuffisante pour un
groupe, réponds "undecided" pour celui-ci plutôt que d'inventer une position."""

SECTION_WRITER_USER_TEMPLATE = """Section à rédiger : "{section_title}"

Besoin de la simulation : {simulation_requirement}

Éléments trouvés dans la mémoire de la simulation :
{search_findings}

Sections déjà rédigées (pour cohérence, ne pas répéter) :
{previous_sections}

Rédige uniquement le contenu de cette section (pas de titre, pas de préambule)."""


class ScenarioAgent:
    """Génère un scénario tendanciel à partir de la mémoire Zep d'une simulation déjà exécutée."""

    def __init__(
        self,
        graph_id: str,
        simulation_id: str,
        simulation_requirement: str,
        api_key: Optional[str] = None,
    ):
        self.graph_id = graph_id
        self.simulation_id = simulation_id
        self.simulation_requirement = simulation_requirement
        self.tools = ZepToolsService(api_key=api_key)
        self.llm_client = LLMClient()

    def _search_for_section(self, section_spec: dict) -> str:
        """Recherche outillée sur le graphe (même outil que ReportAgent : InsightForge), avec
        repli sur une recherche simple si InsightForge échoue -- jamais d'exception qui casserait
        toute la génération pour une seule section."""
        try:
            result = self.tools.insight_forge(
                graph_id=self.graph_id,
                query=section_spec["search_query"],
                simulation_requirement=self.simulation_requirement,
            )
            return result.to_text()
        except Exception as exc:  # noqa: BLE001
            logger.warning("InsightForge échoué pour '%s', repli sur quick_search: %s", section_spec["title"], exc)
            try:
                result = self.tools.quick_search(graph_id=self.graph_id, query=section_spec["search_query"])
                return result.to_text()
            except Exception as exc2:  # noqa: BLE001
                logger.warning("quick_search échoué également pour '%s': %s", section_spec["title"], exc2)
                return "(aucun élément trouvé dans la mémoire de la simulation)"

    def _write_section(self, section_spec: dict, search_findings: str, previous_sections: list[ScenarioSection]) -> str:
        previous_text = "\n".join(f"- {s.title}: {s.content[:200]}" for s in previous_sections) or "(aucune)"
        prompt = SECTION_WRITER_USER_TEMPLATE.format(
            section_title=section_spec["title"],
            simulation_requirement=self.simulation_requirement,
            search_findings=search_findings[:4000],
            previous_sections=previous_text,
        )
        system_prompt = f"{SECTION_WRITER_SYSTEM_PROMPT}\n\n{get_language_instruction()}"
        return self.llm_client.chat(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            temperature=Config.SCENARIO_AGENT_TEMPERATURE,
        )

    def _compute_vote_outcome(self) -> Optional[dict]:
        """Calcule le résultat du vote simulé, pondéré par les sièges réels des groupes
        parlementaires -- concrétise "Ils ... votent sur le texte soumis". Dégrade proprement
        (retourne None) si les données réelles ou l'extraction LLM échouent, jamais d'exception
        qui casserait toute la génération du scénario pour autant."""
        try:
            groups_result = fetch_parliamentary_groups()
            if not groups_result.available or not groups_result.data:
                logger.warning("Composition des groupes indisponible, vote non calculé: %s", groups_result.error)
                return None

            group_names = [g["libelleAbrege"] for g in groups_result.data]
            findings = self._search_for_section({
                "title": "positions de vote",
                "search_query": "position de chaque groupe parlementaire sur le texte : soutien, opposition ou abstention",
            })

            prompt = (
                f"Groupes parlementaires réels à statuer (exactement ceux-ci) : {group_names}\n\n"
                f"Éléments observés dans la simulation :\n{findings[:4000]}"
            )
            system_prompt = f"{VOTE_EXTRACTION_SYSTEM_PROMPT}\n\n{get_language_instruction()}"
            result = self.llm_client.chat_json(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                temperature=0.2,
            )
            positions = result.get("positions", {})

            group_seats = []
            for g in groups_result.data:
                raw_position = positions.get(g["libelleAbrege"], "undecided")
                try:
                    position = GroupPosition(raw_position)
                except ValueError:
                    position = GroupPosition.UNDECIDED
                group_seats.append(GroupSeats(group_name=g["libelleAbrege"], seats=g["nombreMembres"], position=position))

            return aggregate_vote(group_seats).to_dict()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Calcul du vote simulé échoué: %s", exc)
            return None

    def generate_scenario(
        self,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        scenario_id: Optional[str] = None,
    ) -> ScenarioReport:
        scenario_id = scenario_id or f"scenario_{uuid.uuid4().hex[:12]}"
        report = ScenarioReport(
            scenario_id=scenario_id, simulation_id=self.simulation_id,
            status=ScenarioStatus.PLANNING, title="Scénario tendanciel exploratoire",
        )

        def notify(stage: str, progress: int, message: str):
            if progress_callback:
                progress_callback(stage, progress, message)

        try:
            notify("planning", 5, "Préparation du plan de scénario")
            report.status = ScenarioStatus.GENERATING

            notify("generating", 8, "Calcul du vote simulé (pondéré par sièges réels)")
            report.vote_outcome = self._compute_vote_outcome()

            for i, section_spec in enumerate(SECTION_SPECS):
                progress = 10 + int(80 * i / len(SECTION_SPECS))
                notify("generating", progress, f"Section: {section_spec['title']}")

                findings = self._search_for_section(section_spec)
                if i == 0 and report.vote_outcome:
                    # Injecte le résultat du vote calculé dans le contexte de la première section
                    # ("État actuel observé"), pour que la narration s'appuie dessus explicitement.
                    findings += f"\n\nRésultat du vote simulé (pondéré par sièges réels): {report.vote_outcome}"
                content = self._write_section(section_spec, findings, report.sections)
                report.sections.append(ScenarioSection(title=section_spec["title"], content=content))

            report.status = ScenarioStatus.COMPLETED
            report.completed_at = datetime.now().isoformat()
            notify("completed", 100, "Scénario tendanciel généré")
        except Exception as exc:  # noqa: BLE001
            logger.error("Génération du scénario échouée: %s", exc)
            report.status = ScenarioStatus.FAILED
            report.error = str(exc)

        return report


class ScenarioManager:
    """Stockage fichier du scénario, même pattern que `ReportManager` (pas de DB)."""

    @classmethod
    def _dir(cls) -> str:
        path = os.path.join(Config.UPLOAD_FOLDER, "scenarios")
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def _path(cls, scenario_id: str) -> str:
        return os.path.join(cls._dir(), f"{scenario_id}.json")

    @classmethod
    def save_scenario(cls, report: ScenarioReport) -> None:
        with open(cls._path(report.scenario_id), "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def get_scenario(cls, scenario_id: str) -> Optional[ScenarioReport]:
        path = cls._path(scenario_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return ScenarioReport.from_dict(json.load(f))

    @classmethod
    def get_scenario_by_simulation(cls, simulation_id: str) -> Optional[ScenarioReport]:
        latest: Optional[ScenarioReport] = None
        for filename in os.listdir(cls._dir()):
            if not filename.endswith(".json"):
                continue
            with open(os.path.join(cls._dir(), filename), "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("simulation_id") == simulation_id:
                candidate = ScenarioReport.from_dict(data)
                if latest is None or candidate.created_at > latest.created_at:
                    latest = candidate
        return latest
