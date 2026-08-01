import uuid

from fastapi.testclient import TestClient

from tests.app import make_test_app


def test_list_diagrams_empty() -> None:
    with TestClient(make_test_app()) as client:
        pid = client.post(
            "/api/projects", json={"name": f"dg-{uuid.uuid4().hex[:8]}", "repo_path": "/tmp/repo"},
        ).json()["id"]
        resp = client.get(f"/api/projects/{pid}/diagrams")
        assert resp.status_code == 200
        assert resp.json() == []


def test_diagram_path_traversal_is_rejected() -> None:
    """A traversal attempt must never escape the diagrams dir (Story 6)."""
    with TestClient(make_test_app()) as client:
        pid = client.post(
            "/api/projects", json={"name": f"dg-{uuid.uuid4().hex[:8]}", "repo_path": "/tmp/repo"},
        ).json()["id"]
        for bad in ("../../etc/passwd", "..\\..\\etc\\passwd", "/etc/passwd"):
            resp = client.get(f"/api/projects/{pid}/diagrams/{bad}")
            assert resp.status_code in (400, 404), f"{bad!r} -> {resp.status_code}"
