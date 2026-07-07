"""Dedicated worker thread for Claude Code sessions.

The Agent SDK needs asyncio subprocess support (Proactor loop on Windows),
while the rest of the backend runs on a Selector loop for async psycopg.
This worker owns a Proactor loop in its own thread; any caller (orchestrator
tool, API handler, CLI) submits briefs and blocks for the outcome.
"""

import asyncio
import sys
import threading

from assistant.cc_bridge.brief import Brief
from assistant.cc_bridge.runner import DelegationOutcome, DelegationRunner

_lock = threading.Lock()
_worker: "CCWorker | None" = None


class CCWorker:
    def __init__(self) -> None:
        if sys.platform == "win32":
            self._loop = asyncio.ProactorEventLoop()
        else:
            self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name="cc-worker", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def delegate(self, brief: Brief, project_id=None, agent_teams: bool = False,
                 timeout: float = 3600) -> DelegationOutcome:
        """Run a delegation on the worker loop; blocks the calling thread."""
        runner = DelegationRunner()
        future = asyncio.run_coroutine_threadsafe(
            runner.run(brief, project_id=project_id, agent_teams=agent_teams), self._loop
        )
        return future.result(timeout=timeout)


    def run_prompt(self, prompt: str, cwd: str, timeout: float = 1800) -> str:
        """One-shot CC session (e.g. /deep-research); blocks the calling thread."""
        runner = DelegationRunner()
        future = asyncio.run_coroutine_threadsafe(runner.run_prompt(prompt, cwd), self._loop)
        return future.result(timeout=timeout)


def get_worker() -> CCWorker:
    global _worker
    with _lock:
        if _worker is None:
            _worker = CCWorker()
        return _worker
