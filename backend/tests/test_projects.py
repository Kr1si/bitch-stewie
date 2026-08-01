import uuid

from fastapi.testclient import TestClient

from tests.app import make_test_app


def test_project_create_list_roundtrip() -> None:
    with TestClient(make_test_app()) as client:
        name = f"proj-{uuid.uuid4().hex[:8]}"
        created = client.post(
            "/api/projects", json={"name": name, "description": "d", "repo_path": "/tmp/x"},
        )
        assert created.status_code == 201
        body = created.json()
        assert body["name"] == name
        assert "id" in body

        listed = client.get("/api/projects")
        assert listed.status_code == 200
        assert any(p["name"] == name for p in listed.json())


def test_project_duplicate_returns_409() -> None:
    with TestClient(make_test_app()) as client:
        name = f"dup-{uuid.uuid4().hex[:8]}"
        assert client.post("/api/projects", json={"name": name}).status_code == 201
        dup = client.post("/api/projects", json={"name": name})
        assert dup.status_code == 409


def test_list_decisions_empty() -> None:
    with TestClient(make_test_app()) as client:
        pid = client.post("/api/projects", json={"name": f"d-{uuid.uuid4().hex[:8]}"}).json()["id"]
        resp = client.get(f"/api/projects/{pid}/decisions")
        assert resp.status_code == 200
        assert resp.json() == []


def test_list_approvals_and_status_filter() -> None:
    with TestClient(make_test_app()) as client:
        assert client.get("/api/approvals").status_code == 200
        filtered = client.get("/api/approvals?status=pending")
        assert filtered.status_code == 200
        assert filtered.json() == []
