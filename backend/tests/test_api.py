import uuid

from fastapi.testclient import TestClient

from assistant.api.app import create_app


def test_projects_api_roundtrip() -> None:
    with TestClient(create_app()) as client:
        name = f"api-test-{uuid.uuid4().hex[:8]}"
        created = client.post("/api/projects", json={"name": name, "description": "t"})
        assert created.status_code == 201
        listed = client.get("/api/projects")
        assert listed.status_code == 200
        assert any(p["name"] == name for p in listed.json())
        dup = client.post("/api/projects", json={"name": name})
        assert dup.status_code == 409


def test_runs_and_approvals_endpoints() -> None:
    with TestClient(create_app()) as client:
        assert client.get("/api/cc-runs").status_code == 200
        assert client.get("/api/approvals").status_code == 200
