"""
Couche 1 (CLAUDE.md) : données réglementaires spatialisées.

Chaque client de ce paquet expose une interface commune pour rester interchangeable
(cf. CLAUDE.md §7) :

    fetch(theme: str, territory: str | None = None) -> StructuredResult

Tous les clients :
- écrivent/lisent un cache local sous Config.TERRITORIAL_CACHE_DIR (jamais d'appel réseau live
  pendant une démo/présentation, cf. CLAUDE.md §2) ;
- ne lèvent jamais d'exception réseau vers l'appelant : en cas d'échec, `available=False` est
  renvoyé avec le détail de l'erreur dans `error`, pour que l'API et le frontend puissent dégrader
  proprement (cf. le champ `openfisca_indicator.available` du contrat d'API).
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class StructuredResult:
    """Résultat structuré et uniforme renvoyé par tous les clients de données réglementaires."""
    source: str
    available: bool
    data: Any = None
    from_cache: bool = False
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "available": self.available,
            "data": self.data,
            "from_cache": self.from_cache,
            "error": self.error,
            "metadata": self.metadata,
        }
