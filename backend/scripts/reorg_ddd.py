#!/usr/bin/env python3
"""Mechanical DDD re-layering: git mv files into shared/application/infrastructure/
interface, then rewrite all internal import paths accordingly.

Run from repo root (bitch-stewie/). Idempotent-ish: designed for a one-shot move
from the pre-reorg layout. After running, `git diff --stat` shows only path
changes plus import-line edits — no logic changes.

USAGE: uv run python scripts/reorg_ddd.py
VERIFY: git status && cd backend && uv run ruff check src tests && uv run pytest tests/test_health.py -q
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # backend/
SRC = ROOT / "src" / "assistant"

# --- Step 1: file moves (source -> destination), all under src/assistant/ ---
# Listed most-specific-first so the mapping reads clearly.
MOVES: list[tuple[str, str]] = [
    # shared kernel
    ("config.py", "shared/config.py"),
    # interface/mcp (the in-process MCP server is an inbound interface)
    ("cc_bridge/memory_mcp.py", "interface/mcp/memory_mcp.py"),
    # infrastructure (external-system adapters)
    ("memory/db.py", "infrastructure/memory/db.py"),
    ("memory/models.py", "infrastructure/memory/models.py"),
    ("memory/sync_db.py", "infrastructure/memory/sync_db.py"),
    ("rag/ingest.py", "infrastructure/rag/ingest.py"),
    ("rag/store.py", "infrastructure/rag/store.py"),
    ("cc_bridge/brief.py", "infrastructure/cc_bridge/brief.py"),
    ("cc_bridge/lifecycle_hooks.py", "infrastructure/cc_bridge/lifecycle_hooks.py"),
    ("cc_bridge/runner.py", "infrastructure/cc_bridge/runner.py"),
    ("cc_bridge/subagents.py", "infrastructure/cc_bridge/subagents.py"),
    ("cc_bridge/worker.py", "infrastructure/cc_bridge/worker.py"),
    ("jobs/queue.py", "infrastructure/jobs/queue.py"),
    ("jobs/watcher.py", "infrastructure/jobs/watcher.py"),
    ("diagrams/likec4.py", "infrastructure/diagrams/likec4.py"),
    ("docs_gen/pandoc.py", "infrastructure/docs_gen/pandoc.py"),
    # application/orchestrator (orchestration internals)
    ("orchestrator/artifact_tools.py", "application/orchestrator/artifact_tools.py"),
    ("orchestrator/context.py", "application/orchestrator/context.py"),
    ("orchestrator/example_tools.py", "application/orchestrator/example_tools.py"),
    ("orchestrator/factory.py", "application/orchestrator/factory.py"),
    ("orchestrator/planner.py", "application/orchestrator/planner.py"),
    ("orchestrator/research_tools.py", "application/orchestrator/research_tools.py"),
    ("orchestrator/tools.py", "application/orchestrator/tools.py"),
    # interface/api
    ("api/app.py", "interface/api/app.py"),
    ("api/chat.py", "interface/api/chat.py"),
    ("api/diagrams.py", "interface/api/diagrams.py"),
    ("api/examples.py", "interface/api/examples.py"),
    ("api/knowledge.py", "interface/api/knowledge.py"),
    ("api/plan.py", "interface/api/plan.py"),
    ("api/research.py", "interface/api/research.py"),
    ("api/routers.py", "interface/api/routers.py"),
    ("api/stats.py", "interface/api/stats.py"),
    ("api/statusline.py", "interface/api/statusline.py"),
    ("api/util.py", "interface/api/util.py"),
    # interface/cli
    ("cli/chat.py", "interface/cli/chat.py"),
    ("cli/main.py", "interface/cli/main.py"),
]

# --- Step 2: import-path rewrite table (old prefix -> new prefix) ---
# Order matters: more-specific prefixes must come before less-specific ones
# so that e.g. cc_bridge/memory_mcp is rewritten before cc_bridge.
IMPORT_REWRITES: list[tuple[str, str]] = [
    # cc_bridge specializations first
    ("assistant.cc_bridge.memory_mcp", "assistant.interface.mcp.memory_mcp"),
    ("assistant.cc_bridge", "assistant.infrastructure.cc_bridge"),
    # single-module shared kernel
    ("assistant.config", "assistant.shared.config"),
    # layers (order among these is independent since prefixes differ)
    ("assistant.api", "assistant.interface.api"),
    ("assistant.cli", "assistant.interface.cli"),
    ("assistant.orchestrator", "assistant.application.orchestrator"),
    ("assistant.memory", "assistant.infrastructure.memory"),
    ("assistant.rag", "assistant.infrastructure.rag"),
    ("assistant.jobs", "assistant.infrastructure.jobs"),
    ("assistant.diagrams", "assistant.infrastructure.diagrams"),
    ("assistant.docs_gen", "assistant.infrastructure.docs_gen"),
]


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=ROOT, check=True)


def move_files() -> None:
    for src_rel, dst_rel in MOVES:
        src = SRC / src_rel
        dst = SRC / dst_rel
        if not src.exists():
            print(f"  SKIP (gone): {src_rel}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "mv", str(src), str(dst)])
        print(f"  mv {src_rel} -> {dst_rel}")


def rewrite_imports() -> None:
    # Collect every .py file under src and tests.
    files: list[Path] = []
    for base in [SRC, ROOT / "tests"]:
        if base.exists():
            files.extend(base.rglob("*.py"))
    for path in files:
        original = path.read_text(encoding="utf-8")
        new = original
        for old, new_prefix in IMPORT_REWRITES:
            # `from <old> import ...`  (word boundary on the module path)
            new = re.sub(
                r"\bfrom " + re.escape(old) + r"\b",
                f"from {new_prefix}",
                new,
            )
            # `import <old>` as a full module
            new = re.sub(
                r"\bimport " + re.escape(old) + r"\b",
                f"import {new_prefix}",
                new,
            )
        if new != original:
            path.write_text(new, encoding="utf-8")
            print(f"  imports: {path.relative_to(ROOT)}")


def main() -> None:
    print("== moving files ==")
    move_files()
    print("== rewriting imports ==")
    rewrite_imports()
    print("== done ==")
    print("Verify with: git status && cd backend && uv run ruff check src tests")


if __name__ == "__main__":
    main()
