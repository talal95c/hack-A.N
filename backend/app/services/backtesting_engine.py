"""
Module de backtesting (CLAUDE.md §2 & §7) : rejoue un texte de loi historique à travers le moteur
MiroPolis (positions simulées par groupe) et les compare aux votes réels (Tricoteuses), pour publier
des métriques de calibration transparentes -- la réponse structurelle à la critique de rigueur
scientifique, pas un simple disclaimer.
"""

import logging
from dataclasses import dataclass

from .regulatory_data import tricoteuses_client
from .vote_aggregation import GroupPosition

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    law_reference: str
    agreement_score: float  # 0.0 - 1.0 : proportion de groupes dont la position simulée == réelle
    per_group_agreement: list[dict]
    real_outcome_available: bool
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "law_reference": self.law_reference,
            "agreement_score": self.agreement_score,
            "per_group_agreement": self.per_group_agreement,
            "real_outcome_available": self.real_outcome_available,
            "error": self.error,
        }


def _normalize_position(raw_position: str) -> str:
    """Normalise les libellés de position (source Tricoteuses vs sortie MiroPolis) vers
    support/oppose/abstain pour permettre la comparaison."""
    raw = (raw_position or "").strip().lower()
    if raw in ("pour", "support", "adopte", "adopté"):
        return GroupPosition.SUPPORT.value
    if raw in ("contre", "oppose", "opposé", "rejette", "rejeté"):
        return GroupPosition.OPPOSE.value
    if raw in ("abstention", "abstain"):
        return GroupPosition.ABSTAIN.value
    return GroupPosition.UNDECIDED.value


def run_backtest(law_reference: str, simulated_positions: dict[str, str]) -> BacktestResult:
    """Compare les positions simulées (dict {group_name: position}) au vote réel historique du
    texte identifié par `law_reference` (référence Tricoteuses).

    `simulated_positions` doit provenir d'un run MiroPolis complet sur le texte historique rejoué
    (même pipeline que pour un texte nouveau -- c'est tout l'intérêt du backtesting : mêmes
    conditions, résultat connu à l'avance pour validation).
    """
    real_votes = tricoteuses_client.fetch_historical_votes(law_reference)

    if not real_votes.available:
        return BacktestResult(
            law_reference=law_reference,
            agreement_score=0.0,
            per_group_agreement=[],
            real_outcome_available=False,
            error=f"Vote réel indisponible: {real_votes.error}",
        )

    real_by_group: dict[str, str] = {}
    try:
        decompte = real_votes.data.get("scrutin", {}).get("decompteParGroupe", [])
        for entry in decompte:
            group_name = entry.get("groupe", {}).get("libelleAbrege", "?")
            real_by_group[group_name] = _normalize_position(entry.get("position", ""))
    except (AttributeError, KeyError, TypeError) as exc:
        logger.warning("Format de vote réel Tricoteuses inattendu pour %s: %s", law_reference, exc)
        return BacktestResult(
            law_reference=law_reference, agreement_score=0.0, per_group_agreement=[],
            real_outcome_available=False, error=f"Format de vote réel inattendu: {exc}",
        )

    per_group = []
    matches = 0
    compared = 0
    for group_name, real_position in real_by_group.items():
        simulated = _normalize_position(simulated_positions.get(group_name, ""))
        if group_name not in simulated_positions:
            per_group.append({"group_name": group_name, "real": real_position, "simulated": None, "match": None})
            continue
        compared += 1
        match = simulated == real_position
        matches += int(match)
        per_group.append({"group_name": group_name, "real": real_position, "simulated": simulated, "match": match})

    agreement_score = (matches / compared) if compared > 0 else 0.0

    return BacktestResult(
        law_reference=law_reference,
        agreement_score=agreement_score,
        per_group_agreement=per_group,
        real_outcome_available=True,
    )


def persist_backtest_run(result: BacktestResult, law_label: str | None = None) -> str:
    """Enregistre le résultat dans la table BacktestRun (couche 7 : tableau de bord de
    transparence). Retourne l'id créé."""
    from ..db import get_session
    from ..db.models import BacktestRun

    session = get_session()
    try:
        run = BacktestRun(
            law_reference=result.law_reference,
            law_label=law_label,
            simulated_outcome={g["group_name"]: g["simulated"] for g in result.per_group_agreement},
            real_outcome={g["group_name"]: g["real"] for g in result.per_group_agreement},
            agreement_score=result.agreement_score,
            metrics=result.to_dict(),
        )
        session.add(run)
        session.commit()
        return run.id
    finally:
        session.close()
