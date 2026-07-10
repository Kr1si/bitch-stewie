"""Native CC lifecycle hooks -> CCRunEvent rows (+ PermissionRequest -> Approval).

The Agent SDK runs these as in-process Python callbacks (no HTTP webhook
round-trip), attached per session via ClaudeAgentOptions(hooks=...). Each
callback persists through the sync engine — same pattern as
DelegationRunner._add_event — so events land in Postgres in near-real-time and
the Runs page no longer depends on the coarse message-stream writes.

PermissionRequest additionally files an Approval row (kind="cc_permission")
before deferring to CC's own permission flow. With permission_mode
"bypassPermissions" this rarely fires for delegated coding runs; it matters for
non-coding delegations run with stricter modes. The LangGraph milestone gate is
unchanged — this is an additional, native channel into the same Approval table.
"""

import logging
import uuid
from typing import Any

from claude_agent_sdk import HookMatcher

from assistant.memory.models import Approval, ApprovalStatus, CCRunEvent
from assistant.memory.sync_db import get_sync_session_factory

logger = logging.getLogger(__name__)


def _persist_event(run_id: uuid.UUID, event_type: str, payload: dict) -> None:
    try:
        with get_sync_session_factory()() as s:
            s.add(CCRunEvent(run_id=run_id, source="hook",
                             event_type=event_type, payload=payload))
            s.commit()
    except Exception as exc:  # noqa: BLE001 - telemetry must never break the session
        logger.warning("hook event persist failed (%s): %r", event_type, exc)


def build_lifecycle_hooks(run_id: uuid.UUID, project_id=None) -> dict[str, list[HookMatcher]]:
    """Hooks dict for ClaudeAgentOptions; closures bind this run's id."""

    async def on_pre_tool(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
        _persist_event(run_id, "pre_tool", {
            "tool": input_data.get("tool_name", "?"),
            "input": str(input_data.get("tool_input", ""))[:500],
            "agent": input_data.get("agent_type", ""),
        })
        return {}

    async def on_post_tool(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
        _persist_event(run_id, "post_tool", {
            "tool": input_data.get("tool_name", "?"),
            "output": str(input_data.get("tool_response", ""))[:500],
            "agent": input_data.get("agent_type", ""),
        })
        return {}

    async def on_subagent_start(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
        _persist_event(run_id, "subagent_start", {
            "agent": input_data.get("agent_type", "?"),
            "agent_id": input_data.get("agent_id", ""),
        })
        return {}

    async def on_subagent_stop(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
        _persist_event(run_id, "subagent_stop", {
            "agent": input_data.get("agent_type", "?"),
            "agent_id": input_data.get("agent_id", ""),
        })
        return {}

    async def on_stop(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
        _persist_event(run_id, "stop", {
            "stop_hook_active": input_data.get("stop_hook_active", False),
        })
        return {}

    async def on_notification(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
        _persist_event(run_id, "notification", {
            "message": str(input_data.get("message", ""))[:500],
            "type": input_data.get("notification_type", ""),
        })
        return {}

    async def on_permission_request(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
        payload = {
            "run_id": str(run_id),
            "tool": input_data.get("tool_name", "?"),
            "input": str(input_data.get("tool_input", ""))[:500],
        }
        _persist_event(run_id, "permission_request", payload)
        try:
            with get_sync_session_factory()() as s:
                # thread_id is NOT NULL (LangGraph resume key); CC-permission
                # mirrors have no thread, so use a synthetic per-request key.
                s.add(Approval(project_id=project_id, kind="cc_permission",
                               thread_id=f"cc-run:{run_id}:{uuid.uuid4().hex[:8]}",
                               payload=payload, status=ApprovalStatus.pending))
                s.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("cc_permission approval persist failed: %r", exc)
        # Defer to CC's own permission flow; we only mirror the request so the
        # UI's approvals list shows what the session asked for.
        return {}

    return {
        "PreToolUse": [HookMatcher(hooks=[on_pre_tool])],
        "PostToolUse": [HookMatcher(hooks=[on_post_tool])],
        "SubagentStart": [HookMatcher(hooks=[on_subagent_start])],
        "SubagentStop": [HookMatcher(hooks=[on_subagent_stop])],
        "Stop": [HookMatcher(hooks=[on_stop])],
        "Notification": [HookMatcher(hooks=[on_notification])],
        "PermissionRequest": [HookMatcher(hooks=[on_permission_request])],
    }