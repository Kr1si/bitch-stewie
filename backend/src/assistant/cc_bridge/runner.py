"""Delegation runner: brief -> Claude Code session (on GLM 5.2 via Ollama) -> reviewed result.

Runs on a Proactor-capable event loop (asyncio subprocess support required);
persistence goes through the sync engine so this never touches async psycopg.
"""

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    SdkPluginConfig,
    TextBlock,
    ToolUseBlock,
)

from assistant.cc_bridge.brief import RESULT_MARKER, Brief, fallback_working_agreement
from assistant.cc_bridge.lifecycle_hooks import build_lifecycle_hooks
from assistant.cc_bridge.memory_mcp import build_memory_server
from assistant.cc_bridge.subagents import build_subagents
from assistant.config import get_settings
from assistant.memory.models import CCRun, CCRunEvent, CCRunStatus
from assistant.memory.sync_db import get_sync_session_factory

REVIEW_PROMPT = (
    "Now review the changes you just made by running the /code-review skill on the current "
    "diff at medium effort. Fix any CONFIRMED findings and commit the fixes. "
    "When finished reply with exactly one line: REVIEW_VERDICT: clean "
    "(no findings or all fixed) or REVIEW_VERDICT: issues (unresolved problems remain, list them)."
)

logger = logging.getLogger(__name__)

_VERDICT_RE = re.compile(r"REVIEW_VERDICT:\s*(clean|issues)", re.IGNORECASE)
_RESULT_RE = re.compile(rf"{RESULT_MARKER}:\s*(\{{.*\}})", re.DOTALL)

