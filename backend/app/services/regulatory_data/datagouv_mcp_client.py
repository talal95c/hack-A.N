"""
Client data.gouv.fr (CLAUDE.md §3, couche 1) — artificialisation des sols (ZAN/Cerema), budgets
carbone, emploi territorial, et tout autre jeu de données public pertinent.

Statut vérifié à l'implémentation : `https://www.data.gouv.fr/api/1/` répond HTTP 200 et est une
API REST/CKAN classique, bien documentée et directement utilisable avec `requests` (vérifié en
conditions réelles, c'est cette API qui est utilisée ici, pas le serveur MCP officiel de
data.gouv.fr qui demanderait un client MCP dédié plus lourd à opérer côté serveur qu'un simple
appel REST pour le même résultat).
"""

import logging

import requests

from ...config import Config
from . import StructuredResult
from ._cache import read_cache, write_cache

logger = logging.getLogger(__name__)


def search_datasets(query: str, page_size: int = 5) -> StructuredResult:
    """Recherche de jeux de données sur data.gouv.fr par mot-clé (ex: "artificialisation des sols
    ZAN région")."""
    cache_filename = f"datagouv_search_{query.replace(' ', '_')[:60]}.json"
    cached = read_cache(cache_filename)
    if cached is not None:
        return StructuredResult(source="data.gouv.fr", available=True, data=cached, from_cache=True)

    try:
        response = requests.get(
            f"{Config.DATAGOUV_API_URL}/datasets/",
            params={"q": query, "page_size": page_size},
            timeout=Config.HTTP_CLIENT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        datasets = [
            {
                "id": d.get("id"),
                "title": d.get("title"),
                "url": d.get("page"),
                "organization": (d.get("organization") or {}).get("name"),
            }
            for d in payload.get("data", [])
        ]
        write_cache(cache_filename, datasets)
        return StructuredResult(source="data.gouv.fr", available=True, data=datasets, from_cache=False)
    except Exception as exc:  # noqa: BLE001
        logger.warning("data.gouv.fr search_datasets(%r) failed: %s", query, exc)
        return StructuredResult(source="data.gouv.fr", available=False, error=str(exc))


def fetch_dataset_resource(dataset_id: str) -> StructuredResult:
    """Récupère les métadonnées des ressources (fichiers) d'un jeu de données identifié."""
    cache_filename = f"datagouv_dataset_{dataset_id}.json"
    cached = read_cache(cache_filename)
    if cached is not None:
        return StructuredResult(source="data.gouv.fr", available=True, data=cached, from_cache=True)

    try:
        response = requests.get(
            f"{Config.DATAGOUV_API_URL}/datasets/{dataset_id}/",
            timeout=Config.HTTP_CLIENT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        resources = [
            {"title": r.get("title"), "url": r.get("url"), "format": r.get("format")}
            for r in payload.get("resources", [])
        ]
        write_cache(cache_filename, resources)
        return StructuredResult(source="data.gouv.fr", available=True, data=resources, from_cache=False)
    except Exception as exc:  # noqa: BLE001
        logger.warning("data.gouv.fr fetch_dataset_resource(%s) failed: %s", dataset_id, exc)
        return StructuredResult(source="data.gouv.fr", available=False, error=str(exc))
