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