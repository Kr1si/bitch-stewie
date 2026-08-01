import uuid

from fastapi.testclient import TestClient

from tests.app import make_test_app


def test_list_runs_empty() -> None:
    with TestClient(make_test_app()) as client:
        resp = client.get("/api/cc-runs")
        assert resp.status_code == 200
        assert resp.json() == []


def test_run_events_empty() -> None:
    with TestClient(make_test_app()) as client:
        resp = client.get(f"/api/cc-runs/{uuid.uuid4()}/events")
        assert resp.status_code == 200
        assert resp.json() == []


def test_statusline_missing_run_returns_404() -> None:
    with TestClient(make_test_app()) as client:
        resp = client.get(f"/api/runs/{uuid.uuid4()}/statusline")
        assert resp.status_code == 404
