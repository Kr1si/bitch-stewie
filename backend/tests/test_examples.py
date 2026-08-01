import uuid

from fastapi.testclient import TestClient

from assistant.shared import config
from tests.app import make_test_app


def _examples_enabled(tmp_path, monkeypatch) -> None:
    """Point the examples store at a temp dir (router 500s without it)."""
    monkeypatch.setenv("ASSISTANT_EXAMPLES_PATH", str(tmp_path))
    config.get_settings.cache_clear()


def test_examples_list_empty(monkeypatch, tmp_path) -> None:
    _examples_enabled(tmp_path, monkeypatch)
    with TestClient(make_test_app()) as client:
        assert client.get("/api/examples").status_code == 200


def test_example_upload_download_delete_roundtrip(monkeypatch, tmp_path) -> None:
    _examples_enabled(tmp_path, monkeypatch)
    with TestClient(make_test_app()) as client:
        pid = client.post("/api/projects", json={"name": f"ex-{uuid.uuid4().hex[:8]}"}).json()["id"]
        upload = client.post(
            "/api/examples",
            data={"project_id": pid, "kind": "doc", "note": "ref"},
            files={"file": ("ref.txt", b"reference style content", "text/plain")},
        )
        assert upload.status_code == 200, upload.text
        eid = upload.json()["id"]

        listed = client.get(f"/api/examples?project_id={pid}")
        assert listed.status_code == 200
        assert any(e["id"] == eid for e in listed.json())

        content = client.get(f"/api/examples/{eid}/content")
        assert content.status_code == 200
        assert b"reference style content" in content.content

        deleted = client.delete(f"/api/examples/{eid}")
        assert deleted.status_code == 200


def test_example_missing_on_disk_returns_410(monkeypatch, tmp_path) -> None:
    """A DB row whose file was removed from disk returns 410, not 500 (Story 7)."""
    _examples_enabled(tmp_path, monkeypatch)
    with TestClient(make_test_app()) as client:
        pid = client.post("/api/projects", json={"name": f"ex-{uuid.uuid4().hex[:8]}"}).json()["id"]
        upload = client.post(
            "/api/examples",
            data={"project_id": pid, "kind": "doc", "note": "ref"},
            files={"file": ("gone.txt", b"data", "text/plain")},
        )
        assert upload.status_code == 200, upload.text
        eid = upload.json()["id"]
        # Locate the stored file and remove it; the DB row stays. Missing file on
        # disk must surface as 410, not 500.
        storage = next(tmp_path.rglob("gone.txt"))
        storage.unlink()
        resp = client.get(f"/api/examples/{eid}/content")
        assert resp.status_code == 410
