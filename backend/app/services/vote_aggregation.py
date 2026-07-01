"""
Couche de vote agrégée (CLAUDE.md §3, couche 2) — au-dessus du débat OASIS natif (post/comment/like),
simule une majorité/minorité réelle en respectant le nombre de sièges par groupe parlementaire.

OASIS produit des positions qualitatives par agent-groupe (soutien/opposition/neutre, dérivées des
actions post/comment/like réinterprétées -- cf. CLAUDE.md §1 "poster = amendement, commenter =
contre-argument, liker = soutien"). Ce module transforme ces positions qualitatives en un résultat
de vote agrégé pondéré par les sièges réels (source : tricoteuses_client.fetch_parliamentary_groups).
"""

from dataclasses import dataclass
from enum import Enum


class GroupPosition(str, Enum):
    SUPPORT = "support"
    OPPOSE = "oppose"
    ABSTAIN = "abstain"
    UNDECIDED = "undecided"


@dataclass
class GroupSeats:
    group_name: str
    seats: int
    position: GroupPosition


@dataclass
class VoteOutcome:
    total_seats: int
    support_seats: int
    oppose_seats: int
    abstain_seats: int
    undecided_seats: int
    outcome: str  # "adopted" | "rejected" | "uncertain"
    majority_threshold: int
    by_group: list[dict]

    def to_dict(self) -> dict:
        return {
            "total_seats": self.total_seats,
            "support_seats": self.support_seats,
            "oppose_seats": self.oppose_seats,
            "abstain_seats": self.abstain_seats,
            "undecided_seats": self.undecided_seats,
            "outcome": self.outcome,
            "majority_threshold": self.majority_threshold,
            "by_group": self.by_group,
        }


def aggregate_vote(group_positions: list[GroupSeats]) -> VoteOutcome:
    """Agrège les positions qualitatives par groupe en un résultat de vote pondéré par les sièges.

    Règle de majorité simple (majorité des suffrages exprimés, abstentions non comptées dans le
    dénominateur -- convention proche du fonctionnement réel de l'Assemblée Nationale). En cas de
    part significative de groupes "undecided" (> 15% des sièges), le résultat est marqué
    "uncertain" plutôt que tranché arbitrairement -- cf. CLAUDE.md §2 "aucune incertitude cachée".
    """
    total_seats = sum(g.seats for g in group_positions)
    support = sum(g.seats for g in group_positions if g.position == GroupPosition.SUPPORT)
    oppose = sum(g.seats for g in group_positions if g.position == GroupPosition.OPPOSE)
    abstain = sum(g.seats for g in group_positions if g.position == GroupPosition.ABSTAIN)
    undecided = sum(g.seats for g in group_positions if g.position == GroupPosition.UNDECIDED)

    expressed = support + oppose
    majority_threshold = expressed // 2 + 1 if expressed > 0 else 0

    if total_seats > 0 and undecided / total_seats > 0.15:
        outcome = "uncertain"
    elif expressed == 0:
        outcome = "uncertain"
    elif support >= majority_threshold:
        outcome = "adopted"
    else:
        outcome = "rejected"

    return VoteOutcome(
        total_seats=total_seats,
        support_seats=support,
        oppose_seats=oppose,
        abstain_seats=abstain,
        undecided_seats=undecided,
        outcome=outcome,
        majority_threshold=majority_threshold,
        by_group=[
            {"group_name": g.group_name, "seats": g.seats, "position": g.position.value}
            for g in group_positions
        ],
    )
