"""Goal-creator graph: a SEPARATE top-level LangGraph graph for authoring goals.

This is NOT the orchestrator. The orchestrator is the async execution worker;
this graph is the interview flow that defines a goal before the orchestrator
ever sees it. Clean separation of concerns.

Flow:
  START -> clarify -> (END : persist)
                     ^        |
                     |        v
                     +----- END (after persist)

The ``clarify`` node is an LLM-driven interviewer. Each turn it reads the
accumulated conversation + in-progress goal, then either:
  (a) asks 1-2 clarifying questions (routes to END so the UI can collect the
      user's answer and re-invoke on the same thread_id), or
  (b) decides the goal is complete enough -> routes to ``persist``.

No ``interrupt()``/``Command(resume)``: the loop is the standard invoke ->
stream -> done pattern. The FE appends the user's answer to messages and
re-invokes on the same thread_id; the checkpointer restores GoalState with the
reducer-accumulated messages.
"""

import json
import re
import uuid
from pathlib import Path
from typing import Annotated, Any, Literal

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from assistant.application.services.goal_service import create_goal_entity
from assistant.shared.config import get_settings

# Goal JSON the clarify node emits when it decides the goal is ready.
_GOAL_JSON_RE = re.compile(r"\[\[GOAL_JSON\]\](.*?)\[\[/GOAL_JSON\]\]", re.DOTALL)


class GoalState(TypedDict):
    messages: Annotated[list, add_messages]
    goal: dict
    status: Literal["interviewing", "confirmed"]
    kind: str | None


def _skill_system_prompt() -> str:
    """Load the goal-creation skill as the clarify node's system playbook."""
    skill_path = Path(__file__).resolve().parents[3] / "skills" / "goal-creation" / "SKILL.md"
    try:
        return skill_path.read_text(encoding="utf-8")
    except OSError:
        return (
            "You are a goal-creation interviewer. Help the user define a Goal "
            "(research / coding / testing) by asking 1-2 focused questions at a "
            "time. When you have title, kind, cadence, project, and the "
            "kind-specific config, emit the goal as "
            "[[GOAL_JSON]]{\"title\":...,\"kind\":...,\"cadence\":...,"
            "\"description\":...,\"project_id\":...,\"config\":{...}}[[/GOAL_JSON]]."
        )


def _model():  # noqa: ANN202 — lazy import; return type is BaseChatModel
    # LongCat needs Bearer auth — reuse the orchestrator's auth-aware builder
    # (a bare init_chat_model would send x-api-key, which LongCat rejects).
    from assistant.application.orchestrator.factory import _build_chat_model
    return _build_chat_model(get_settings())


async def clarify_node(state: GoalState, config: RunnableConfig) -> dict:
    """Interview agent: ask questions or signal the goal is ready.

    Streams its questions as AIMessage tokens (via the graph-level astream).
    If the agent's own response carries a [[GOAL_JSON]] signal, parse it and
    return the goal as a state update so ``persist_node`` receives it (a
    router's mutations would NOT reach the next node).
    """
    model = _model()

    project_id = (config or {}).get("configurable", {}).get("project_id")
    context = (f"\nThe project_id for this goal is {project_id} (already fixed; "
               "do not ask for it)." if project_id else "")

    system = SystemMessage(content=_skill_system_prompt() + context)
    messages = [system, *state["messages"]]

    response = await model.ainvoke(messages)
    content = getattr(response, "content", "") or ""

    # Parse any goal the agent emitted so it survives as a real state update.
    goal = dict(state.get("goal", {}))
    kind = state.get("kind")
    match = _GOAL_JSON_RE.search(content)
    if match:
        try:
            data = json.loads(match.group(1))
            goal = {**goal, **data}
            kind = data.get("kind", kind)
        except json.JSONDecodeError:
            pass

    return {
        "messages": [AIMessage(content=content)],
        "goal": goal,
        "kind": kind,
        "status": "interviewing",
    }


def route_after_clarify(state: GoalState) -> Literal["persist", "__end__"]:
    """If the last agent message carried a goal, persist it; else wait for user."""
    last = state["messages"][-1] if state["messages"] else None
    content = getattr(last, "content", "") or ""
    return "persist" if _GOAL_JSON_RE.search(content) else END


async def persist_node(state: GoalState, config: RunnableConfig) -> dict:
    """Persist the goal via the shared service and confirm."""
    goal_data = state.get("goal", {})
    project_raw = goal_data.get("project_id")
    project_id = None
    if project_raw:
        try:
            project_id = (
                uuid.UUID(str(project_raw))
                if not isinstance(project_raw, uuid.UUID)
                else project_raw
            )
        except (ValueError, AttributeError):
            project_id = None  # goal has no project scope

    goal = await create_goal_entity(
        title=goal_data.get("title", "Untitled goal"),
        kind=goal_data.get("kind", "research"),
        cadence=goal_data.get("cadence", "0 7 * * *"),
        description=goal_data.get("description", ""),
        project_id=project_id,
        config=goal_data.get("config", {}),
    )

    summary = (
        f"Goal created: **{goal.title}** ({goal.kind.value}) — cadence "
        f"`{goal.cadence}`. It will run on the scheduler starting next match."
    )
    return {
        "messages": [AIMessage(content=summary)],
        "status": "confirmed",
    }


def build_goal_creator_graph(checkpointer: BaseCheckpointSaver | None = None) -> Any:
    builder = StateGraph(GoalState)
    builder.add_node("clarify", clarify_node)
    builder.add_node("persist", persist_node)
    builder.add_edge(START, "clarify")
    builder.add_conditional_edges("clarify", route_after_clarify, ["persist", END])
    builder.add_edge("persist", END)
    return builder.compile(checkpointer=checkpointer)
