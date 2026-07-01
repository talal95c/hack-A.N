"""
Pipeline "loi → règle calculable" via OpenFisca-France (CLAUDE.md §1, §5) — l'approche LexImpact :

1. Extraction LLM des changements paramétriques candidats du texte de loi.
2. Rapprochement avec un dictionnaire de correspondance vers les paramètres OpenFisca-France connus.
3. Simulation sur une batterie de cas types représentatifs (pondérés INSEE).
4. Validation humaine obligatoire avant qu'un résultat entre dans un scénario publiable
   (CLAUDE.md §2 — principe non négociable, indépendant du calendrier).

⚠️ RÉSOLU (voir CLAUDE.md §1 note d'environnement) : `openfisca-france` ne s'importe PAS sous
Python 3.12 (`TypeError: metaclass conflict` dans `openfisca_core.types`, incompatibilité connue
avec numpy/typing récents). Vérifié fonctionnel sous **Python 3.11** (`backend/.venv311`, même
venv dédié que le sous-processus OASIS, cf. `Config.OASIS_PYTHON_EXECUTABLE`). Ce module continue
d'importer `openfisca_france` de façon paresseuse et différée (jamais au chargement du module) et
de renvoyer `available=False` proprement si l'import échoue — utile pour que le process Flask
principal (qui peut tourner en 3.12) continue de fonctionner même sans OpenFisca en mémoire.

En pratique, ce pipeline est appelé de deux façons :
1. **Hors ligne, via `backend/scripts/precompute_openfisca.py`**, exécuté explicitement avec
   l'interpréteur `.venv311` (`.venv311/Scripts/python.exe backend/scripts/precompute_openfisca.py`)
   -- c'est le chemin recommandé et le seul garanti fonctionnel pour la simulation réelle.
2. En léger (`check_openfisca_available`) depuis le process principal, pour savoir si la couche de
   calcul réel doit être proposée à l'utilisateur -- renverra `available=False` si le process
   principal tourne en Python ≥3.12, ce qui est attendu et géré.
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional

from . import StructuredResult

logger = logging.getLogger(__name__)

# Dictionnaire de correspondance "concept de loi -> paramètre OpenFisca-France connu".
# À enrichir au fur et à mesure des textes traités (CLAUDE.md §5 : "dictionnaire de correspondance
# entretenu"). Les clés sont des libellés humains utilisés par l'extraction LLM ; les valeurs sont
# des chemins de paramètres réels d'openfisca-france (ex: 'prestations_sociales.aides_logement...').
KNOWN_PARAMETER_MAPPING: dict[str, str] = {
    "plafond_loyer_zone_tendue": "prestations_sociales.aides_logement.al_parametres.plafond_loyer",
    "taux_apl": "prestations_sociales.aides_logement.al_parametres.taux",
    # Ajouter ici de nouvelles correspondances validées humainement, pas générées automatiquement.
}


@dataclass
class OpenFiscaScenarioParameter:
    """Un changement paramétrique candidat, extrait du texte de loi puis validé par un humain
    avant simulation (CLAUDE.md §2)."""
    law_concept_label: str
    openfisca_parameter_path: Optional[str]
    proposed_value: Any
    human_validated: bool = False
    validated_by: Optional[str] = None
    period: Optional[str] = None  # ex: "2025-01" -- défaut appliqué dans simulate_impact si absent


def _lazy_import_openfisca():
    """Import différé d'openfisca_france — voir avertissement en tête de module."""
    from openfisca_france import FranceTaxBenefitSystem  # type: ignore
    from openfisca_core.simulation_builder import SimulationBuilder  # type: ignore
    return FranceTaxBenefitSystem, SimulationBuilder


def check_openfisca_available() -> StructuredResult:
    """Vérifie si le moteur OpenFisca-France est utilisable dans l'environnement courant, sans
    lever d'exception. À appeler au démarrage de l'application pour savoir si la couche de calcul
    réel doit être proposée à l'utilisateur ou grisée."""
    try:
        _lazy_import_openfisca()
        return StructuredResult(source="openfisca-france", available=True, data={"status": "importable"})
    except Exception as exc:  # noqa: BLE001
        logger.warning("openfisca-france indisponible dans cet environnement: %s", exc)
        return StructuredResult(source="openfisca-france", available=False, error=str(exc))


