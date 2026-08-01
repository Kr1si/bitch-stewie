import { describe, it, expect } from "vitest";
import {
  groupEvents,
  laneDuration,
  timeLabel,
  type RunEvent,
  type Lane,
} from "../eventsGrouping";

const ev = (type: string, payload: Record<string, unknown> = {}, at = "2024-01-01T10:00:00Z"): RunEvent => ({
  type,
  payload,
  at,
});

/** Collect the items of a given kind from every lane, in lane-then-item order. */
function itemsOf<T extends Lane["items"][number]["kind"]>(lanes: Lane[], kind: T): Extract<Lane["items"][number], { kind: T }>[] {
  const out = [];
  for (const l of lanes) for (const it of l.items) if (it.kind === kind) out.push(it as any);
  return out;
}

describe("groupEvents", () => {
  it("returns only the main lane for empty input", () => {
    const lanes = groupEvents([]);
    expect(lanes).toHaveLength(1);
    expect(lanes[0].isMain).toBe(true);
    expect(lanes[0].items).toHaveLength(0);
  });

  it("puts a single text event on the main lane", () => {
    const lanes = groupEvents([ev("text", { text: "hello" })]);
    const main = lanes.find((l) => l.isMain)!;
    expect(main.items).toHaveLength(1);
    expect(main.items[0]).toMatchObject({ kind: "text", text: "hello" });
  });

  it("drops a text event whose text is empty", () => {
    const lanes = groupEvents([ev("text", { text: "" })]);
    const main = lanes.find((l) => l.isMain)!;
    expect(main.items).toHaveLength(0);
  });

  it("pairs a pre_tool/post_tool on the orchestrator into one ToolBlock", () => {
    const lanes = groupEvents([
      ev("pre_tool", { tool: "Bash", input: "ls", agent: "" }),
      ev("post_tool", { tool: "Bash", output: "file.txt", agent: "" }),
    ]);
    const main = lanes.find((l) => l.isMain)!;
    const tools = itemsOf(lanes, "tool");
    expect(tools).toHaveLength(1);
    expect(tools[0]).toMatchObject({ kind: "tool", tool: "Bash", input: "ls", output: "file.txt", agent: "" });
  });

  it("leaves output null until post_tool arrives (tool still running)", () => {
    const lanes = groupEvents([ev("pre_tool", { tool: "Bash", input: "sleep 10", agent: "" })]);
    const tools = itemsOf(lanes, "tool");
    expect(tools).toHaveLength(1);
    expect(tools[0].output).toBeNull();
  });

  it("spawns a child lane on subagent_start and closes it on subagent_stop", () => {
    const lanes = groupEvents([
      ev("subagent_start", { agent: "researcher", agent_id: "r-1" }),
      ev("subagent_stop", { agent: "researcher", agent_id: "r-1" }),
    ]);
    const child = lanes.find((l) => l.key === "sub:r-1");
    expect(child).toBeDefined();
    expect(child!.agent).toBe("researcher");
    expect(child!.agentId).toBe("r-1");
    expect(child!.running).toBe(false);
    expect(child!.startedAt).toBe("2024-01-01T10:00:00Z");
    expect(child!.stoppedAt).toBe("2024-01-01T10:00:00Z");
  });

  it("marks a lane running when start has no matching stop", () => {
    const lanes = groupEvents([ev("subagent_start", { agent: "researcher", agent_id: "r-2" })]);
    const child = lanes.find((l) => l.key === "sub:r-2");
    expect(child!.running).toBe(true);
    expect(child!.stoppedAt).toBeNull();
  });

  it("attributes a tool event to the innermost open subagent of the same type", () => {
    const lanes = groupEvents([
      ev("subagent_start", { agent: "researcher", agent_id: "r-1" }),
      ev("subagent_start", { agent: "researcher", agent_id: "r-2" }),
      ev("pre_tool", { tool: "WebSearch", input: "q", agent: "researcher" }),
      ev("subagent_stop", { agent: "researcher", agent_id: "r-2" }),
      ev("subagent_stop", { agent: "researcher", agent_id: "r-1" }),
    ]);
    // innermost open researcher is r-2
    const inner = lanes.find((l) => l.key === "sub:r-2")!;
    expect(itemsOf([inner], "tool")).toHaveLength(1);
    const outer = lanes.find((l) => l.key === "sub:r-1")!;
    expect(itemsOf([outer], "tool")).toHaveLength(0);
  });

  it("routes a typeless text event to the innermost open subagent", () => {
    const lanes = groupEvents([
      ev("subagent_start", { agent: "researcher", agent_id: "r-1" }),
      ev("text", { text: "thinking…" }), // no agent field
    ]);
    const child = lanes.find((l) => l.key === "sub:r-1")!;
    expect(child.items).toHaveLength(1);
    expect(child.items[0]).toMatchObject({ kind: "text", text: "thinking…" });
  });

  it("puts a typeless text event on the main lane when no subagent is open", () => {
    const lanes = groupEvents([ev("text", { text: "solo" })]);
    const main = lanes.find((l) => l.isMain)!;
    expect(main.items).toHaveLength(1);
    expect(main.items[0]).toMatchObject({ kind: "text", text: "solo" });
  });

  it("creates an orphan lane for a tool event whose type has no open scope", () => {
    const lanes = groupEvents([ev("pre_tool", { tool: "WebSearch", input: "q", agent: "researcher" })]);
    const orphan = lanes.find((l) => l.key === "orphan:researcher");
    expect(orphan).toBeDefined();
    expect(orphan!.agent).toBe("researcher");
    expect(itemsOf([orphan!], "tool")).toHaveLength(1);
  });

  it("pairs interleaved same-named tools FIFO (not LIFO)", () => {
    // pre_A, pre_B, post_A, post_B  -> post_A must attach to pre_A
    const lanes = groupEvents([
      ev("pre_tool", { tool: "Bash", input: "1", agent: "" }),
      ev("pre_tool", { tool: "Bash", input: "2", agent: "" }),
      ev("post_tool", { tool: "Bash", output: "out-1", agent: "" }),
      ev("post_tool", { tool: "Bash", output: "out-2", agent: "" }),
    ]);
    const tools = itemsOf(lanes, "tool");
    expect(tools).toHaveLength(2);
    expect(tools[0]).toMatchObject({ input: "1", output: "out-1" });
    expect(tools[1]).toMatchObject({ input: "2", output: "out-2" });
  });

  it("appends an orphan post_tool as its own item when no pre_tool matches", () => {
    const lanes = groupEvents([ev("post_tool", { tool: "Bash", output: "ghost", agent: "" })]);
    const tools = itemsOf(lanes, "tool");
    expect(tools).toHaveLength(1);
    expect(tools[0]).toMatchObject({ input: "", output: "ghost" });
  });

  it("records a stop note on the main lane", () => {
    const lanes = groupEvents([ev("stop", {})]);
    const main = lanes.find((l) => l.isMain)!;
    expect(main.items[0]).toMatchObject({ kind: "note", noteType: "stop", text: "session stopped" });
  });

  it("records a stop note with stop_hook_active detail", () => {
    const lanes = groupEvents([ev("stop", { stop_hook_active: true })]);
    const main = lanes.find((l) => l.isMain)!;
    expect(main.items[0]).toMatchObject({ noteType: "stop", text: "stop hook active" });
  });

  it("records a notification note on the main lane", () => {
    const lanes = groupEvents([ev("notification", { message: "ready" })]);
    const main = lanes.find((l) => l.isMain)!;
    expect(main.items[0]).toMatchObject({ kind: "note", noteType: "notification", text: "ready" });
  });

  it("records a permission_request note on the main lane", () => {
    const lanes = groupEvents([ev("permission_request", { tool: "Bash", input: "rm -rf" })]);
    const main = lanes.find((l) => l.isMain)!;
    expect(main.items[0]).toMatchObject({ noteType: "permission", text: "Bash: rm -rf" });
  });

  it("surfaces an unknown event type as a note on the main lane", () => {
    const lanes = groupEvents([ev("weird_new_event", { foo: "bar" })]);
    const main = lanes.find((l) => l.isMain)!;
    expect(main.items[0]).toMatchObject({ kind: "note", noteType: "weird_new_event" });
    expect((main.items[0] as any).text).toContain("bar");
  });

  it("falls back to '?' when subagent_start has no agent name", () => {
    const lanes = groupEvents([ev("subagent_start", { agent_id: "x-9" })]);
    const child = lanes.find((l) => l.key === "sub:x-9");
    expect(child!.agent).toBe("?");
  });

  it("matches subagent_stop by agent type when agent_id is missing", () => {
    const lanes = groupEvents([
      ev("subagent_start", { agent: "researcher", agent_id: "r-1" }),
      ev("subagent_stop", { agent: "researcher" }), // no agent_id
    ]);
    const child = lanes.find((l) => l.key === "sub:r-1")!;
    expect(child.running).toBe(false);
    expect(child.stoppedAt).toBe("2024-01-01T10:00:00Z");
  });

  it("is deterministic / idempotent when re-run on the same events", () => {
    const events: RunEvent[] = [
      ev("text", { text: "hi" }),
      ev("subagent_start", { agent: "researcher", agent_id: "r-1" }),
      ev("pre_tool", { tool: "Bash", input: "ls", agent: "researcher" }),
      ev("post_tool", { tool: "Bash", output: "ok", agent: "researcher" }),
      ev("subagent_stop", { agent: "researcher", agent_id: "r-1" }),
      ev("stop", {}),
    ];
    const a = groupEvents(events);
    const b = groupEvents(events);
    expect(JSON.parse(JSON.stringify(a))).toEqual(JSON.parse(JSON.stringify(b)));
  });

  it("produces a superset when the event log grows (append-only safety)", () => {
    const base: RunEvent[] = [ev("text", { text: "a" })];
    const grown: RunEvent[] = [...base, ev("text", { text: "b" })];
    const lanesBase = groupEvents(base);
    const lanesGrown = groupEvents(grown);
    expect(itemsOf(lanesGrown, "text").length).toBeGreaterThan(itemsOf(lanesBase, "text").length);
  });
});

