import uuid

from fastapi.testclient import TestClient

from tests.app import make_test_app


def test_chat_stream_returns_done(monkeypatch) -> None:
    """Chat SSE endpoint returns text/event-stream and terminates with 'done'.

    The orchestrator graph is the fake from make_test_app (yields nothing), so
    the stream completes with a single done event — exercising the HTTP/SSE
    layer without an LLM (Story 1).
    """
    with TestClient(make_test_app()) as client:
        pid = client.post("/api/projects", json={"name": f"c-{uuid.uuid4().hex[:8]}"}).json()["id"]
        with client.stream(
            "POST", "/api/chat/stream",
            json={"message": "hello", "project_id": pid},
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            events = [line for line in resp.iter_lines() if line.startswith("event:")]
            assert any("done" in e for e in events)


def test_chat_sessions_and_messages() -> None:
    with TestClient(make_test_app()) as client:
        assert client.get("/api/chat/sessions").status_code == 200
        assert client.get(f"/api/chat/sessions/{uuid.uuid4()}/messages").status_code == 200
