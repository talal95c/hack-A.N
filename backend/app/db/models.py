"""
Modèles ORM MiroPolis (CLAUDE.md §5 et §6).

Remplace la persistance JSON fichier de MiroFish (backend/app/models/project.py, task.py) par des
modèles SQLAlchemy. Les anciens modèles dataclass restent en place pour ne pas casser le pipeline
MiroFish hérité (graphe/ontologie) le temps de la migration complète -- voir CLAUDE.md §4, colonne
"Évolution": migration progressive, pas une réécriture brutale.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, JSON, Enum, Table, Text, Boolean
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Couche 5 : comptes et permissions
# ---------------------------------------------------------------------------

user_roles = Table(
    'user_roles', Base.metadata,
    Column('user_id', String, ForeignKey('users.id'), primary_key=True),
    Column('role_id', String, ForeignKey('roles.id'), primary_key=True),
)


class Role(Base):
    """Rôle applicatif -- ex: admin, analyst (crée des simulations), publisher (peut publier),
    viewer (lecture seule). Cf. CLAUDE.md §5 "Comptes et permissions"."""
    __tablename__ = 'roles'

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    users = relationship('User', secondary=user_roles, back_populates='roles')


class User(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)

    roles = relationship('Role', secondary=user_roles, back_populates='users')
    projects = relationship('Project', back_populates='owner')


# ---------------------------------------------------------------------------
# Couche 1/2 : Project -> Scenario -> Simulation (remplace ProjectManager/SimulationManager fichier)
# ---------------------------------------------------------------------------

class ProjectStatus(str, PyEnum):
    CREATED = "created"
    ONTOLOGY_GENERATED = "ontology_generated"
    GRAPH_BUILDING = "graph_building"
    GRAPH_COMPLETED = "graph_completed"
    FAILED = "failed"


class Project(Base):
    """Équivalent DB du dataclass Project (backend/app/models/project.py), pour permettre le
    multi-utilisateur et l'indexation -- le pipeline d'ontologie/graphe hérité de MiroFish continue
    à fonctionner à l'identique, seule la persistance change."""
    __tablename__ = 'projects'

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False, default="Unnamed Project")
    status = Column(Enum(ProjectStatus), default=ProjectStatus.CREATED)
    owner_id = Column(String, ForeignKey('users.id'), nullable=True)
    files = Column(JSON, default=list)
    total_text_length = Column(Integer, default=0)
    ontology = Column(JSON, nullable=True)
    analysis_summary = Column(Text, nullable=True)
    graph_id = Column(String, nullable=True)
    simulation_requirement = Column(Text, nullable=True)
    law_topic = Column(String, nullable=True)  # ex: "logement/loyers"
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    owner = relationship('User', back_populates='projects')
    scenarios = relationship('Scenario', back_populates='project', cascade='all, delete-orphan')


class ScenarioStatus(str, PyEnum):
    """État du cycle de vie d'un scénario -- CLAUDE.md §2 & §7 : toute publication externe passe
    par une revue humaine, ce n'est jamais un raccourci automatique."""
    DRAFT = "draft"
    REVIEWED = "reviewed"
    PUBLISHED = "published"


