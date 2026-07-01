"""
File de jobs MiroPolis (CLAUDE.md §5 et §7 : "Tâches longues systématiquement en job Celery,
jamais en thread bloquant dans la requête Flask").

En l'absence de REDIS_URL (dev/local), Celery tourne en mode "eager" : les tâches s'exécutent de
façon synchrone dans le process appelant, sans broker. Le code des tâches est identique dans les
deux cas -- c'est uniquement le mode de transport qui change. Voir Config.CELERY_TASK_ALWAYS_EAGER.
"""

from celery import Celery

from .config import Config


def make_celery() -> Celery:
    broker_url = Config.REDIS_URL or 'memory://'
    backend_url = Config.REDIS_URL or 'cache+memory://'

    app = Celery('miropolis', broker=broker_url, backend=backend_url)
    app.conf.update(
        task_always_eager=Config.CELERY_TASK_ALWAYS_EAGER,
        task_eager_propagates=True,  # en mode eager, les exceptions remontent immédiatement (utile pour les tests)
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        timezone='Europe/Paris',
        enable_utc=True,
    )
    return app


celery_app = make_celery()

# Enregistre les modules de tâches (chaque import déclenche les décorateurs @celery_app.task)
from .tasks import (  # noqa: E402,F401
    graph_tasks, simulation_tasks, backtesting_tasks, temporal_tasks, comparison_tasks, map_data_tasks,
)
