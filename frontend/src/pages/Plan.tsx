import { useEffect, useRef, useState } from "react";
import {
  Box, Button, CircularProgress, FormControl, InputLabel, List, ListItem,
  MenuItem, Paper, Select, Stack, TextField, Typography, Avatar, Alert,
} from "@mui/material";
import { apiGet, apiPost } from "../lib/api";
import { useStreamChat } from "../hooks/useStreamChat";

type Msg = { role: "user" | "assistant" | "gate"; text: string };
type Project = { id: string; name: string };
type Session = { id: string; thread_id: string; title: string };
type Focus = "" | "research-plan" | "coding-plan" | "design-plan";

const FOCUS_OPTIONS: { value: Focus; label: string }[] = [
  { value: "", label: "General" },
  { value: "research-plan", label: "Research" },
  { value: "coding-plan", label: "Coding" },
  { value: "design-plan", label: "Design" },
];

export default function Plan() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [draftText, setDraftText] = useState("");
  const [focus, setFocus] = useState<Focus>("");
  const [handoffResult, setHandoffResult] = useState<string | null>(null);
  const [handoffError, setHandoffError] = useState<string | null>(null);
  const [handoffBusy, setHandoffBusy] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  const { busy, run, gate } = useStreamChat();

  useEffect(() => {
    apiGet<Project[]>("/api/projects").then((rows) => {
      setProjects(rows);
      const stewie = rows.find((p) => p.name === "bitch-stewie");
      setProjectId((prev) => prev || (stewie ?? rows[0])?.id || "");
    }).catch(() => {});
  }, []);
  useEffect(() => {
    apiGet<Session[]>("/api/plan/sessions").then(setSessions).catch(() => {});
  }, [busy]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, draftText, busy]);

  const loadHistory = async (s: Session) => {
    setThreadId(s.thread_id);
    setHandoffResult(null);
    setHandoffError(null);
    const msgs = await apiGet<{ role: string; content: string }[]>(`/api/plan/sessions/${s.id}/messages`);
    setMessages(msgs.map((m) => ({ role: m.role as Msg["role"], text: m.content })));
  };

  const send = async () => {
    if (!input.trim() || busy) return;
    const tag = focus ? `[${focus}] ` : "";
    const text = `${tag}${input.trim()}`;
    setInput("");
    setMessages((p) => [...p, { role: "user", text }]);
    setDraftText("");

    await run("/api/plan/stream", { message: text, project_id: projectId, thread_id: threadId }, {
      onToken: (t) => setDraftText((p) => p + t),
      onDone: (reply) => {
        setMessages((p) => [...p, { role: "assistant", text: reply }]);
        setDraftText("");
        apiGet<Session[]>("/api/plan/sessions").then(setSessions).catch(() => {});
      },
    }).catch((e) => {
      setMessages((p) => [...p, { role: "assistant", text: `Error: ${String(e)}` }]);
      setDraftText("");
    });
  };

  const sendToOrchestrator = async () => {
    if (!threadId || !projectId) return;
    setHandoffBusy(true);
    setHandoffResult(null);
    setHandoffError(null);
    try {
      const res = await apiPost<{ orchestrator_thread_id: string; reply: string }>(
        "/api/plan/handoff", { thread_id: threadId, project_id: projectId },
      );
      setHandoffResult(
        `Sent to orchestrator — find it in the Chat page's thread list (thread ${res.orchestrator_thread_id.slice(0, 12)}).`,
      );
    } catch (e) {
      setHandoffError(String(e));
    } finally {
      setHandoffBusy(false);
    }
  };

  return (
    <Box sx={{ display: "flex", height: "calc(100vh - 112px)", gap: 2 }}>
      <Paper sx={{ width: 220, p: 1.5, display: { xs: "none", md: "block" } }}>
        <Typography variant="subtitle2" sx={{ px: 1, mb: 1 }}>Plans</Typography>
        <List dense>
          {sessions.map((s) => (
            <ListItem key={s.id} disablePadding sx={{ mb: 0.5 }}>
              <Button
                fullWidth size="small" onClick={() => loadHistory(s)}
                sx={{ justifyContent: "flex-start", textTransform: "none",
                  bgcolor: s.thread_id === threadId ? "primary.main" : "transparent",
                  color: s.thread_id === threadId ? "primary.contrastText" : "inherit" }}
              >
                {s.title || s.thread_id.slice(0, 10)}
              </Button>
            </ListItem>
          ))}
          {!sessions.length && <Typography variant="caption" sx={{ color: "text.secondary", px: 1 }}>No plans yet.</Typography>}
        </List>
        <Button fullWidth size="small" variant="outlined" sx={{ mt: 1 }}
          onClick={() => { setThreadId(null); setMessages([]); setHandoffResult(null); setHandoffError(null); }}>
          + New plan
        </Button>
      </Paper>

      <Stack direction="column" spacing={1} sx={{ flex: 1, minWidth: 0 }}>
        <Stack direction="row" spacing={1} alignItems="center">
          <FormControl size="small" sx={{ minWidth: 200 }} required error={!projectId}>
            <InputLabel>Project</InputLabel>
            <Select value={projectId} label="Project" onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>Plan focus</InputLabel>
            <Select value={focus} label="Plan focus" onChange={(e) => setFocus(e.target.value as Focus)}>
              {FOCUS_OPTIONS.map((o) => <MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>)}
            </Select>
          </FormControl>
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            Thread: {threadId ? threadId.slice(0, 12) : "new"}
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          <Button
            variant="outlined" size="small" disabled={!threadId || !projectId || handoffBusy}
            onClick={sendToOrchestrator}
          >
            {handoffBusy ? "Sending…" : "Send to Orchestrator"}
          </Button>
        </Stack>

        {handoffResult && <Alert severity="success" onClose={() => setHandoffResult(null)}>{handoffResult}</Alert>}
        {handoffError && <Alert severity="error" onClose={() => setHandoffError(null)}>{handoffError}</Alert>}

        <Paper sx={{ flex: 1, overflow: "auto", p: 2 }} ref={logRef as never}>
          {messages.map((m, i) => (
            <MsgRow key={i} m={m} />
          ))}
          {draftText && <MsgRow m={{ role: "assistant", text: draftText }} streaming />}
          {busy && !draftText && (
            <Stack direction="row" spacing={1} alignItems="center" sx={{ opacity: 0.7 }}>
              <CircularProgress size={14} /> <Typography variant="caption">working…</Typography>
            </Stack>
          )}
        </Paper>

        {gate && (
          <Paper sx={{ p: 2, borderColor: "warning.main", border: 1, borderRadius: 2 }}>
            <Typography fontWeight={700}>Gate — approval required</Typography>
            <pre style={{ margin: 0, fontSize: 12, maxHeight: 120, overflow: "auto" }}>
              {JSON.stringify(gate.requests, null, 2)}
            </pre>
          </Paper>
        )}

        <Stack direction="row" spacing={1}>
          <TextField
            fullWidth size="small"
            placeholder={projectId ? "Describe what you want to plan…" : "Pick a project first"}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            disabled={busy || !projectId}
          />
          <Button variant="contained" onClick={send} disabled={busy || !input.trim() || !projectId}>Send</Button>
        </Stack>
      </Stack>
    </Box>
  );
}

function MsgRow({ m, streaming }: { m: Msg; streaming?: boolean }) {
  const isUser = m.role === "user";
  return (
    <Stack direction="row" spacing={1} sx={{ justifyContent: isUser ? "flex-end" : "flex-start", my: 0.5 }}>
      {!isUser && <Avatar sx={{ width: 24, height: 24, fontSize: 12, bgcolor: "primary.main" }}>P</Avatar>}
      <Paper sx={{
        px: 1.5, py: 1, maxWidth: "80%",
        bgcolor: isUser ? "primary.main" : "background.paper",
        color: isUser ? "primary.contrastText" : "text.primary",
        border: isUser ? "none" : (t) => `1px solid ${t.palette.divider}`,
      }}>
        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
          {m.text}{streaming ? "▍" : ""}
        </Typography>
      </Paper>
    </Stack>
  );
}
