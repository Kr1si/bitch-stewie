"""Vault watcher: auto-ingest markdown files when they change."""

from pathlib import Path

from watchfiles import watch

from assistant.config import get_settings
from assistant.rag.ingest import ingest_path

_SUFFIXES = {".md", ".markdown", ".txt", ".rst"}


def watch_vault() -> None:
    """Blocking loop: watch the configured vault and ingest changed files."""
    vault = get_settings().vault_path
    if not vault or not Path(vault).is_dir():
        raise SystemExit("ASSISTANT_VAULT_PATH is not set or not a directory.")
    print(f"Watching vault: {vault}")
    for changes in watch(vault):
        for _change, path in changes:
            if Path(path).suffix.lower() in _SUFFIXES and Path(path).exists():
                result = ingest_path(path)
                print(f"ingested {path}: {result['chunks']} chunk(s)")
