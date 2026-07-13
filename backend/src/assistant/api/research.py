"""Deep research endpoints: a direct Claude Code /deep-research one-shot.

Unlike the chat flow (where the orchestrator decides when to call the
``deep_research`` tool), these endpoints are driven explicitly by the web UI's
"Deep Research" button: the user gives a goal and gets back a cited Markdown
report produced through Claude Code. The report is ingested into the knowledge
base so later questions can reuse it.
"""

import asyncio
import json

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from assistant.orchestrator.research_tools import run_deep_research

router = APIRouter(prefix="/api/research")


class DeepResearchIn(BaseModel):
    goal: str = Field(..., min_length=1, description="The research question / goal.")
    project: str = ""


@router.post("/deep/stream")
async def deep_research_stream(body: DeepResearchIn):
    """Run /deep-research via Claude Code and stream the outcome as SSE.

    The CC worker blocks the calling thread for minutes, so the actual research
    runs on a threadpool via ``asyncio.to_thread`` to keep the event loop free.

    Events:
      - ``start``  {goal}        -- research has begun
      - ``done``   {report}      -- finished, full Markdown report
      - ``error``  {error}       -- research failed
    """

    async def event_gen():
        yield {"event": "start", "data": json.dumps({"goal": body.goal})}
        try:
            report = await asyncio.to_thread(run_deep_research, body.goal, body.project)
            yield {"event": "done",
                   "data": json.dumps({"report": report})}
        except Exception as exc:  # noqa: BLE001 - surface failure to the UI
            yield {"event": "error", "data": json.dumps({"error": str(exc)})}

    return EventSourceResponse(event_gen())