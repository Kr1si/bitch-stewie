"""Native Claude Code subagents handed to every delegated CC session.

These are *CC-level* subagents (claude_agent_sdk AgentDefinition), distinct from
the LangGraph orchestrator nodes. A delegated coding session can spawn one of
these scoped, memory:project-backed subagents natively instead of the
orchestrator doing it upstream — e.g. the code-delegate can hand a research
question to `researcher` without a round-trip through the LangGraph graph.

`memory="project"` lets each subagent persist its own notes into the target
project repo's auto-memory, so lessons survive across sessions for free (we do
not reimplement CC's memory). All subagents may use the in-process
`assistant-memory` MCP server (registered in runner._options) by name.
"""

from claude_agent_sdk import AgentDefinition

# Tool allowlists are CC tool names. We scope each subagent tightly so a
# delegated session can't accidentally escalate a narrow role into full file
# mutation. The `code-delegate` keeps the full coding toolset.

_RESEARCHER_TOOLS = ["Read", "Grep", "Glob", "WebFetch", "WebSearch"]
_ARCHITECT_TOOLS = ["Read", "Grep", "Glob", "Edit", "Write"]
_DOC_WRITER_TOOLS = ["Read", "Grep", "Glob", "Write", "Edit"]
_CODE_DELEGATE_TOOLS = [
    "Read", "Write", "Edit", "Glob", "Grep", "Bash",
    "Task", "TaskUpdate", "TaskList", "TaskGet",
]

_MCP = ["assistant-memory"]

_RESEARCHER_PROMPT = (
    "You are the researcher subagent. Investigate questions by reading code, "
    "searching the repo, and fetching the web. Return a concise, cited summary "
    "(file:line references). Do NOT edit files. Record any decision worth "
    "remembering via the assistant-memory `record_decision` tool."
)

_ARCHITECT_PROMPT = (
    "You are the architect subagent. Make and document architecture decisions "
    "for the target repo. You may read and lightly edit docs/rules, but do not "
    "implement features. Record every decision via `record_decision` and keep "
    "conventions via `write_convention`."
)

_DOC_WRITER_PROMPT = (
    "You are the doc-writer subagent. Produce or update markdown documentation "
    "and diagrams for the target repo. Follow the architecture-doc output style "
    "when set. Record structural decisions via `record_decision`."
)

_CODE_DELEGATE_PROMPT = (
    "You are the code-delegate subagent. Implement the assigned task directly "
    "in the target repo: branch, code, test, commit. Follow the "
    "`delegate-coding-task` skill for the delivery format and working "
    "agreement. Record any architecture-significant choice via "
    "`record_decision`."
)


def build_subagents() -> dict[str, AgentDefinition]:
    """Return the CC subagent registry passed as `agents=` to ClaudeAgentOptions."""
    return {
        "researcher": AgentDefinition(
            description="Investigate questions by reading code and the web; return cited summaries. No edits.",
            prompt=_RESEARCHER_PROMPT,
            tools=_RESEARCHER_TOOLS,
            mcpServers=_MCP,
            memory="project",
            effort="medium",
        ),
        "architect": AgentDefinition(
            description="Make and document architecture decisions; lightly edit docs/rules only.",
            prompt=_ARCHITECT_PROMPT,
            tools=_ARCHITECT_TOOLS,
            mcpServers=_MCP,
            memory="project",
            effort="high",
        ),
        "doc-writer": AgentDefinition(
            description="Write/update markdown docs and diagrams, following the architecture-doc output style.",
            prompt=_DOC_WRITER_PROMPT,
            tools=_DOC_WRITER_TOOLS,
            mcpServers=_MCP,
            memory="project",
            effort="medium",
        ),
        "code-delegate": AgentDefinition(
            description="Implement an assigned coding task in the target repo: branch, code, test, commit.",
            prompt=_CODE_DELEGATE_PROMPT,
            tools=_CODE_DELEGATE_TOOLS,
            mcpServers=_MCP,
            memory="project",
            effort="high",
        ),
    }