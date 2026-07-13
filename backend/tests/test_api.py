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


def test_deep_research_stream(monkeypatch) -> None:
    """The /api/research/deep/stream SSE endpoint drives a CC /deep-research run.

    The real CC worker is monkeypatched so the test never starts a Claude Code
    session or touches Qdrant; it only asserts the SSE event sequence
    (start -> done) the web UI's "Deep Research" button consumes.
    """
    import json as _json

    import assistant.api.research as research_api

    monkeypatch.setattr(
        research_api, "run_deep_research",
        lambda question, project="": f"# Report\n\nResearch on: {question}",
    )

    with TestClient(create_app()) as client:
        with client.stream("POST", "/api/research/deep/stream",
                           json={"goal": "compare A and B"}) as resp:
            assert resp.status_code == 200
            events: dict[str, object] = {}
            for line in resp.iter_lines():
                if line.startswith("event:"):
                    events["event"] = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and events.get("event"):
                    events["data"] = _json.loads(line.split(":", 1)[1].strip())
                    if events["event"] in ("done", "error"):
                        break
            assert events["event"] == "done"
            assert "Research on: compare A and B" in events["data"]["report"]  # type: ignore[index]
