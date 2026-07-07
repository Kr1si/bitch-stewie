import { useRef, useState } from "react";
import { apiPost } from "../lib/api";

type Msg = { role: "user" | "assistant" | "gate"; text: string };
type ChatResp = {
  thread_id: string;
  reply: string;
  pending: boolean;
  interrupt: { requests: unknown[] } | null;
};

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [pendingGate, setPendingGate] = useState(false);
  const thread = useRef<string | null>(null);

  const push = (m: Msg) => setMessages((prev) => [...prev, m]);

  const handleResp = (r: ChatResp) => {
    thread.current = r.thread_id;
    if (r.pending) {
      setPendingGate(true);
      push({ role: "gate", text: JSON.stringify(r.interrupt?.requests, null, 2) });
    } else if (r.reply) {
      push({ role: "assistant", text: r.reply });
    }
  };

  const send = async () => {
    if (!input.trim() || busy) return;
    const text = input.trim();
    setInput("");
    push({ role: "user", text });
    setBusy(true);
    try {
      handleResp(await apiPost<ChatResp>("/api/chat", { message: text, thread_id: thread.current }));
    } catch (e) {
      push({ role: "assistant", text: `Error: ${String(e)}` });
    } finally {
      setBusy(false);
    }
  };

  const gate = async (approved: boolean) => {
    setPendingGate(false);
    setBusy(true);
    try {
      handleResp(await apiPost<ChatResp>("/api/chat/resume", {
        thread_id: thread.current, approved, note: approved ? "" : "rejected from web UI",
      }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="chat">
      <h2>Chat</h2>
      <div className="chat-log">
        {messages.map((m, i) => (
          <div key={i} className={`msg msg-${m.role}`}>
            {m.role === "gate" ? (
              <div>
                <strong>Milestone gate — approval required</strong>
                <pre>{m.text}</pre>
              </div>
            ) : (
              <span><b>{m.role === "user" ? "you" : "assistant"}:</b> {m.text}</span>
            )}
          </div>
        ))}
        {busy && <div className="msg msg-assistant">…working</div>}
      </div>
      {pendingGate && (
        <div className="gate-actions">
          <button onClick={() => gate(true)}>Approve</button>
          <button onClick={() => gate(false)}>Reject</button>
        </div>
      )}
      <div className="chat-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask the orchestrator…"
          disabled={busy || pendingGate}
        />
        <button onClick={send} disabled={busy || pendingGate}>Send</button>
      </div>
    </section>
  );
}
