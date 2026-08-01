import uuid
from unittest import mock

from fastapi.testclient import TestClient

from assistant.infrastructure.cc_bridge.brief import (
    RESULT_MARKER,
    Brief,
    fallback_working_agreement,
)
from tests.app import make_test_app


def test_brief_to_prompt_includes_goal_and_criteria() -> None:
    brief = Brief(
        goal="Add a login page",
        repo_path="/tmp/repo",
        constraints=["no new deps"],
        acceptance_criteria=["redirects after login"],
    )
    prompt = brief.to_prompt()
    assert "# Delegated coding task" in prompt
    assert "## Goal" in prompt
    assert "Add a login page" in prompt
    assert "- no new deps" in prompt
    assert "- redirects after login" in prompt


def test_brief_to_prompt_skills_and_examples() -> None:
    brief = Brief(
        goal="g", repo_path="/r", skills=["delegate-coding-task"], examples=["ref.md"],
    )
    prompt = brief.to_prompt()
    assert "`delegate-coding-task`" in prompt
    assert "ref.md" in prompt


def test_fallback_working_agreement_contains_result_marker() -> None:
    """The inline fallback preserves the delivery contract (Story 2)."""
    agreement = fallback_working_agreement()
    assert RESULT_MARKER in agreement
    assert "branch" in agreement


def test_start_run_enqueues_and_returns_202(monkeypatch) -> None:
    """POST /api/cc-runs enqueues via Procrastinate and returns 202 + job_id.

    delegate_brief.defer() needs the Procrastinate app open (a production
    lifespan concern), so it's mocked here (the worker is what opens it).
    """
    # delegate_brief is imported lazily inside the handler, so patch it at its
    # source (jobs_service) where the name actually lives.
    import assistant.application.services.jobs_service as jobs_service

    fake_brief = mock.Mock(defer=mock.Mock(return_value="job-1"))
    monkeypatch.setattr(jobs_service, "delegate_brief", fake_brief)

    with TestClient(make_test_app()) as client:
        pid = client.post(
            "/api/projects", json={"name": f"del-{uuid.uuid4().hex[:8]}", "repo_path": "/tmp/x"},
        ).json()["id"]
        resp = client.post("/api/cc-runs", json={"goal": "fix bug", "project_id": pid})
        assert resp.status_code == 202, resp.text
        assert resp.json()["job_id"] == "job-1"
