import uuid

from fastapi.testclient import TestClient

from tests.app import make_test_app


def test_statusline_missing_run_returns_404() -> None:
    with TestClient(make_test_app()) as client:
        assert client.get(f"/api/runs/{uuid.uuid4()}/statusline").status_code == 404
