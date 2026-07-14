/**
 * Group a flat CC run event log into per-agent "lanes" so the Events dialog can
 * visualize delegation (who is doing what, when a subagent spawns/runs/finishes)
 * instead of dumping raw JSON.
 *
 * Event payload shapes (see backend/src/assistant/cc_bridge/lifecycle_hooks.py):
 *  - pre_tool / post_tool : { tool, input|output, agent }  — agent is "" for the
 *    main orchestrator, or an agent *type* name when the tool call happens inside
 *    a subagent.
 *  - subagent_start / subagent_stop : { agent, agent_id }  — marks a subagent
 *    instance beginning / ending. agent_id identifies the specific instance.
 *  - text : narration from whichever agent is currently active (optional agent
 *    field; falls back to the innermost active subagent).
 *  - stop / notification / permission_request : session-level, no agent field.
 *
 * Because tool/text events carry only the agent *type* (not agent_id), an
 * instance is attributed via a stack of open subagent scopes: a tool event with
 * agent===T is attached to the innermost still-open subagent of type T. Tool
 * events whose type matches no open scope land on a per-type "orphan" lane so
 * nothing is silently dropped.
 */

export type RunEvent = { type: string; payload: Record<string, unknown>; at: string };

export type ToolItem = {
  kind: "tool";
  id: string;
  tool: string;
  input: string;
  output: string | null; // null => post_tool hasn't arrived yet (still running)
  agent: string;
};
export type TextItem = { kind: "text"; id: string; text: string; agent: string };
export type NoteItem = { kind: "note"; id: string; noteType: string; text: string };

export type LaneItem = ToolItem | TextItem | NoteItem;

export type Lane = {
  key: string;
  agent: string; // type name; "" for the main orchestrator
  agentId: string; // instance id; "" for the main orchestrator / orphan lanes
  label: string;
  isMain: boolean;
  startedAt: string | null;
  stoppedAt: string | null;
  running: boolean; // true if subagent_start seen with no matching subagent_stop
  items: LaneItem[];
};

const MAIN_KEY = "__main__";

function str(v: unknown): string {
  return typeof v === "string" ? v : v == null ? "" : String(v);
}

/**
 * Group raw events into lanes. Pure & deterministic — safe to re-run on every
 * poll without flicker as long as the underlying event list is append-only.
 */
