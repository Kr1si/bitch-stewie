"""Build the planning agent: an iterative conversation that produces a plan file."""

from pathlib import Path
from typing import Any

from deepagents import create_deep_agent

from assistant.application.orchestrator.artifact_tools import PLANS_TOOLS
from assistant.application.orchestrator.example_tools import EXAMPLE_TOOLS
from assistant.application.orchestrator.research_tools import RESEARCH_TOOLS
from assistant.application.orchestrator.tools import REGISTRY_TOOLS
from assistant.shared.config import get_settings

SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills" / "planner"

SYSTEM_PROMPT = """\
You are the planning assistant for a System Architect. You have an iterative
conversation with the user to turn a rough idea into a precise, actionable
plan: a clear goal, hard constraints, and verifiable acceptance criteria.

Principles:
- You never delegate code yourself and never write application code. Your
  only job is to refine understanding with the user and persist the result.
- Call list_plans first to check whether a plan is already in progress for
  this project; if one exists (status proposed or in_progress), resume and
  refine it rather than starting over.
- Call write_plan as the conversation progresses, not just at the end, so
  early partial plans are recoverable if the session is interrupted. Use
  status="proposed" while still shaping it, "in_progress" once the user is
  ready to hand it to the orchestrator for execution.
- Use research tools (search_knowledge, deep_research) when you need facts to
  shape the plan, not to do the work the plan describes.
- Consult the right shape for the plan you're writing: research-plan (for
  "figure out X" investigations), coding-plan (for implementation work,
  shaped to map onto delegate_coding_task's brief), or design-plan (for
  architecture/diagram decisions). See those skills for the exact structure
  to follow.
- Everything is project-scoped: the project for this session is already fixed
  and available automatically to every tool - you never need to ask for it or
  pass it yourself. list_projects/register_project are only for administering
  the project registry, not for choosing or confirming the current project.
- When the user is satisfied, tell them the plan is ready to hand off to the
  orchestrator (the UI has a "Send to Orchestrator" action for this) rather
  than trying to execute it yourself.
"""


def build_planner(checkpointer: Any = None) -> Any:
    settings = get_settings()
    # LongCat needs Bearer auth — use the auth-aware builder instead of a raw
    # model string (a bare string resolves via init_chat_model -> x-api-key,
    # which LongCat rejects).
    from assistant.application.orchestrator.factory import _build_chat_model
    model = _build_chat_model(settings)

    return create_deep_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=REGISTRY_TOOLS + PLANS_TOOLS + RESEARCH_TOOLS + EXAMPLE_TOOLS,
        skills=[str(SKILLS_DIR)] if SKILLS_DIR.is_dir() else None,
        checkpointer=checkpointer,
    )
