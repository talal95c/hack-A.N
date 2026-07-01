"""
Couche persistance MiroPolis (CLAUDE.md §5, infrastructure de production).

Remplace le stockage JSON fichier de MiroFish par une base de données réelle (SQLAlchemy).
En dev/local sans DATABASE_URL configuré vers Postgres, on utilise SQLite -- même code,
même modèles, juste un moteur différent. Voir Config.DATABASE_URL.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from ..config import Config

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        connect_args = {}
        if Config.DATABASE_URL.startswith('sqlite'):
            # Nécessaire pour utiliser SQLite depuis plusieurs threads (Flask + Celery eager)
            connect_args = {'check_same_thread': False}
            # S'assure que le dossier du fichier SQLite existe (ex: backend/uploads/)
            db_path = Config.DATABASE_URL.replace('sqlite:///', '', 1)
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
        _engine = create_engine(Config.DATABASE_URL, connect_args=connect_args, future=True)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = scoped_session(sessionmaker(bind=get_engine(), autoflush=False, autocommit=False))
    return _SessionLocal


def get_session():
    """Retourne une session SQLAlchemy scoped (thread-safe)."""
    return get_session_factory()()


def init_db():
    """Crée les tables si elles n'existent pas (dev/tests). En production, utiliser Alembic."""
    from . import models  # noqa: F401  (enregistre les modèles sur Base.metadata)
    from .models import Base

    Base.metadata.create_all(bind=get_engine())
