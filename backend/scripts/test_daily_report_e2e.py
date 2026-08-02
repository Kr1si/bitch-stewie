"""One-shot e2e: run the daily-report pipeline for the seeded goal.

Needs local Postgres + Qdrant (make infra) and a working Claude Code provider
(ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN). Writes reports to ASSISTANT_REPORTS_PATH.
"""
import asyncio
import os
import sys
from pathlib import Path

# backend/scripts/ -> backend/ -> backend/src/ (where `assistant` lives)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

os.environ.setdefault("ASSISTANT_DATABASE_URL", "postgresql://assistant:assistant@localhost:5433/assistant")
os.environ.setdefault("ASSISTANT_QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("ASSISTANT_REPORTS_PATH", "/tmp/test-reports")
os.makedirs(os.environ["ASSISTANT_REPORTS_PATH"], exist_ok=True)

from assistant.application.services.goal_service import list_goals
from assistant.application.orchestrator.daily_report import run_daily_report


async def main():
    goals = await list_goals()
    g = next((x for x in goals if x.title == "Daily AI Intelligence Report"), None)
    if not g:
        print("SEEDED GOAL NOT FOUND")
        return
    print(f"RUNNING: {g.title} | kind={g.kind.value} | cadence={g.cadence}")
    result = await run_daily_report(g)
    print("RESULT:", result)


if __name__ == "__main__":
    asyncio.run(main())
