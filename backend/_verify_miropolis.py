"""
Script de vérification MiroPolis -- exécuté une fois pour valider que le backend démarre et que
les nouveaux endpoints répondent correctement. Pas un fichier de production, à supprimer ou
déplacer vers de vrais tests (pytest) dans une itération suivante.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("LLM_API_KEY", "dummy-for-smoke-test")
os.environ.setdefault("ZEP_API_KEY", "dummy-for-smoke-test")
os.environ.setdefault("FLASK_DEBUG", "False")

from app import create_app  # noqa: E402

app = create_app()
client = app.test_client()

print("== /health ==")
r = client.get("/health")
print(r.status_code, r.get_json())
assert r.status_code == 200

print("\n== POST /api/auth/register ==")
r = client.post("/api/auth/register", json={"email": "depute.test@an.fr", "password": "s3cret!", "full_name": "Test AN"})
print(r.status_code, r.get_json())
assert r.status_code == 201

print("\n== POST /api/auth/login ==")
r = client.post("/api/auth/login", json={"email": "depute.test@an.fr", "password": "s3cret!"})
print(r.status_code, r.get_json())
assert r.status_code == 200
token = r.get_json()["access_token"]

print("\n== GET /api/simulation/does-not-exist/map-data ==")
r = client.get("/api/simulation/does-not-exist/map-data")
print(r.status_code, r.get_json())
assert r.status_code == 200
assert r.get_json()["areas"] == []

print("\n== GET /api/simulation/does-not-exist/map-data?granularity=bad ==")
r = client.get("/api/simulation/does-not-exist/map-data?granularity=bad")
print(r.status_code, r.get_json())
assert r.status_code == 400

print("\n== POST /api/backtesting/runs (référence inconnue -> dégradation propre) ==")
r = client.post("/api/backtesting/runs", json={"law_reference": "unknown-ref-123", "simulated_positions": {}})
print(r.status_code, r.get_json())
assert r.status_code == 201
assert r.get_json()["real_outcome_available"] is False

print("\n== POST /api/comparison/runs (2 scénarios factices) ==")
snapshots = [
    {
        "scenario_id": "scenario-a", "scenario_name": "Variante A",
        "areas": [{"code": "84", "name": "ARA", "qualitative_score": 1, "openfisca_indicator": {"available": False}}],
    },
    {
        "scenario_id": "scenario-b", "scenario_name": "Variante B",
        "areas": [{"code": "84", "name": "ARA", "qualitative_score": -1, "openfisca_indicator": {"available": False}}],
    },
]
r = client.post("/api/comparison/runs", json={"name": "Test comparaison", "snapshots": snapshots})
print(r.status_code, r.get_json())
assert r.status_code == 201
run_id = r.get_json()["run_id"]

print("\n== GET /api/comparison/runs/<id> ==")
r = client.get(f"/api/comparison/runs/{run_id}")
print(r.status_code, r.get_json())
assert r.status_code == 200

print("\n== POST /api/scenarios/<id>/publish sans revue préalable (doit être refusé) ==")
from app.db import get_session
from app.db.models import Project, Scenario

session = get_session()
project = Project(name="Projet test", law_topic="logement")
session.add(project)
session.commit()
scenario = Scenario(project_id=project.id, name="Scénario test")
session.add(scenario)
session.commit()
scenario_id = scenario.id
session.close()

r = client.post(f"/api/scenarios/{scenario_id}/publish", headers={"Authorization": f"Bearer {token}"})
print(r.status_code, r.get_json())
assert r.status_code == 409

print("\n== POST /api/scenarios/<id>/review puis publish (doit réussir) ==")
r = client.post(f"/api/scenarios/{scenario_id}/review", headers={"Authorization": f"Bearer {token}"})
print(r.status_code, r.get_json())
assert r.status_code == 200

r = client.post(f"/api/scenarios/{scenario_id}/publish", headers={"Authorization": f"Bearer {token}"})
print(r.status_code, r.get_json())
assert r.status_code == 200
assert r.get_json()["status"] == "published"

print("\nTOUT EST OK")
