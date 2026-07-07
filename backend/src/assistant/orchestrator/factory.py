"""Build the orchestrator deep agent with its four subagents."""

from pathlib import Path

from deepagents import create_deep_agent

SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills" / "orchestrator"

from assistant.config import get_settings
from assistant.orchestrator.artifact_tools import ARCHITECT_TOOLS, DOC_TOOLS
from assistant.orchestrator.example_tools import EXAMPLE_TOOLS
from assistant.orchestrator.research_tools import RESEARCH_TOOLS
from assistant.orchestrator.tools import DELEGATION_TOOLS, REGISTRY_TOOLS

SYSTEM_PROMPT = """\
You are the orchestrator of a personal assistant for a System Architect.
You coordinate architecture work across projects: diagrams, documentation,
research, and code delegation. Principles:

- Everything is project-scoped: know which project you are working on
  (list_projects; register new ones when the user starts something new).
- Record significant architecture decisions with record_decision as they happen.
- Never write application code yourself: delegate coding work to Claude Code
  via delegate_coding_task (it implements, tests, and self-reviews on a branch).
- Use subagents for focused work; keep your own context high-level.
- Ask before irreversible or expensive actions; delegation is milestone-gated.
"""

ARCHITECT_PROMPT = """\
You are the architecture subagent. You answer architecture questions, maintain
the decision log (record_decision/list_decisions), and own the diagram
pipeline: the LikeC4 model in the project repo is the source of truth; after
model changes run update_diagrams to regenerate the .drawio exports. To change
the model itself, delegate the edit as a coding task via the orchestrator.

Before creating or restyling a diagram, call list_examples(project, "diagram")
and read_example for any text examples; pass the relevant example file paths
into delegate_coding_task's 'examples' argument so the Claude Code instance
mimics their style/layout. Match the quality of the user's reference diagrams.
"""

DOC_WRITER_PROMPT = """\
You are the documentation subagent. You draft Markdown documentation
(design docs, ADR write-ups, READMEs) grounded in the project registry and
decision log. Follow the user's stored preferences (list_preferences).
For stakeholder deliverables use export_document to produce .docx/.pdf.

Before drafting, call list_examples(project, "doc") and read_example to study
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
verifiable acceptance criteria, and the correct repo_path from the registry.
Use parallel=True only for genuinely independent workstreams. If the caller
provides reference example file paths, pass them via the 'examples' argument
so the Claude Code instance reads them for style/layout. Report the
structured outcome faithfully, including failures.
"""


def build_orchestrator(checkpointer=None):
    settings = get_settings()
    model = settings.default_model

    subagents = [
        {
            "name": "architect",
            "description": "Architecture questions, decision log, C4 model planning.",
            "system_prompt": ARCHITECT_PROMPT,
            "tools": REGISTRY_TOOLS + ARCHITECT_TOOLS + EXAMPLE_TOOLS,
        },
        {
            "name": "doc-writer",
            "description": "Drafts Markdown documentation from registry and decisions.",
            "system_prompt": DOC_WRITER_PROMPT,
            "tools": REGISTRY_TOOLS + DOC_TOOLS + EXAMPLE_TOOLS,
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
        + ARCHITECT_TOOLS + DOC_TOOLS + EXAMPLE_TOOLS,
        subagents=subagents,
        skills=[str(SKILLS_DIR)] if SKILLS_DIR.is_dir() else None,
        # Milestone gate: delegating to Claude Code pauses for human approval.
        interrupt_on={"delegate_coding_task": True},
        checkpointer=checkpointer,
    )
