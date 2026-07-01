"""Utilitaire de cache local partagé par les clients de la couche 1 (CLAUDE.md §6, convention de
nommage des fichiers de cache : `<source>_<theme>.json`)."""

import json
import os
from typing import Any, Optional

from ...config import Config


def _cache_path(filename: str) -> str:
    os.makedirs(Config.TERRITORIAL_CACHE_DIR, exist_ok=True)
    return os.path.join(Config.TERRITORIAL_CACHE_DIR, filename)


def read_cache(filename: str) -> Optional[Any]:
    path = _cache_path(filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def write_cache(filename: str, data: Any) -> None:
    path = _cache_path(filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
