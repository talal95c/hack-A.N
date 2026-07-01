"""
Client DataCirco (CLAUDE.md §3, couche 1) — données publiques agrégées par circonscription
électorale, fourni par la cellule LexImpact de l'Assemblée Nationale (datacirco.leximpact.an.fr).

⚠️ Statut vérifié à l'implémentation : la disponibilité et le schéma d'une API publique pour
DataCirco n'ont pas pu être confirmés (pas d'endpoint documenté trouvé lors de l'implémentation).
Ce client encapsule néanmoins la mécanique complète (requête + cache + dégradation), pour que
brancher la vraie source ne demande qu'une correction d'URL/parsing, pas une réécriture. Tant que
l'endpoint n'est pas confirmé, `fetch_circonscription_data` renvoie `available=False` de façon
prévisible plutôt que d'échouer bruyamment -- la carte doit alors se replier sur la granularité
région (cf. FranceMap.vue, prop `granularity`, repli automatique déjà prévu côté contrat d'API).
"""

import logging

import requests

from ...config import Config
from . import StructuredResult
from ._cache import read_cache, write_cache

logger = logging.getLogger(__name__)


def fetch_circonscription_data(circo_code: str) -> StructuredResult:
    """Données agrégées pour une circonscription donnée (ex: "75-01"). Retourne
    `available=False` si l'API DataCirco n'est pas jointe/documentée -- la carte doit alors se
    replier sur la granularité région (cf. contrat d'API `/map-data?granularity=region`)."""
    cache_filename = f"datacirco_{circo_code}.json"
    cached = read_cache(cache_filename)
    if cached is not None:
        return StructuredResult(source="datacirco", available=True, data=cached, from_cache=True)

    try:
        response = requests.get(
            f"{Config.DATACIRCO_URL}/api/circonscriptions/{circo_code}",
            timeout=Config.HTTP_CLIENT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        write_cache(cache_filename, payload)
        return StructuredResult(source="datacirco", available=True, data=payload, from_cache=False)
    except Exception as exc:  # noqa: BLE001
        logger.info(
            "DataCirco fetch_circonscription_data(%s) indisponible (%s) -- repli sur granularité "
            "région recommandé côté appelant.", circo_code, exc
        )
        return StructuredResult(source="datacirco", available=False, error=str(exc))
