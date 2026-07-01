"""
Client Tricoteuses (CLAUDE.md §3, couche 1) — composition des groupes parlementaires, historique
de votes/amendements, dossiers législatifs (données ouvertes de l'Assemblée Nationale via le projet
Tricoteuses / Parlement Ouvert : assemblee.tricoteuses.fr).

⚠️ Statut vérifié à l'implémentation : l'URL `Config.TRICOTEUSES_GRAPHQL_URL` répond HTTP 200 mais
sert l'application front-end (SPA), pas un endpoint GraphQL JSON — le vrai point d'entrée GraphQL
du projet `tricoteuses-api-assemblee` n'a pas pu être confirmé publiquement lors de l'implémentation
(cf. rapport de vérification). Ce client est donc écrit avec la mécanique GraphQL complète et prêt
à fonctionner dès que l'URL exacte est confirmée/configurée (variable d'env TRICOTEUSES_GRAPHQL_URL),
mais dégrade proprement vers `available=False` tant que ce n'est pas le cas -- jamais d'exception
qui remonterait jusqu'au frontend.
"""

import logging
from typing import Optional

import requests

from ...config import Config
from . import StructuredResult
from ._cache import read_cache, write_cache

logger = logging.getLogger(__name__)

# Requête GraphQL minimale pour récupérer la composition des groupes parlementaires.
# Le schéma exact dépend de la version déployée de tricoteuses-api-assemblee ; à ajuster une fois
# l'endpoint confirmé (voir docstring du module).
GROUPS_QUERY = """
query ParliamentaryGroups {
  organes(type: "GP") {
    uid
    libelle
    libelleAbrege
    nombreMembres
  }
}
"""


def _graphql_request(query: str, variables: Optional[dict] = None) -> dict:
    response = requests.post(
        Config.TRICOTEUSES_GRAPHQL_URL,
        json={"query": query, "variables": variables or {}},
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout=Config.HTTP_CLIENT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        raise ValueError(
            f"Réponse non-JSON reçue de {Config.TRICOTEUSES_GRAPHQL_URL} "
            f"(content-type={content_type}) — l'URL configurée sert probablement le front-end, "
            f"pas l'API GraphQL. Vérifier TRICOTEUSES_GRAPHQL_URL."
        )
    payload = response.json()
    if "errors" in payload:
        raise ValueError(f"Erreurs GraphQL Tricoteuses: {payload['errors']}")
    return payload["data"]


def fetch_parliamentary_groups(force_refresh: bool = False) -> StructuredResult:
    """Composition actuelle des groupes parlementaires (nom, taille). Mise en cache local
    (`tricoteuses_groupes.json`) pour respecter la règle "aucun appel réseau live pendant une démo"
    (CLAUDE.md §2)."""
    cache_filename = "tricoteuses_groupes.json"

    if not force_refresh:
        cached = read_cache(cache_filename)
        if cached is not None:
            return StructuredResult(source="tricoteuses", available=True, data=cached, from_cache=True)

    try:
        data = _graphql_request(GROUPS_QUERY)
        groups = data.get("organes", [])
        write_cache(cache_filename, groups)
        return StructuredResult(source="tricoteuses", available=True, data=groups, from_cache=False)
    except Exception as exc:  # noqa: BLE001 — on ne laisse jamais une erreur réseau remonter brute
        logger.warning("Tricoteuses fetch_parliamentary_groups failed: %s", exc)
        # Dégradation : si un cache existant est disponible même périmé, on le sert plutôt que rien.
        cached = read_cache(cache_filename)
        if cached is not None:
            return StructuredResult(
                source="tricoteuses", available=True, data=cached, from_cache=True,
                metadata={"stale": True, "refresh_error": str(exc)},
            )
        return StructuredResult(source="tricoteuses", available=False, error=str(exc))


def fetch_historical_votes(law_reference: str) -> StructuredResult:
    """Votes réels historiques pour un texte donné, par groupe parlementaire — utilisé uniquement
    par le module de backtesting (CLAUDE.md §2 : jamais affiché comme prédiction, usage interne de
    calibration uniquement)."""
    cache_filename = f"tricoteuses_votes_{law_reference}.json"
    cached = read_cache(cache_filename)
    if cached is not None:
        return StructuredResult(source="tricoteuses", available=True, data=cached, from_cache=True)

    query = """
    query HistoricalVotes($ref: String!) {
      scrutin(reference: $ref) {
        reference
        titre
        decompteParGroupe { groupe { libelleAbrege } position }
      }
    }
    """
    try:
        data = _graphql_request(query, {"ref": law_reference})
        write_cache(cache_filename, data)
        return StructuredResult(source="tricoteuses", available=True, data=data, from_cache=False)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tricoteuses fetch_historical_votes(%s) failed: %s", law_reference, exc)
        return StructuredResult(source="tricoteuses", available=False, error=str(exc))