class Scenario(Base):
    """Un scénario = une configuration de simulation pour un projet donné (texte de loi + paramètres
    OpenFisca choisis + mode temporel). Un Project peut avoir plusieurs Scenario (ex: variantes pour
    une comparaison, couche 4)."""
    __tablename__ = 'scenarios'

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey('projects.id'), nullable=False)
    name = Column(String, nullable=False)
    status = Column(Enum(ScenarioStatus), default=ScenarioStatus.DRAFT)
    config = Column(JSON, default=dict)  # paramètres OpenFisca choisis, mode temporel, etc.
    reviewed_by = Column(String, ForeignKey('users.id'), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    published_by = Column(String, ForeignKey('users.id'), nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    project = relationship('Project', back_populates='scenarios')
    simulations = relationship('Simulation', back_populates='scenario', cascade='all, delete-orphan')
    rounds = relationship('Round', back_populates='scenario', cascade='all, delete-orphan')


class SimulationStatus(str, PyEnum):
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Simulation(Base):
    """Équivalent DB de SimulationState (backend/app/services/simulation_manager.py)."""
    __tablename__ = 'simulations'

    id = Column(String, primary_key=True, default=_uuid)
    scenario_id = Column(String, ForeignKey('scenarios.id'), nullable=False)
    graph_id = Column(String, nullable=True)
    status = Column(Enum(SimulationStatus), default=SimulationStatus.CREATED)
    entities_count = Column(Integer, default=0)
    profiles_count = Column(Integer, default=0)
    config_generated = Column(Boolean, default=False)
    run_config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    scenario = relationship('Scenario', back_populates='simulations')


# ---------------------------------------------------------------------------
# Couche 3 : moteur temporel (tendanciel / rétrospectif)
# ---------------------------------------------------------------------------

class TemporalMode(str, PyEnum):
    TENDANCIEL = "tendanciel"
    RETROSPECTIF = "retrospectif"


class Round(Base):
    """Un round du moteur temporel = une période simulée (ex: une année). Cf. CLAUDE.md §3 --
    le moteur s'appuie sur la mémoire temporelle Zep déjà présente dans MiroFish."""
    __tablename__ = 'rounds'

    id = Column(String, primary_key=True, default=_uuid)
    scenario_id = Column(String, ForeignKey('scenarios.id'), nullable=False)
    mode = Column(Enum(TemporalMode), nullable=False)
    round_index = Column(Integer, nullable=False)
    label = Column(String, nullable=True)  # ex: "Année 3"
    indicators = Column(JSON, default=dict)  # {indicator_name: {mean, variance, ci_low, ci_high}}
    narrative = Column(Text, nullable=True)  # section narrative générée par ReportAgent pour ce round
    trajectory_rank = Column(Integer, nullable=True)  # pour le mode rétrospectif : rang de la trajectoire candidate
    created_at = Column(DateTime, default=_now)

    scenario = relationship('Scenario', back_populates='rounds')


# ---------------------------------------------------------------------------
# Couche 4 : comparaison de lois/variantes
# ---------------------------------------------------------------------------

class ComparisonRunStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ComparisonRun(Base):
    __tablename__ = 'comparison_runs'

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    scenario_ids = Column(JSON, default=list)  # liste des Scenario.id comparés (A/B/N)
    status = Column(Enum(ComparisonRunStatus), default=ComparisonRunStatus.PENDING)
    result = Column(JSON, nullable=True)  # écarts d'indicateurs, cartes consolidées, intervalles
    created_at = Column(DateTime, default=_now)
    completed_at = Column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# Couche 2/7 : backtesting (rigueur méthodologique vérifiable)
# ---------------------------------------------------------------------------

class BacktestRun(Base):
    """Rejoue un texte de loi historique à travers le moteur MiroPolis et compare le résultat
    simulé au vote réel -- CLAUDE.md §2 & §7 : la réponse structurelle à la critique de rigueur
    scientifique, pas un simple disclaimer."""
    __tablename__ = 'backtest_runs'

    id = Column(String, primary_key=True, default=_uuid)
    law_reference = Column(String, nullable=False)  # ex: référence Tricoteuses du texte historique
    law_label = Column(String, nullable=True)
    simulated_outcome = Column(JSON, nullable=True)  # positions simulées par groupe
    real_outcome = Column(JSON, nullable=True)  # votes réels par groupe (Tricoteuses)
    agreement_score = Column(Float, nullable=True)  # taux d'accord simulé/réel, 0.0-1.0
    metrics = Column(JSON, nullable=True)  # détail des métriques de calibration
    created_at = Column(DateTime, default=_now)