describe("laneDuration", () => {
  const lane = (over: Partial<Lane>): Lane => ({
    key: "k",
    agent: "",
    agentId: "",
    label: "",
    isMain: false,
    startedAt: null,
    stoppedAt: null,
    running: false,
    items: [],
    ...over,
  });

  it("returns null when there is no start time", () => {
    expect(laneDuration(lane({}))).toBeNull();
  });

  it("returns null when started but not yet stopped (running)", () => {
    expect(laneDuration(lane({ startedAt: "2024-01-01T10:00:00Z" }))).toBeNull();
  });

  it("formats sub-second durations as ms", () => {
    expect(laneDuration(lane({ startedAt: "2024-01-01T10:00:00.000Z", stoppedAt: "2024-01-01T10:00:00.500Z" }))).toBe("500ms");
  });

  it("formats seconds", () => {
    expect(laneDuration(lane({ startedAt: "2024-01-01T10:00:00Z", stoppedAt: "2024-01-01T10:00:07Z" }))).toBe("7s");
  });

  it("formats minutes+seconds with zero padding", () => {
    expect(laneDuration(lane({ startedAt: "2024-01-01T10:00:00Z", stoppedAt: "2024-01-01T10:02:05Z" }))).toBe("2m05s");
  });

  it("clamps negative durations to zero", () => {
    expect(laneDuration(lane({ startedAt: "2024-01-01T10:00:10Z", stoppedAt: "2024-01-01T10:00:00Z" }))).toBe("0ms");
  });
});

describe("timeLabel", () => {
  it("returns the HH:MM:SS portion of an ISO timestamp", () => {
    expect(timeLabel("2024-01-01T14:32:05Z")).toBe("14:32:05");
  });

  it("passes through a short/unknown timestamp unchanged", () => {
    expect(timeLabel("14:32:05")).toBe("14:32:05");
  });
});
