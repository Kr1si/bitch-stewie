"""Orchestrator service facade.

Re-exports the deep-agent builder entry points the interface layer needs,
so routers/CLI never import `assistant.application.orchestrator.*` directly.
Kept as a thin seam so the orchestration internals can evolve independently.
"""

from assistant.application.orchestrator.factory import build_orchestrator
from assistant.application.orchestrator.planner import build_planner

__all__ = [
    "build_orchestrator",
    "build_planner",
]
