"""The brief: the contract between the orchestrator and a Claude Code instance.

The brief carries the *task-specific* parts (goal, repo, constraints,
acceptance criteria, context, reference examples). The *working agreement* and
*delivery format* (the RESULT_MARKER contract) live in the `delegate-coding-task`
CC skill, loaded via `skills=` in DelegationRunner._options — so they are not
duplicated here. If the skill is not loaded, the runner falls back to the
inline working agreement (see runner._fallback_working_agreement).
"""

from pydantic import BaseModel, Field

RESULT_MARKER = "ASSISTANT_RESULT_JSON"


class Brief(BaseModel):
    goal: str
    repo_path: str
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    context: str = ""  # project background injected by the orchestrator
    skills: list[str] = Field(default_factory=list)  # CC skills to prefer (names)
    examples: list[str] = Field(default_factory=list)  # reference file paths to mimic
    output_style: str = ""  # CC output style name (e.g. "architecture-doc"); "" = none

    def to_prompt(self) -> str:
        parts = ["# Delegated coding task", "", "## Goal", self.goal.strip()]
        if self.context:
            parts += ["", "## Context", self.context.strip()]
        if self.constraints:
            parts += ["", "## Constraints"] + [f"- {c}" for c in self.constraints]
        if self.acceptance_criteria:
            parts += ["", "## Acceptance criteria"] + [f"- {a}" for a in self.acceptance_criteria]
        if self.skills:
            parts += ["", "## Follow skill",
                      f"Follow the `{self.skills[0]}` skill for the working "
                      f"agreement and delivery format."]
        if self.examples:
            parts += ["", "## Reference examples",
                      "Read these files for style/layout/structure and match their quality:"]
            parts += [f"- {p}" for p in self.examples]
        return "\n".join(parts)


# Inline fallback used by the runner only when the delegate-coding-task skill
# file is not available, so a missing skill never silently drops the delivery
# contract. Kept here (not in to_prompt) so it is only emitted when needed.
def fallback_working_agreement() -> str:
    return (
        "\n## Working agreement\n"
        "- Work directly in this repository; create a feature branch and commit your work.\n"
        "- Run the project's tests if present; do not finish with failing tests.\n"
        "- When done, output a final line of the form:\n"
        f'  {RESULT_MARKER}: {{"branch": "...", "commits": ["..."], '
        '"summary": "...", "tests": "passed|failed|none"}'
    )