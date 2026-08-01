// @vitest-environment node
// SSE parsing relies on a streaming Response body + TextDecoder, which jsdom does
// not implement; Node's native fetch/ReadableStream make this straightforward.
import { describe, it, expect, vi, afterEach } from "vitest";
import { streamChat, streamResearch, type StreamHandlers, type ResearchHandlers } from "../api";

/** Build a streaming Response whose body emits the given SSE text in one chunk. */
function sseResponse(text: string, status = 200): Response {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(text));
      controller.close();
    },
  });
  return new Response(stream, {
    status,
    headers: { "Content-Type": "text/event-stream" },
  });
}

const chatSse = [
  "event: token",
  'data: {"text":"Hello"}',
  "",
  "event: token",
  'data: {"text":" world"}',
  "",
  "event: tool",
  'data: {"calls":[{"name":"Bash"}]}',
  "",
  "event: done",
  'data: {"reply":"Hello world"}',
  "",
].join("\n");

const researchSse = [
  "event: start",
  'data: {"goal":"explain X"}',
  "",
  "event: done",
  'data: {"report":"# Report"}',
  "",
].join("\n");

afterEach(() => {
  vi.restoreAllMocks();
});

describe("streamChat (SSE parse)", () => {
  it("dispatches token events and accumulates full text", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(sseResponse(chatSse));
    const tokens: string[] = [];
    const handlers: StreamHandlers = { onToken: (t) => tokens.push(t) };
    await streamChat("/x", {}, handlers);
    expect(tokens).toEqual(["Hello", " world"]);
  });

  it("dispatches a tool event with the call list", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(sseResponse(chatSse));
    const tools: { name: string }[][] = [];
    const handlers: StreamHandlers = { onTool: (c) => tools.push(c) };
    await streamChat("/x", {}, handlers);
    expect(tools).toEqual([[{ name: "Bash" }]]);
  });

  it("dispatches a done event with the accumulated reply", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(sseResponse(chatSse));
    let reply = "";
    const handlers: StreamHandlers = { onDone: (r) => (reply = r) };
    await streamChat("/x", {}, handlers);
    expect(reply).toBe("Hello world");
  });

  it("throws on a non-ok response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("nope", { status: 500, statusText: "Server Error" }),
    );
    await expect(streamChat("/x", {}, {})).rejects.toThrow(/500/);
  });
});

describe("streamResearch (SSE parse)", () => {
  it("dispatches start then done events", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(sseResponse(researchSse));
    const events: string[] = [];
    const handlers: ResearchHandlers = {
      onStart: (goal) => events.push(`start:${goal}`),
      onDone: (report) => events.push(`done:${report}`),
    };
    await streamResearch("/x", {}, handlers);
    expect(events).toEqual(["start:explain X", "done:# Report"]);
  });

  it("dispatches an error event", async () => {
    const errSse = "event: error\ndata: {\"error\":\"boom\"}\n\n";
    vi.spyOn(globalThis, "fetch").mockResolvedValue(sseResponse(errSse));
    let message = "";
    const handlers: ResearchHandlers = { onError: (e) => (message = e) };
    await streamResearch("/x", {}, handlers);
    expect(message).toBe("boom");
  });

  it("throws on a non-ok response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("nope", { status: 502, statusText: "Bad Gateway" }),
    );
    await expect(streamResearch("/x", {}, {})).rejects.toThrow(/502/);
  });
});
