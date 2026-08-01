from fastapi.testclient import TestClient

from tests.app import make_test_app


def test_stats_shape() -> None:
    with TestClient(make_test_app()) as client:
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        for key in ("projects", "kb_points", "kb_sources", "runs_by_status", "recent"):
            assert key in data
