import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "DB", tmp_path / "test.db")
    with TestClient(server.app) as test_client:
        yield test_client


def test_opportunity_match_is_computed_from_profile_skills(client):
    response = client.get("/api/opportunities", params={"skills":"python,SQL"})
    assert response.status_code == 200
    first = next(x for x in response.json() if x["id"] == "p1")
    assert first["matched_skills"] == ["Python", "SQL"]
    assert first["gaps"] == ["Machine Learning"]
    assert first["score"] == 67


def test_unknown_skills_give_zero_match(client):
    response = client.get("/api/opportunities/p1", params={"skills":"Rust"})
    assert response.status_code == 200
    assert response.json()["score"] == 0


def test_pathfinder_translates_intent_and_uses_profile_skills(client):
    response = client.post("/api/pathfinder", json={"message":"is this job a scam?", "language":"ಕನ್ನಡ", "skills":["Python"]})
    assert response.status_code == 200
    body = response.json()
    assert "ಶುಲ್ಕ" in body["reply"]
    assert body["mode"] == "rule-based demo assistant"
    assert "routed_to" not in body


def test_tracker_persists_and_database_connections_close(client):
    added = client.post("/api/applications", json={"opportunity_id":"p1"})
    assert added.status_code == 201
    assert client.get("/api/applications").json()[0]["id"] == "p1"
    assert client.patch("/api/applications/p1", json={"status":"Preparing"}).json()["status"] == "Preparing"
    assert client.delete("/api/applications/p1").json() == {"deleted":True}


def test_reports_can_be_submitted_but_not_read_publicly(client):
    response = client.post("/api/reports", json={"listing_id":"p1", "details":"Employer asks for a registration fee."})
    assert response.status_code == 201
    assert client.get("/api/reports").status_code == 404


def test_project_files_are_not_mounted_as_assets(client):
    assert client.get("/assets/server.py").status_code == 404
    assert client.get("/assets/nammapath.db").status_code == 404
