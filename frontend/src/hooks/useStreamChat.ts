import { useCallback, useRef, useState } from "react";
import { streamChat, type StreamHandlers } from "../lib/api";

export type ToolCall = { name: string };
export type Interrupt = { requests: unknown[] } | null;

/**
 * Drives the streaming chat endpoints. Holds the running thread id, busy
 * state, the in-flight tool calls, and the current interrupt gate.
 */
export function useStreamChat() {
  const [busy, setBusy] = useState(false);
  const [tools, setTools] = useState<ToolCall[]>([]);
  const [gate, setGate] = useState<Interrupt>(null);
  const threadRef = useRef<string | null>(null);

  const run = useCallback(
    (
      url: string,
      body: Record<string, unknown>,
      handlers: StreamHandlers,
    ) => {
      setBusy(true);
      setTools([]);
      setGate(null);
      const wrapped: StreamHandlers = {
        onToken: handlers.onToken,
        onTool: (calls) => { setTools((prev) => [...prev, ...calls]); handlers.onTool?.(calls); },
        onInterrupt: (i) => { if (i) setGate(i); handlers.onInterrupt?.(i); },
        onDone: (reply) => { setGate(null); setBusy(false); handlers.onDone?.(reply); },
      };
      // busy is cleared in onDone; on error, clear it here
      return streamChat(url, body, wrapped).catch((e) => {
        setBusy(false);
        handlers.onDone?.("");
        throw e;
      });
    },
    [],
  );

  const setThread = useCallback((id: string | null) => { threadRef.current = id; }, []);

  return { busy, tools, gate, run, setThread, threadRef };
}