def extract_candidate_parameters(law_text: str, llm_client) -> list[OpenFiscaScenarioParameter]:
    """Étape 1 : demande au LLM d'identifier les changements paramétriques candidats dans le texte
    de loi, puis les rapproche du dictionnaire de correspondance connu (étape 2). Ne simule rien —
    produit uniquement une liste de candidats à valider humainement."""
    import json

    prompt = (
        "Tu es un assistant d'analyse législative. Le texte de loi suivant peut contenir des "
        "changements de paramètres fiscaux ou sociaux calculables (plafonds, taux, seuils). "
        "Identifie au maximum 3 changements paramétriques candidats. Réponds en JSON strict : "
        '{"candidates": [{"label": "...", "proposed_value": ...}]}\n\n'
        f"Concepts de paramètres connus (utilise ces libellés exacts si applicable) : "
        f"{list(KNOWN_PARAMETER_MAPPING.keys())}\n\n"
        f"Texte de loi :\n{law_text[:8000]}"
    )
    result = llm_client.chat_json(messages=[{"role": "user", "content": prompt}], temperature=0.2)
    candidates = []
    for item in result.get("candidates", []):
        label = item.get("label", "")
        candidates.append(OpenFiscaScenarioParameter(
            law_concept_label=label,
            openfisca_parameter_path=KNOWN_PARAMETER_MAPPING.get(label),
            proposed_value=item.get("proposed_value"),
            human_validated=False,
        ))
    return candidates


def simulate_impact(
    validated_parameters: list[OpenFiscaScenarioParameter],
    household_cases: list[dict],
) -> StructuredResult:
    """Étape 3 : simule l'impact des paramètres **validés humainement** sur une batterie de cas
    types de ménages (household_cases -- typiquement dérivés des archétypes citoyens INSEE).
    Refuse de simuler tout paramètre non validé (CLAUDE.md §2)."""
    unvalidated = [p for p in validated_parameters if not p.human_validated]
    if unvalidated:
        return StructuredResult(
            source="openfisca-france", available=False,
            error=(
                f"{len(unvalidated)} paramètre(s) non validé(s) humainement — refus de simuler. "
                "Cf. CLAUDE.md §2 : toute règle légale générée automatiquement doit être validée "
                "avant usage."
            ),
        )

    try:
        FranceTaxBenefitSystem, SimulationBuilder = _lazy_import_openfisca()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Simulation OpenFisca impossible (import échoué): %s", exc)
        return StructuredResult(source="openfisca-france", available=False, error=str(exc))

    try:
        tax_benefit_system = FranceTaxBenefitSystem()
        for param in validated_parameters:
            if not param.openfisca_parameter_path:
                continue
            # Traversée par attribut du ParameterNode racine (vérifié : ParameterNode n'a pas de
            # méthode get_child, la navigation se fait par attributs successifs correspondant aux
            # segments du chemin séparés par des points).
            node = tax_benefit_system.parameters
            for segment in param.openfisca_parameter_path.split('.'):
                node = getattr(node, segment)
            # `node` est ici un Parameter (feuille) -- .update(period=..., value=...) est l'API
            # réelle vérifiée (openfisca-core), pas la signature `value=` seule initialement supposée.
            node.update(period=param.period or "2025-01", value=param.proposed_value)

        results = []
        for case in household_cases:
            # `case["situation"]` doit contenir UNIQUEMENT les entités reconnues par
            # openfisca-france (individus/menages/familles/foyers_fiscaux) -- vérifié : toute clé
            # supplémentaire au même niveau (metadata) fait échouer build_from_entities avec
            # SituationParsingError. Le reste (archetype_id, target_variable, period) est donc
            # gardé à part, au niveau du case, jamais mélangé dans la situation elle-même.
            simulation_builder = SimulationBuilder()
            simulation = simulation_builder.build_from_entities(tax_benefit_system, case["situation"])
            variable = case.get("target_variable", "revenu_disponible")
            period = case.get("period", "2025-01")
            value = simulation.calculate(variable, period)
            results.append({
                "archetype_id": case.get("archetype_id"),
                "variable": variable,
                "period": period,
                "value": float(value[0]) if hasattr(value, "__len__") else float(value),
            })

        return StructuredResult(source="openfisca-france", available=True, data=results)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erreur pendant la simulation OpenFisca")
        return StructuredResult(source="openfisca-france", available=False, error=str(exc))
