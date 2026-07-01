"""
Client "composition des groupes parlementaires" (CLAUDE.md §3, couche 1).

⚠️ Historique de la décision (important pour la maintenance) : ce module s'appelait à l'origine
un client GraphQL vers `assemblee.tricoteuses.fr`. Vérifié à l'implémentation : cette URL sert
l'application front-end (SvelteKit, SPA) sur toutes les routes, pas un endpoint GraphQL JSON, et
le point d'entrée réel du projet `tricoteuses-api-assemblee` n'a pas pu être confirmé publiquement.

**Source retenue et vérifiée fonctionnelle en conditions réelles** : le dataset officiel
"Groupes politiques actifs de l'Assemblée nationale" publié sur data.gouv.fr
(`Config.DATAGOUV_GROUPES_DATASET_ID`), dont la ressource CSV est mise à jour automatiquement
(vérifié : la ressource porte la date du jour dans son URL et sa colonne `dateMaj`). Ce fichier
contient exactement ce dont MiroPolis a besoin pour la couche 2 (composition réelle par groupe,
avec effectif réel utilisable directement par `vote_aggregation.py`).

Le module ne contient plus que cette fonction : `fetch_historical_votes` (utilisée pour le
backtesting) a été retirée avec le reste des fonctionnalités hors scope de MiroFish v2.
"""

import csv
import io
import logging

import requests

from ...config import Config
from . import StructuredResult
from ._cache import read_cache, write_cache
from .datagouv_mcp_client import fetch_dataset_resource

logger = logging.getLogger(__name__)


def fetch_parliamentary_groups(force_refresh: bool = False) -> StructuredResult:
    """Composition actuelle des groupes parlementaires (nom, effectif réel), depuis le dataset
    officiel data.gouv.fr -- source vérifiée fonctionnelle (voir docstring du module). Mise en
    cache local (`tricoteuses_groupes.json`) pour respecter la règle "aucun appel réseau live
    pendant une démo" (CLAUDE.md §2)."""
    cache_filename = "tricoteuses_groupes.json"

    if not force_refresh:
        cached = read_cache(cache_filename)
        if cached is not None:
            return StructuredResult(source="data.gouv.fr/an-groupes", available=True, data=cached, from_cache=True)

    try:
        resources = fetch_dataset_resource(Config.DATAGOUV_GROUPES_DATASET_ID)
        if not resources.available:
            raise RuntimeError(f"dataset AN groupes indisponible: {resources.error}")

        csv_resource = next((r for r in resources.data if r.get("format") == "csv"), None)
        if csv_resource is None:
            raise RuntimeError("aucune ressource CSV trouvée dans le dataset AN groupes")

        response = requests.get(csv_resource["url"], timeout=Config.HTTP_CLIENT_TIMEOUT_SECONDS)
        response.raise_for_status()
        response.encoding = "utf-8"

        reader = csv.DictReader(io.StringIO(response.text))
        groups = [
            {
                "uid": row["id"],
                "libelle": row["libelle"],
                "libelleAbrege": row["libelleAbrege"],
                "nombreMembres": int(row["effectif"]) if row.get("effectif") else 0,
                "couleurAssociee": row.get("couleurAssociee"),
                "dateMaj": row.get("dateMaj"),
            }
            for row in reader
        ]

        write_cache(cache_filename, groups)
        return StructuredResult(source="data.gouv.fr/an-groupes", available=True, data=groups, from_cache=False)
    except Exception as exc:  # noqa: BLE001 — on ne laisse jamais une erreur réseau remonter brute
        logger.warning("fetch_parliamentary_groups failed: %s", exc)
        cached = read_cache(cache_filename)
        if cached is not None:
            return StructuredResult(
                source="data.gouv.fr/an-groupes", available=True, data=cached, from_cache=True,
                metadata={"stale": True, "refresh_error": str(exc)},
            )
        return StructuredResult(source="data.gouv.fr/an-groupes", available=False, error=str(exc))


