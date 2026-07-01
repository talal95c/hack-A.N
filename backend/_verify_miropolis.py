"""
Script de vérification MiroPolis v2 ("MiroFish v2") -- vérifie que le backend démarre avec le
stockage fichier simple (pas de DB/Celery/Auth), que les sources de données réelles fonctionnent,
et que les nouveaux endpoints de l'agent de scénario répondent. Pas un fichier de production.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("LLM_API_KEY", "dummy-for-smoke-test")
os.environ.setdefault("ZEP_API_KEY", "dummy-for-smoke-test")
os.environ.setdefault("FLASK_DEBUG", "False")

print("== Sources de données réelles ==")
from app.services.regulatory_data import tricoteuses_client
groups = tricoteuses_client.fetch_parliamentary_groups()
print("groupes parlementaires:", groups.available, "n=", len(groups.data) if groups.data else 0)
assert groups.available
assert sum(g["nombreMembres"] for g in groups.data) > 500  # ~577 sièges réels

from app.services.population_synthesizer import Dimension, synthesize_population
dims = [Dimension("csp", ["Cadre", "Employe", "Ouvrier", "Retraite"], [20, 30, 20, 30])]
agents = synthesize_population(dims, n_agents=20)
print("archétypes citoyens synthétiques:", len(agents), "somme poids=", sum(a.demographic_weight for a in agents))
assert len(agents) == 20
assert abs(sum(a.demographic_weight for a in agents) - 1.0) < 1e-6

from app.services.vote_aggregation import GroupPosition, GroupSeats, aggregate_vote
outcome = aggregate_vote([
    GroupSeats("A", 300, GroupPosition.SUPPORT),
    GroupSeats("B", 277, GroupPosition.OPPOSE),
])
print("agrégation de vote:", outcome.outcome)
assert outcome.outcome == "adopted"

print("\n== Démarrage Flask (sans DB/Celery/Auth) ==")
from app import create_app
app = create_app()
client = app.test_client()

r = client.get("/health")
print("/health:", r.status_code, r.get_json())
assert r.status_code == 200

print("\n== Endpoints agent de scénario (dégradation propre sans clé LLM réelle) ==")
r = client.post("/api/scenario/generate", json={"simulation_id": "does-not-exist"})
print("/api/scenario/generate (simulation inconnue):", r.status_code, r.get_json())
assert r.status_code == 404

r = client.get("/api/scenario/does-not-exist")
print("/api/scenario/<id> (inconnu):", r.status_code)
assert r.status_code == 404

print("\nTOUT EST OK")
