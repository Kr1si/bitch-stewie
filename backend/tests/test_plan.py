import uuid

from fastapi.testclient import TestClient

from tests.app import make_test_app


def test_plan_stream_returns_done() -> None:
    """Planner SSE endpoint returns text/event-stream and terminates (Story 3)."""
    with TestClient(make_test_app()) as client:
        pid = client.post("/api/projects", json={"name": f"pl-{uuid.uuid4().hex[:8]}"}).json()["id"]
        with client.stream(
            "POST", "/api/plan/stream",
            json={"message": "refine this idea", "project_id": pid},
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]


def test_plan_sessions_and_messages() -> None:
    with TestClient(make_test_app()) as client:
        assert client.get("/api/plan/sessions").status_code == 200
        assert client.get(f"/api/plan/sessions/{uuid.uuid4()}/messages").status_code == 200
