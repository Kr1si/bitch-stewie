// big-delegation — capped parallel fan-out over a work list.
//
// Use from an INTERACTIVE Claude Code session in this repo when a job splits
// into independent parts touching different files:
//   /big-delegation tasks.md
// where tasks.md contains one task per line (or a markdown list).
//
// ⚠️ Token cost warning: every spawned agent starts cold and bills its own
// context. A previous uncontrolled fan-out spawned 103 agents. This template
// is deliberately capped: at most MAX_PARALLEL agents at a time and at most
// MAX_TASKS total. Do not raise these without checking the plan's budget.
//
// The orchestrated (non-interactive) path stays in the LangGraph orchestrator;
// this workflow is the native-CC alternative for hands-on terminal use.

export const meta = {
  name: "big-delegation",
  description:
    "Fan a work list out to code-delegate subagents in isolated worktrees (capped).",
  args: "<path to work-list file, one task per line>",
};

const MAX_PARALLEL = 4; // concurrent agents; keep ≤6
const MAX_TASKS = 12;   // hard cap per invocation

export default async function bigDelegation({ args, read, agent, log }) {
  const listPath = (args || "").trim();
  if (!listPath) throw new Error("Usage: /big-delegation <work-list file>");

  const raw = await read(listPath);
  const tasks = raw
    .split("\n")
    .map((l) => l.replace(/^[-*\d.\s]+/, "").trim())
    .filter(Boolean);

  if (tasks.length === 0) throw new Error(`No tasks found in ${listPath}`);
  if (tasks.length > MAX_TASKS) {
    throw new Error(
      `${tasks.length} tasks exceeds the cap of ${MAX_TASKS}. ` +
        "Split the list or raise MAX_TASKS deliberately (mind token budget).",
    );
  }

  log(`Delegating ${tasks.length} tasks, ${MAX_PARALLEL} at a time.`);

  const results = [];
  for (let i = 0; i < tasks.length; i += MAX_PARALLEL) {
    const batch = tasks.slice(i, i + MAX_PARALLEL);
    const settled = await Promise.all(
      batch.map((task) =>
        agent({
          type: "code-delegate",       // .claude/agents/code-delegate.md
          isolation: "worktree",       // each task on its own branch/worktree
          prompt:
            `${task}\n\nFollow the delegate-coding-task skill: feature branch, ` +
            "tests, commit, and end with the ASSISTANT_RESULT_JSON line.",
        }).then(
          (out) => ({ task, ok: true, out }),
          (err) => ({ task, ok: false, out: String(err) }),
        ),
      ),
    );
    results.push(...settled);
  }

  const failed = results.filter((r) => !r.ok);
  log(`Done: ${results.length - failed.length}/${results.length} succeeded.`);
  return results
    .map((r) => `${r.ok ? "✅" : "❌"} ${r.task}\n${String(r.out).slice(-400)}`)
    .join("\n\n");
}