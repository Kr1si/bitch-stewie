const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function parseErr(resp: Response, method: string, path: string): Promise<Error> {
  let detail = `${resp.status}`;
  try {
    const body = await resp.json();
    if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  } catch {
    /* non-json body */
  }
  return new Error(`${method} ${path}: ${detail}`);
}

export async function apiGet<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`);
  if (!resp.ok) throw await parseErr(resp, "GET", path);
  return resp.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw await parseErr(resp, "POST", path);
  return resp.json() as Promise<T>;
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw await parseErr(resp, "PUT", path);
  return resp.json() as Promise<T>;
}

export async function apiDelete<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  if (!resp.ok) throw await parseErr(resp, "DELETE", path);
  return resp.json() as Promise<T>;
}

export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, { method: "POST", body: form });
  if (!resp.ok) throw await parseErr(resp, "POST", path);
  return resp.json() as Promise<T>;
}

export type StreamHandlers = {
  onToken?: (text: string) => void;
  onTool?: (calls: { name: string }[]) => void;
  onInterrupt?: (interrupt: { requests: unknown[] } | null) => void;
  onDone?: (reply: string) => void;
  onError?: (error: string) => void;
};

/**
 * POST an SSE stream (EventSource can't POST). Parses the text/event-stream
 * body and dispatches token/tool/interrupt/done events.
 */
export async function streamChat(
  url: string,
  body: unknown,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await fetch(`${API_BASE}${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });
  if (!resp.ok || !resp.body) throw await parseErr(resp, "POST", url);

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let event = "message";
  let fullText = "";

  const dispatch = () => {
    const lines = buffer.split("\n");
    buffer = "";
    let dataLines: string[] = [];
    for (const line of lines) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      else if (line === "") {
        if (dataLines.length) {
          handleEvent(event, dataLines.join("\n"));
          dataLines = [];
          event = "message";
        }
      }
    }
  };

  const handleEvent = (ev: string, data: string) => {
    let payload: any = {};
    try { payload = JSON.parse(data); } catch { payload = { raw: data }; }
    if (ev === "token" && payload.text != null) {
      fullText += payload.text;
      handlers.onToken?.(payload.text);
    } else if (ev === "tool") {
      handlers.onTool?.(payload.calls ?? []);
    } else if (ev === "interrupt") {
      handlers.onInterrupt?.(payload.interrupt ?? null);
    } else if (ev === "done") {
      if (payload.reply) fullText = payload.reply;
      handlers.onInterrupt?.(null);
      handlers.onDone?.(fullText);
    } else if (ev === "error") {
      handlers.onError?.(payload.error || "Something went wrong.");
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    if (buffer.includes("\n\n")) dispatch();
  }
  if (buffer.trim()) dispatch();
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw await parseErr(resp, "PATCH", path);
  return resp.json() as Promise<T>;
}

// --- Goals -------------------------------------------------------------------
export type Goal = {
  id: string;
  project_id: string | null;
  title: string;
  description: string;
  kind: "research" | "coding" | "testing";
  status: "active" | "paused" | "completed";
  cadence: string;
  config: Record<string, unknown>;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export async function listGoals(): Promise<Goal[]> {
  return apiGet<Goal[]>("/api/goals");
}

export async function createGoal(body: Partial<Goal>): Promise<Goal> {
  return apiPost<Goal>("/api/goals", body);
}

export async function patchGoal(id: string, body: Partial<Goal>): Promise<Goal> {
  return apiPatch<Goal>(`/api/goals/${id}`, body);
}

// --- Reports -----------------------------------------------------------------
export type ReportFinding = { category: string; markdown: string };
export type Report = {
  date: string;
  digest: string;
  findings: ReportFinding[];
  market_ideas: string;
};

export async function listReports(): Promise<string[]> {
  return apiGet<string[]>("/api/goals/reports");
}

export async function readReport(date: string): Promise<Report> {
  return apiGet<Report>(`/api/goals/reports/${date}`);
}

export async function deleteGoal(id: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/goals/${id}`, { method: "DELETE" });
  if (!resp.ok) throw await parseErr(resp, "DELETE", `/api/goals/${id}`);
}

// --- Goal-creation interview stream -------------------------------------------
export type GoalChatHandlers = {
  onToken?: (text: string) => void;
  onDone?: (reply: string) => void;
  onError?: (error: string) => void;
};

/**
 * POST one turn of the goal-creator interview to /api/goals/chat/stream.
 * The FE keeps a thread_id across turns so the checkpointer accumulates the
 * interview; pass the same thread_id on every call for a given goal.
 */
export async function streamGoalChat(
  body: { message: string; thread_id?: string; project_id?: string },
  handlers: GoalChatHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/goals/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });
  if (!resp.ok || !resp.body) throw await parseErr(resp, "POST", "/api/goals/chat/stream");

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let event = "message";

  const handleEvent = (ev: string, data: string) => {
    let payload: any = {};
    try { payload = JSON.parse(data); } catch { payload = { raw: data }; }
    if (ev === "token" && payload.text != null) handlers.onToken?.(payload.text);
    else if (ev === "done") handlers.onDone?.(payload.reply ?? "");
    else if (ev === "error") handlers.onError?.(payload.error ?? "goal chat failed");
  };

  const dispatch = () => {
    const lines = buffer.split("\n");
    buffer = "";
    let dataLines: string[] = [];
    for (const line of lines) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      else if (line === "") {
        if (dataLines.length) { handleEvent(event, dataLines.join("\n")); dataLines = []; event = "message"; }
      }
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    if (buffer.includes("\n\n")) dispatch();
  }
  if (buffer.trim()) dispatch();
}

export type ResearchHandlers = {
  onStart?: (goal: string) => void;
  onDone?: (report: string) => void;
  onError?: (error: string) => void;
};

/**
 * POST an SSE stream for the /api/research/deep/stream endpoint. Parses the
 * text/event-stream body and dispatches start/done/error events.
 */
export async function streamResearch(
  url: string,
  body: unknown,
  handlers: ResearchHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await fetch(`${API_BASE}${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });
  if (!resp.ok || !resp.body) throw await parseErr(resp, "POST", url);

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let event = "message";

  const handleEvent = (ev: string, data: string) => {
    let payload: any = {};
    try { payload = JSON.parse(data); } catch { payload = { raw: data }; }
    if (ev === "start") handlers.onStart?.(payload.goal ?? "");
    else if (ev === "done") handlers.onDone?.(payload.report ?? "");
    else if (ev === "error") handlers.onError?.(payload.error ?? "research failed");
  };

  const dispatch = () => {
    const lines = buffer.split("\n");
    buffer = "";
    let dataLines: string[] = [];
    for (const line of lines) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      else if (line === "") {
        if (dataLines.length) {
          handleEvent(event, dataLines.join("\n"));
          dataLines = [];
          event = "message";
        }
      }
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    if (buffer.includes("\n\n")) dispatch();
  }
  if (buffer.trim()) dispatch();
}