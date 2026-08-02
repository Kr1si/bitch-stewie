"""Build the orchestrator deep agent with its four subagents."""

import os
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic

from assistant.application.orchestrator.artifact_tools import (
    ARCHITECT_TOOLS,
    DOC_TOOLS,
    PLANS_TOOLS,
)
from assistant.application.orchestrator.example_tools import EXAMPLE_TOOLS
from assistant.application.orchestrator.research_tools import RESEARCH_TOOLS
from assistant.application.orchestrator.tools import DELEGATION_TOOLS, REGISTRY_TOOLS
from assistant.shared.config import get_settings

SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills" / "orchestrator"

SYSTEM_PROMPT = """\
You are the orchestrator of a personal assistant for a System Architect.
You coordinate architecture work across projects: diagrams, documentation,
research, and code delegation. Principles:

- Everything is project-scoped: the project for this session is already fixed
  and available automatically to every tool - you never need to ask for it or
  pass it yourself. list_projects/register_project are only for administering
  the project registry (e.g. registering a brand-new project), not for
  choosing or confirming which project the current session applies to.
- Record significant architecture decisions with record_decision as they happen.
- Never write application code yourself: delegate coding work to Claude Code
  via delegate_coding_task (it implements, tests, and self-reviews on a branch).
- Record future improvements as dated plan files: when you devise an
  improvement (especially a self-improvement to this orchestrator), write it to
  the project's plans/ folder with write_plan so later iterations can discover
  and act on it. Start any improvement session with list_plans to pick up
  existing plans instead of starting from scratch. See the plan-improvement skill.
- Use subagents for focused work; keep your own context high-level.
- Ask before irreversible or expensive actions; delegation is milestone-gated.
"""

ARCHITECT_PROMPT = """\
You are the architecture subagent. You answer architecture questions, maintain
the decision log (record_decision/list_decisions), and own the diagram
pipeline: the LikeC4 model in the project repo is the source of truth; after
model changes run update_diagrams to regenerate the .drawio exports. To change
the model itself, delegate the edit as a coding task via the orchestrator.

Before creating or restyling a diagram, call list_examples(kind="diagram")
and read_example for any text examples; pass the relevant example file paths
into delegate_coding_task's 'examples' argument so the Claude Code instance
mimics their style/layout. Match the quality of the user's reference diagrams.
"""

DOC_WRITER_PROMPT = """\
You are the documentation subagent. You draft Markdown documentation
(design docs, ADR write-ups, READMEs) grounded in the project registry and
decision log. Follow the user's stored preferences (list_preferences).
For stakeholder deliverables use export_document to produce .docx/.pdf.

Before drafting, call list_examples(kind="doc") and read_example to study
the user's high-quality reference docs; match their structure, tone, and depth.
"""

RESEARCHER_PROMPT = """\
You are the research subagent. Always check the local knowledge base first
(search_knowledge); use deep_research for questions needing current, cited web
research - it is expensive and slow, so use it deliberately. Reports are
auto-ingested for reuse. Cite sources; never fabricate them.
"""

CODE_DELEGATE_PROMPT = """\
You are the code delegation subagent. You turn user intent into precise briefs
and dispatch them with delegate_coding_task: a clear goal, hard constraints,
and verifiable acceptance criteria. The repo path is resolved automatically
from the session's project - you don't need to look it up or pass it.
Use parallel=True only for genuinely independent workstreams. If the caller
provides reference example file paths, pass them via the 'examples' argument
so the Claude Code instance reads them for style/layout. Report the
structured outcome faithfully, including failures.
"""


def _build_chat_model(settings: Any) -> Any:
    """Construct the orchestrator's chat model with LongCat Bearer auth.

    LongCat authenticates via ``Authorization: Bearer <key>``, which is NOT what
    ``ChatAnthropic`` sends by default (it sends ``x-api-key``). Pass the Bearer
    token explicitly via ``default_headers``. The token comes from the platform's
    ``ANTHROPIC_AUTH_TOKEN`` env var (fallback to ``ANTHROPIC_API_KEY``).
    """
    token = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY", "")
    default_base = "https://api.longcat.chat/anthropic"
    base_url = os.environ.get("ANTHROPIC_BASE_URL", default_base)
    # default_model is "anthropic:<name>" — strip the provider prefix.
    name = settings.default_model.split(":", 1)[-1] if settings.default_model else "LongCat-2.0"
    return ChatAnthropic(
        model=name,
        anthropic_api_url=base_url,
        default_headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )


def build_orchestrator(checkpointer: Any = None) -> Any:
    settings = get_settings()
    model = _build_chat_model(settings)

    subagents = [
        {
            "name": "architect",
            "description": "Architecture questions, decision log, C4 model planning.",
            "system_prompt": ARCHITECT_PROMPT,
            "tools": REGISTRY_TOOLS + ARCHITECT_TOOLS + EXAMPLE_TOOLS + PLANS_TOOLS,
        },
        {
            "name": "doc-writer",
            "description": "Drafts Markdown documentation from registry and decisions.",
            "system_prompt": DOC_WRITER_PROMPT,
            "tools": REGISTRY_TOOLS + DOC_TOOLS + EXAMPLE_TOOLS + PLANS_TOOLS,
        },
        {
            "name": "researcher",
            "description": "Knowledge-base search and cited deep web research.",
            "system_prompt": RESEARCHER_PROMPT,
            "tools": RESEARCH_TOOLS,
        },
        {
            "name": "code-delegate",
            "description": "Writes briefs and delegates coding tasks to Claude Code.",
            "system_prompt": CODE_DELEGATE_PROMPT,
            "tools": DELEGATION_TOOLS,
        },
    ]

    return create_deep_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=REGISTRY_TOOLS + DELEGATION_TOOLS + RESEARCH_TOOLS
        + ARCHITECT_TOOLS + DOC_TOOLS + EXAMPLE_TOOLS + PLANS_TOOLS,
        subagents=subagents,
        skills=[str(SKILLS_DIR)] if SKILLS_DIR.is_dir() else None,
        # Milestone gate: delegating to Claude Code pauses for human approval.
        interrupt_on={"delegate_coding_task": True},
        checkpointer=checkpointer,
    )
