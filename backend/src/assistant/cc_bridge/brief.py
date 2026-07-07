"""The brief: the contract between the orchestrator and a Claude Code instance."""

from pydantic import BaseModel, Field

RESULT_MARKER = "ASSISTANT_RESULT_JSON"


class Brief(BaseModel):
    goal: str
    repo_path: str
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    context: str = ""  # project background injected by the orchestrator
    skills: list[str] = Field(default_factory=list)  # CC skills to prefer
    examples: list[str] = Field(default_factory=list)  # reference file paths to mimic

    def to_prompt(self) -> str:
        parts = ["# Delegated coding task", "", "## Goal", self.goal.strip()]
        if self.context:
            parts += ["", "## Context", self.context.strip()]
        if self.constraints:
            parts += ["", "## Constraints"] + [f"- {c}" for c in self.constraints]
        if self.acceptance_criteria:
            parts += ["", "## Acceptance criteria"] + [f"- {a}" for a in self.acceptance_criteria]
        if self.skills:
            parts += ["", "## Preferred skills", ", ".join(self.skills)]
        if self.examples:
            parts += ["", "## Reference examples",
                      "Read these files for style/layout/structure and match their quality:"]
            parts += [f"- {p}" for p in self.examples]
        parts += [
            "",
            "## Working agreement",
            "- Work directly in this repository; create a feature branch and commit your work.",
            "- Run the project's tests if present; do not finish with failing tests.",
            "- When done, output a final line of the form:",
            f'  {RESULT_MARKER}: {{"branch": "...", "commits": ["..."], '
            '"summary": "...", "tests": "passed|failed|none"}',
        ]
        return "\n".join(parts)