# Repo-local CC assets shipped with the backend (skills, output styles,
# managed settings). Resolved once; existence is checked at staging time
# so a moved/missing asset degrades gracefully instead of failing the run.
# skills/delegate holds DELEGATE-facing skills (working agreement etc.);
# skills/orchestrator is the LangGraph agent's own skill set — never staged.
_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_DELEGATE_SKILLS_DIR = _BACKEND_ROOT / "skills" / "delegate"
_MANAGED_SETTINGS_DIR = _BACKEND_ROOT / ".claude" / "managed-settings"
_OUTPUT_STYLES_DIR = _BACKEND_ROOT / ".claude" / "output-styles"


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

    @staticmethod
    def _stage_skills(brief: Brief) -> list[str]:
        """Copy delegate skills into the target repo's .claude/skills; return staged names.

        The SDK's `skills=` takes skill NAMES resolved from setting sources —
        with setting_sources=["project"] that means the target repo's
        .claude/skills/. Staging the files there is what makes the name
        resolvable; a failed copy (read-only repo) drops the name so the
        caller falls back to the inline working agreement.
        """
        names = dict.fromkeys(["delegate-coding-task", *brief.skills])  # dedupe, keep order
        staged: list[str] = []
        for name in names:
            src = _DELEGATE_SKILLS_DIR / name / "SKILL.md"
            if not src.is_file():
                continue
            try:
                dest_dir = Path(brief.repo_path) / ".claude" / "skills" / name
                dest_dir.mkdir(parents=True, exist_ok=True)
                (dest_dir / "SKILL.md").write_text(
                    src.read_text(encoding="utf-8"), encoding="utf-8")
                staged.append(name)
            except OSError as exc:
                logger.warning("skill staging failed for %s: %r", name, exc)
        return staged

    @staticmethod
    def _stage_output_style(brief: Brief) -> str | None:
        """Stage the output style into the target repo; return the settings path.

        outputStyle is a setting, not a ClaudeAgentOptions field, and the style
        *file* must be resolvable from the session's cwd — so the style .md is
        copied into the target repo's .claude/output-styles. Only overwrites a
        file we previously staged (never a user's own same-named style).
        """
        if not brief.output_style:
            return None
        candidate = _MANAGED_SETTINGS_DIR / f"{brief.output_style}.json"
        style_src = _OUTPUT_STYLES_DIR / f"{brief.output_style}.md"
        if not (candidate.is_file() and style_src.is_file()):
            return None
        try:
            dest_dir = Path(brief.repo_path) / ".claude" / "output-styles"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / style_src.name
            src_text = style_src.read_text(encoding="utf-8")
            if dest.is_file() and dest.read_text(encoding="utf-8") != src_text:
                logger.warning(
                    "not overwriting user output style %s; running without style", dest)
                return None
            dest.write_text(src_text, encoding="utf-8")
            return str(candidate)
        except OSError as exc:
            logger.warning("output-style staging failed: %r", exc)
            return None  # read-only repo: run without the style

    def _plugins(self) -> list[SdkPluginConfig]:
        """Local plugins for delegated sessions (ecc, frontend-design, ...).

        setting_sources=["project"] excludes user-scope config, so plugins
        installed via `claude plugin install` would never load — they must be
        passed explicitly. cc_plugins_dir subdirs with a plugin manifest are
        provisioned into the image by cc-setup.sh.
        """
        root = self._settings.cc_plugins_dir
        if not root:
            return []
        base = Path(root)
        if not base.is_dir():
            logger.warning("cc_plugins_dir %s does not exist; running without plugins", root)
            return []
        return [
            SdkPluginConfig(type="local", path=str(p))
            for p in sorted(base.iterdir())
            if (p / ".claude-plugin" / "plugin.json").is_file()
        ]

    def _options(
        self,
        brief: Brief,
        run_id: uuid.UUID,
        skill_names: list[str],
        project_id=None,
        agent_teams: bool = False,
    ) -> ClaudeAgentOptions:
        env = {
            "ANTHROPIC_BASE_URL": self._settings.cc_anthropic_base_url,
            "ANTHROPIC_AUTH_TOKEN": self._settings.cc_anthropic_auth_token,
            "API_TIMEOUT_MS": self._settings.cc_api_timeout_ms,
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
            settings=self._stage_output_style(brief),
            env=env,
            mcp_servers={"assistant-memory": build_memory_server()},
            plugins=self._plugins(),
            agents=build_subagents(),
            skills=skill_names or None,  # NAMES, staged into the target repo
            hooks=build_lifecycle_hooks(run_id, project_id=project_id),
        )

    @staticmethod
    def _prompt_for(brief: Brief, skill_names: list[str]) -> str:
        """Brief prompt; appends the inline working agreement only when the
        delegate-coding-task skill could not be staged into the target repo."""
        prompt = brief.to_prompt()
        if "delegate-coding-task" not in skill_names:
            prompt += "\n" + fallback_working_agreement()
        return prompt

    async def _drive(self, client: ClaudeSDKClient, run_id: uuid.UUID, prompt: str) -> str:
        """Send one prompt and collect the response text, persisting events.

        Tool/lifecycle events are persisted by the native lifecycle hooks
        (source="hook"); the message loop only records assistant text (tokens
        aren't visible to hooks) and the final result marker.
        """
        await client.query(prompt)
        text_parts: list[str] = []
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
                        self._add_event(run_id, "text", {"text": block.text[:2000]})
                    elif isinstance(block, ToolUseBlock) and self._on_event:
                        self._on_event(f"[tool] {block.name}")
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
            skill_names = self._stage_skills(brief)
            options = self._options(brief, run_id, skill_names, project_id, agent_teams)
            async with ClaudeSDKClient(options=options) as client:
                text = await self._drive(client, run_id, self._prompt_for(brief, skill_names))

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

    async def run_prompt(
        self, prompt: str, cwd: str, agent_teams: bool = False, output_style: str = ""
    ) -> str:
        """One-shot CC session without the coding review loop (research, analysis)."""
        brief = Brief(goal=prompt, repo_path=cwd, output_style=output_style)
        run_id = self._create_run(brief, None)
        try:
            # no skill staging: research one-shots need no coding contract and
            # shouldn't write .claude/skills into arbitrary working dirs
            options = self._options(brief, run_id, [], None, agent_teams)
            async with ClaudeSDKClient(options=options) as client:
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