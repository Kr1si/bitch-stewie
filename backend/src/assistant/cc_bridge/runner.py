"""Delegation runner: brief -> Claude Code session (on GLM 5.2 via Ollama) -> reviewed result.

Runs on a Proactor-capable event loop (asyncio subprocess support required);
persistence goes through the sync engine so this never touches async psycopg.
"""

import json
import re
import uuid
from dataclasses import dataclass, field

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from assistant.cc_bridge.brief import RESULT_MARKER, Brief
from assistant.cc_bridge.memory_mcp import build_memory_server
from assistant.config import get_settings
from assistant.memory.models import CCRun, CCRunEvent, CCRunStatus
from assistant.memory.sync_db import get_sync_session_factory

REVIEW_PROMPT = (
    "Now review the changes you just made by running the /code-review skill on the current "
    "diff at medium effort. Fix any CONFIRMED findings and commit the fixes. "
    "When finished reply with exactly one line: REVIEW_VERDICT: clean "
    "(no findings or all fixed) or REVIEW_VERDICT: issues (unresolved problems remain, list them)."
)

_VERDICT_RE = re.compile(r"REVIEW_VERDICT:\s*(clean|issues)", re.IGNORECASE)
_RESULT_RE = re.compile(rf"{RESULT_MARKER}:\s*(\{{.*\}})", re.DOTALL)


@dataclass
class DelegationOutcome:
    run_id: uuid.UUID
    status: CCRunStatus
    result: dict = field(default_factory=dict)
    review_iterations: int = 0
    transcript_tail: str = ""


class DelegationRunner:
    def __init__(self, on_event=None):
        self._settings = get_settings()
        self._factory = get_sync_session_factory()
        self._on_event = on_event  # optional callable(str) for live CLI output

    # -- persistence helpers -------------------------------------------------

    def _create_run(self, brief: Brief, project_id) -> uuid.UUID:
        with self._factory() as s:
            run = CCRun(
                project_id=project_id,
                repo_path=brief.repo_path,
                brief=brief.to_prompt(),
                model=self._settings.cc_model,
                status=CCRunStatus.running,
            )
            s.add(run)
            s.commit()
            return run.id

    def _add_event(self, run_id: uuid.UUID, event_type: str, payload: dict) -> None:
        with self._factory() as s:
            s.add(CCRunEvent(run_id=run_id, source="sdk", event_type=event_type, payload=payload))
            s.commit()
        if self._on_event:
            self._on_event(f"[{event_type}] {json.dumps(payload)[:200]}")

    def _finish(self, run_id: uuid.UUID, status: CCRunStatus, result: dict, iterations: int) -> None:
        with self._factory() as s:
            run = s.get(CCRun, run_id)
            run.status = status
            run.result = result
            run.review_iterations = iterations
            s.commit()

    # -- session -------------------------------------------------------------

    def _options(self, brief: Brief, agent_teams: bool = False) -> ClaudeAgentOptions:
        env = {
            "ANTHROPIC_BASE_URL": self._settings.cc_anthropic_base_url,
            "ANTHROPIC_AUTH_TOKEN": "ollama",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        }
        if agent_teams:
            # Experimental: lead session may spawn teammates for parallelizable jobs.
            env["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"
        return ClaudeAgentOptions(
            model=self._settings.cc_model,
            cwd=brief.repo_path,
            # bypassPermissions: the instance works in its own repo checkout and the
            # merge is milestone-gated, so tool prompts would only deadlock headless runs
            # ("dontAsk" denies every tool not pre-allowed).
            permission_mode="bypassPermissions",
            setting_sources=["project"],  # load the target repo's CLAUDE.md, not user config
            env=env,
            mcp_servers={"assistant-memory": build_memory_server()},
        )

    async def _drive(self, client: ClaudeSDKClient, run_id: uuid.UUID, prompt: str) -> str:
        """Send one prompt and collect the response text, persisting events."""
        await client.query(prompt)
        text_parts: list[str] = []
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
                        self._add_event(run_id, "text", {"text": block.text[:2000]})
                    elif isinstance(block, ToolUseBlock):
                        self._add_event(
                            run_id, "tool_use",
                            {"tool": block.name, "input": str(block.input)[:500]},
                        )
            elif isinstance(message, ResultMessage):
                self._add_event(
                    run_id, "result",
                    {"is_error": message.is_error, "num_turns": message.num_turns},
                )
        return "\n".join(text_parts)

    async def run(self, brief: Brief, project_id=None, agent_teams: bool = False) -> DelegationOutcome:
        run_id = self._create_run(brief, project_id)
        iterations = 0
        try:
            async with ClaudeSDKClient(options=self._options(brief, agent_teams)) as client:
                text = await self._drive(client, run_id, brief.to_prompt())

                # review loop (native /code-review inside the same session)
                verdict = "issues"
                for iterations in range(1, self._settings.cc_max_review_iterations + 1):
                    self._finish(run_id, CCRunStatus.reviewing, {}, iterations)
                    review_text = await self._drive(client, run_id, REVIEW_PROMPT)
                    m = _VERDICT_RE.search(review_text)
                    verdict = m.group(1).lower() if m else "issues"
                    if verdict == "clean":
                        break

                result = self._parse_result(text)
                result["review_verdict"] = verdict
                status = CCRunStatus.succeeded if verdict == "clean" else CCRunStatus.failed
                self._finish(run_id, status, result, iterations)
                return DelegationOutcome(
                    run_id=run_id, status=status, result=result,
                    review_iterations=iterations, transcript_tail=text[-1500:],
                )
        except Exception as exc:  # noqa: BLE001 - single failure boundary for the whole run
            self._add_event(run_id, "error", {"error": repr(exc)[:1000]})
            self._finish(run_id, CCRunStatus.failed, {"error": repr(exc)[:1000]}, iterations)
            return DelegationOutcome(run_id=run_id, status=CCRunStatus.failed,
                                     result={"error": repr(exc)})

    async def run_prompt(self, prompt: str, cwd: str, agent_teams: bool = False) -> str:
        """One-shot CC session without the coding review loop (research, analysis)."""
        brief = Brief(goal=prompt, repo_path=cwd)
        run_id = self._create_run(brief, None)
        try:
            async with ClaudeSDKClient(options=self._options(brief, agent_teams)) as client:
                text = await self._drive(client, run_id, prompt)
            self._finish(run_id, CCRunStatus.succeeded, {"kind": "prompt"}, 0)
            return text
        except Exception as exc:  # noqa: BLE001
            self._add_event(run_id, "error", {"error": repr(exc)[:1000]})
            self._finish(run_id, CCRunStatus.failed, {"error": repr(exc)[:1000]}, 0)
            raise

    @staticmethod
    def _parse_result(text: str) -> dict:
        m = _RESULT_RE.search(text)
        if not m:
            return {"structured": False}
        try:
            parsed = json.loads(m.group(1))
            parsed["structured"] = True
            return parsed
        except json.JSONDecodeError:
            return {"structured": False, "raw": m.group(1)[:500]}
