"""
Tâche Celery pour la construction de graphe (CLAUDE.md §5 & §7 : "Tâches longues systématiquement
en job Celery, jamais en thread bloquant dans la requête Flask").

Le chemin hérité de MiroFish (`GraphBuilderService.build_graph_async`, dans
`app/services/graph_builder.py`) utilise encore un `threading.Thread` brut -- conservé tel quel
pour ne pas casser le pipeline existant pendant la migration progressive (CLAUDE.md §4 : "migration
progressive, pas une réécriture brutale"). Cette tâche Celery est le nouveau chemin recommandé pour
tout code neuf qui déclenche une construction de graphe.
"""

from ..celery_app import celery_app
from ..services.graph_builder import GraphBuilderService


@celery_app.task(name="miropolis.build_graph")
def build_graph_task(
    text: str, ontology: dict, graph_name: str = "MiroPolis Graph",
    chunk_size: int = 500, chunk_overlap: int = 50, batch_size: int = 3, locale: str = "fr",
) -> dict:
    """Construit le graphe de connaissances de façon synchrone dans le worker Celery (au lieu d'un
    thread Flask). Progression toujours suivie via TaskManager (poll frontend inchangé)."""
    service = GraphBuilderService()
    task_id = service.task_manager.create_task(
        task_type="graph_build", metadata={"graph_name": graph_name, "chunk_size": chunk_size}
    )
    service._build_graph_worker(  # noqa: SLF001 — réutilisation intentionnelle de la logique existante
        task_id=task_id, text=text, ontology=ontology, graph_name=graph_name,
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, batch_size=batch_size, locale=locale,
    )
    task = service.task_manager.get_task(task_id)
    return task.to_dict() if task else {"task_id": task_id, "status": "unknown"}
