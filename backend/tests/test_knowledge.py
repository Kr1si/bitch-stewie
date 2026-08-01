from unittest import mock

from fastapi.testclient import TestClient

from tests.app import make_test_app


def test_list_collections_shape() -> None:
    with TestClient(make_test_app()) as client:
        resp = client.get("/api/knowledge/collections")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


def test_search_returns_results() -> None:
    fake_results = [
        {"source": "doc.md", "kind": "doc", "score": 0.9, "text": "snippet"},
    ]
    with mock.patch(
        "assistant.interface.api.knowledge.hybrid_search",
        return_value=fake_results,
    ), TestClient(make_test_app()) as client:
        resp = client.post("/api/knowledge/search", json={"query": "hello"})
        assert resp.status_code == 200
        assert resp.json() == fake_results


def test_ingest_text_returns_summary() -> None:
    with mock.patch(
        "assistant.interface.api.knowledge.ingest_text",
        return_value=3,
    ), TestClient(make_test_app()) as client:
        resp = client.post(
            "/api/knowledge/ingest-text", json={"text": "hello world", "source": "inline"},
        )
        assert resp.status_code == 200
        assert resp.json()["chunks"] == 3