export function groupEvents(events: RunEvent[]): Lane[] {
  const lanes = new Map<string, Lane>();
  const order: string[] = []; // lane insertion order

  const getLane = (key: string): Lane => {
    let lane = lanes.get(key);
    if (!lane) {
      lane = {
        key,
        agent: "",
        agentId: "",
        label: "",
        isMain: false,
        startedAt: null,
        stoppedAt: null,
        running: false,
        items: [],
      };
      lanes.set(key, lane);
      order.push(key);
    }
    return lane;
  };

  const main = getLane(MAIN_KEY);
  main.isMain = true;
  main.label = "orchestrator";

  // Stack of open subagent scopes, innermost last. Each entry ties an agent type
  // to its instance lane key so tool/text events can be attributed by type.
  const open: { key: string; agent: string; agentId: string }[] = [];

  let counter = 0;
  const nextId = (p: string) => `${p}-${counter++}`;

  // Pick the lane a tool/text event with the given agent type belongs to.
  const laneForAgent = (agent: string): Lane => {
    if (!agent) return main;
    // innermost still-open subagent of the same type
    for (let i = open.length - 1; i >= 0; i--) {
      if (open[i].agent === agent) return getLane(open[i].key);
    }
    // no open scope of this type — orphan lane keyed by type name
    const key = `orphan:${agent}`;
    const lane = getLane(key);
    lane.agent = agent;
    lane.label = agent;
    return lane;
  };

  for (const e of events) {
    const p = e.payload ?? {};
    switch (e.type) {
      case "subagent_start": {
        const agent = str(p.agent) || "?";
        const agentId = str(p.agent_id);
        const key = agentId ? `sub:${agentId}` : `sub:${agent}:${counter}`;
        const lane = getLane(key);
        lane.agent = agent;
        lane.agentId = agentId;
        lane.label = agent;
        lane.startedAt = e.at;
        lane.running = true;
        open.push({ key, agent, agentId });
        break;
      }
      case "subagent_stop": {
        const agentId = str(p.agent_id);
        // match the innermost open scope with this agent_id (or same agent type
        // when agent_id is missing)
        const agent = str(p.agent);
        let idx = -1;
        for (let i = open.length - 1; i >= 0; i--) {
          if (agentId && open[i].agentId === agentId) { idx = i; break; }
          if (!agentId && open[i].agent === agent) { idx = i; break; }
        }
        if (idx >= 0) {
          const scope = open.splice(idx, 1)[0];
          const lane = getLane(scope.key);
          lane.stoppedAt = e.at;
          lane.running = false;
        } else {
          // stop with no matching start: best-effort mark any same-type open lane
          const key = `sub:${agentId || agent}`;
          const lane = lanes.get(key);
          if (lane) { lane.stoppedAt = e.at; lane.running = false; }
        }
        break;
      }
      case "pre_tool": {
        const agent = str(p.agent);
        const lane = laneForAgent(agent);
        if (!lane.agent && agent) { lane.agent = agent; lane.label = agent; }
        lane.items.push({
          kind: "tool",
          id: nextId("t"),
          tool: str(p.tool) || "?",
          input: str(p.input),
          output: null,
          agent,
        });
        break;
      }
      case "post_tool": {
        const agent = str(p.agent);
        const lane = laneForAgent(agent);
        const tool = str(p.tool) || "?";
        const output = str(p.output);
        // pair with the OLDEST pending (output===null) pre_tool of the same tool
        // name in this lane (FIFO). LIFO would mis-pair when two same-named tools
        // interleave (pre_A, pre_B, post_A, post_B): post_A would attach to pre_B.
        let matched = false;
        for (let i = 0; i < lane.items.length; i++) {
          const it = lane.items[i];
          if (it.kind === "tool" && it.output === null && it.tool === tool) {
            it.output = output;
            matched = true;
            break;
          }
        }
        if (!matched) {
          // orphan post_tool (no pre): still surface it
          lane.items.push({
            kind: "tool",
            id: nextId("t"),
            tool,
            input: "",
            output,
            agent,
          });
        }
        break;
      }
      case "text": {
        const agent = str(p.agent);
        const lane = agent ? laneForAgent(agent)
          : (open.length ? getLane(open[open.length - 1].key) : main);
        const text = str(p.text ?? p.content ?? p.message ?? "");
        if (!text) break;
        lane.items.push({ kind: "text", id: nextId("x"), text, agent: lane.agent });
        break;
      }
      case "stop": {
        const active = p.stop_hook_active;
        main.items.push({
          kind: "note",
          id: nextId("n"),
          noteType: "stop",
          text: active ? "stop hook active" : "session stopped",
        });
        break;
      }
      case "notification": {
        main.items.push({
          kind: "note",
          id: nextId("n"),
          noteType: "notification",
          text: str(p.message) || str(p.type),
        });
        break;
      }
      case "permission_request": {
        main.items.push({
          kind: "note",
          id: nextId("n"),
          noteType: "permission",
          text: `${str(p.tool)}: ${str(p.input)}`,
        });
        break;
      }
      default: {
        // unknown event type: surface as a note on the main lane so it isn't lost
        main.items.push({
          kind: "note",
          id: nextId("n"),
          noteType: e.type,
          text: JSON.stringify(p).slice(0, 200),
        });
        break;
      }
    }
  }

  return order.map((k) => lanes.get(k)!).filter((l): l is Lane => Boolean(l));
}

/** Format a start→stop duration; returns null if no start. */
export function laneDuration(lane: Lane): string | null {
  if (!lane.startedAt) return null;
  const start = new Date(lane.startedAt).getTime();
  const end = lane.stoppedAt ? new Date(lane.stoppedAt).getTime() : null;
  if (end == null) return null;
  const ms = Math.max(0, end - start);
  if (ms < 1000) return `${ms}ms`;
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m${rem.toString().padStart(2, "0")}s`;
}

/** Relative time label for an event timestamp, e.g. "14:32:05". */
export function timeLabel(at: string): string {
  return at.length >= 19 ? at.slice(11, 19) : at;
}
