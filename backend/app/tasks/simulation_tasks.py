"""
Tâche Celery pour la préparation de simulation (couche vote/archétypes, CLAUDE.md §5).

⚠️ Note d'environnement importante, vérifiée à l'implémentation : le moteur de simulation OASIS
sous-jacent dépend du paquet `camel-oasis`, dont la distribution publiée ne s'installe pas sous
Python 3.12 (`pip install camel-oasis==0.2.5` échoue : aucune distribution compatible trouvée).
C'est une contrainte héritée de MiroFish lui-même (le README l'annonce "Python ≥3.11, ≤3.12" mais
le paquet publié restreint en réalité à <3.12) -- pas une limitation introduite par MiroPolis.
Cette tâche orchestre donc tout ce qui NE dépend PAS directement de camel-oasis (préparation des
archétypes/population synthétique, couche de vote), et documente clairement l'endroit où le
sous-processus OASIS doit être invoqué (`SimulationRunner.start_simulation`, inchangé) pour les
environnements de déploiement qui utiliseront Python 3.11.
"""

from ..celery_app import celery_app
from ..services.vote_aggregation import GroupPosition, GroupSeats, aggregate_vote


@celery_app.task(name="miropolis.aggregate_vote")
def aggregate_vote_task(group_positions: list[dict]) -> dict:
    """Agrège les positions de groupes (issues du débat OASIS une fois celui-ci exécuté, cf. note
    d'environnement ci-dessus) en un résultat de vote pondéré par les sièges réels."""
    typed = [
        GroupSeats(group_name=g["group_name"], seats=g["seats"], position=GroupPosition(g["position"]))
        for g in group_positions
    ]
    outcome = aggregate_vote(typed)
    return outcome.to_dict()
