import json

from fastapi.testclient import TestClient

import assistant.interface.api.research as research_api
from tests.app import make_test_app


def test_deep_research_stream(monkeypatch) -> None:
    """The /api/research/deep/stream SSE endpoint drives a CC /deep-research run.

    The real CC worker is monkeypatched so the test never starts a Claude Code
    session; it only asserts the SSE event sequence (start -> done) the UI's
    "Deep Research" button consumes (Story 5).
    """
    monkeypatch.setattr(
        research_api, "run_deep_research",
        lambda question, project="": f"# Report\n\nResearch on: {question}",
    )

    with TestClient(make_test_app()) as client, client.stream(
        "POST", "/api/research/deep/stream", json={"goal": "compare A and B"},
    ) as resp:
        assert resp.status_code == 200
        events: dict[str, object] = {}
        for line in resp.iter_lines():
            if line.startswith("event:"):
                events["event"] = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and events.get("event"):
                events["data"] = json.loads(line.split(":", 1)[1].strip())
                if events["event"] in ("done", "error"):
                    break
        assert events["event"] == "done"
        assert "Research on: compare A and B" in events["data"]["report"]  # type: ignore[index]
