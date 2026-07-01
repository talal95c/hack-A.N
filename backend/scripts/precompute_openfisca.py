#!/usr/bin/env python
"""
Script de précalcul OpenFisca (CLAUDE.md §4.2) : encode un scénario de paramètre(s) de loi validé
humainement, calcule l'impact sur une batterie de cas types de ménages, écrit le résultat dans
backend/uploads/territorial_cache/openfisca_results.json.

⚠️ À exécuter avec l'interpréteur Python 3.11 dédié (backend/.venv311), jamais avec le venv
principal -- voir CLAUDE.md §1 et app/services/regulatory_data/openfisca_pipeline.py pour le détail
de la contrainte de compatibilité. Jamais exécuté en direct pendant une démo (CLAUDE.md §2) : ce
script tourne hors ligne, avant la présentation.

Usage :
    backend/.venv311/Scripts/python.exe backend/scripts/precompute_openfisca.py --scenario logement_apl

Le mapping "scénario -> paramètres" est volontairement statique et versionné dans ce fichier, pas
généré dynamiquement à l'exécution : chaque scénario doit être ajouté ici après validation humaine
explicite de ses paramètres OpenFisca (CLAUDE.md §2, "Tout code de règle légale généré
automatiquement... passe par une validation humaine avant usage").
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import Config  # noqa: E402
from app.services.regulatory_data.openfisca_pipeline import (  # noqa: E402
    OpenFiscaScenarioParameter, check_openfisca_available, simulate_impact,
)

# ---------------------------------------------------------------------------
# Scénarios pré-validés humainement (CLAUDE.md §2). Ajouter ici un nouveau scénario UNIQUEMENT
# après vérification manuelle du chemin de paramètre OpenFisca-France et de la valeur proposée.
# ---------------------------------------------------------------------------
SCENARIOS: dict[str, list[OpenFiscaScenarioParameter]] = {
    # Chemin vérifié réel (introspection directe de FranceTaxBenefitSystem().parameters, 2026-07) :
    # coefficient de plafond de loyer appliqué en cas de colocation pour le calcul des allocations
    # logement locatives -- pertinent pour un scénario de loi "encadrement des loyers / colocation".
    "logement_apl": [
        OpenFiscaScenarioParameter(
            law_concept_label="coef_colocation_plafond_loyer",
            openfisca_parameter_path=(
                "prestations_sociales.aides_logement.allocations_logement.locatif.formule."
                "l_plafonds_loyers.coef_chambre_et_colocation.coef_colocation"
            ),
            proposed_value=0.85,  # exemple illustratif -- à ajuster selon le vrai texte de loi étudié
            period="2025-01",
            human_validated=True,
            validated_by="cli-operator",
        ),
    ],
}

# Cas types de ménages représentatifs (à faire correspondre aux archétypes citoyens INSEE générés
# par population_synthesizer.py -- ici en exemple minimal, à enrichir par scénario réel).
DEFAULT_HOUSEHOLD_CASES = [
    {
        "archetype_id": "tenant-young-active",
        "target_variable": "aide_logement",
        "period": "2025-01",
        # "situation" : format OpenFisca standard (entités individus/menages/familles/foyers_fiscaux
        # UNIQUEMENT -- toute autre clé au même niveau fait échouer build_from_entities, vérifié).
        "situation": {
            "individus": {"parent1": {"salaire_de_base": {"2025-01": 1800}}},
            "menages": {"menage1": {"personne_de_reference": ["parent1"], "loyer": {"2025-01": 750}}},
            "familles": {"famille1": {"parents": ["parent1"]}},
            "foyers_fiscaux": {"foyer1": {"declarants": ["parent1"]}},
        },
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, choices=sorted(SCENARIOS.keys()))
    parser.add_argument("--output", default=None, help="Chemin de sortie (défaut: cache territorial standard)")
    args = parser.parse_args()

    availability = check_openfisca_available()
    if not availability.available:
        print(f"ERREUR : openfisca-france indisponible dans cet interpréteur : {availability.error}", file=sys.stderr)
        print("Ce script doit être exécuté avec backend/.venv311/Scripts/python.exe", file=sys.stderr)
        return 1

    parameters = SCENARIOS[args.scenario]
    result = simulate_impact(parameters, DEFAULT_HOUSEHOLD_CASES)

    if not result.available:
        print(f"ERREUR de simulation OpenFisca : {result.error}", file=sys.stderr)
        return 1

    output_path = args.output or os.path.join(Config.TERRITORIAL_CACHE_DIR, "openfisca_results.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"scenario": args.scenario, "results": result.data}, f, ensure_ascii=False, indent=2)

    print(f"OK : résultats écrits dans {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
