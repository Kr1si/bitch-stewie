import { useEffect, useRef, useState } from "react";
import {
  Box, Button, Chip, CircularProgress, FormControl, InputLabel, List, ListItem,
  MenuItem, Paper, Select, Stack, TextField, Typography, Avatar,
} from "@mui/material";
import BuildIcon from "@mui/icons-material/Build";
import GavelIcon from "@mui/icons-material/Gavel";
import { apiGet } from "../lib/api";
import { useStreamChat } from "../hooks/useStreamChat";

type Msg = { role: "user" | "assistant" | "tool" | "gate"; text: string; tools?: string[] };
type Project = { id: string; name: string };
type Session = { id: string; thread_id: string; title: string };

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [draftText, setDraftText] = useState(""); // streaming assistant text
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
    apiGet<Session[]>("/api/chat/sessions").then(setSessions).catch(() => {});
  }, [busy]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, draftText, busy]);

  const loadHistory = async (s: Session) => {
    setThreadId(s.thread_id);
    const msgs = await apiGet<{ role: string; content: string }[]>(`/api/chat/sessions/${s.id}/messages`);
    setMessages(msgs.map((m) => ({ role: m.role as Msg["role"], text: m.content })));
  };

  const send = async () => {
    if (!input.trim() || busy || !projectId) return;
    const text = input.trim();
    setInput("");
    setMessages((p) => [...p, { role: "user", text }]);
    setDraftText("");

    await run("/api/chat/stream", { message: text, project_id: projectId, thread_id: threadId }, {
      onToken: (t) => setDraftText((p) => p + t),
      onDone: (reply) => {
        setMessages((p) => [...p, { role: "assistant", text: reply }]);
        setDraftText("");
        // capture the thread id for subsequent turns via a re-fetch of sessions
        apiGet<Session[]>("/api/chat/sessions").then(setSessions).catch(() => {});
      },
    }).catch((e) => {
      setMessages((p) => [...p, { role: "assistant", text: `Error: ${String(e)}` }]);
      setDraftText("");
    });
  };

  const gate2 = async (approved: boolean) => {
    if (!threadId) return;
    setMessages((p) => [...p, { role: "gate", text: approved ? "approved → resuming" : "rejected → resuming" }]);
    setDraftText("");
    await run("/api/chat/resume/stream", { thread_id: threadId, approved, note: approved ? "" : "rejected" }, {
      onToken: (t) => setDraftText((p) => p + t),
      onDone: (reply) => {
        setMessages((p) => [...p, { role: "assistant", text: reply }]);
        setDraftText("");
      },
    });
  };

  return (
    <Box sx={{ display: "flex", height: "calc(100vh - 112px)", gap: 2 }}>
      <Paper sx={{ width: 220, p: 1.5, display: { xs: "none", md: "block" } }}>
        <Typography variant="subtitle2" sx={{ px: 1, mb: 1 }}>Threads</Typography>
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
          {!sessions.length && <Typography variant="caption" sx={{ color: "text.secondary", px: 1 }}>No threads yet.</Typography>}
        </List>
        <Button fullWidth size="small" variant="outlined" sx={{ mt: 1 }}
          onClick={() => { setThreadId(null); setMessages([]); }}>+ New thread</Button>
      </Paper>

      <Stack direction="column" spacing={1} sx={{ flex: 1, minWidth: 0 }}>
        <Stack direction="row" spacing={1} alignItems="center">
          <FormControl size="small" sx={{ minWidth: 200 }} required error={!projectId}>
            <InputLabel>Project</InputLabel>
            <Select value={projectId} label="Project" onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
            </Select>
          </FormControl>
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            Thread: {threadId ? threadId.slice(0, 12) : "new"}
          </Typography>
        </Stack>

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
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
              <GavelIcon color="warning" />
              <Typography fontWeight={700}>Milestone gate — approval required</Typography>
            </Stack>
            <pre style={{ margin: 0, fontSize: 12, maxHeight: 120, overflow: "auto" }}>
              {JSON.stringify(gate.requests, null, 2)}
            </pre>
            <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
              <Button variant="contained" color="success" onClick={() => gate2(true)}>Approve</Button>
              <Button variant="outlined" color="error" onClick={() => gate2(false)}>Reject</Button>
            </Stack>
          </Paper>
        )}

        <Stack direction="row" spacing={1}>
          <TextField
            fullWidth size="small"
            placeholder={projectId ? "Ask the orchestrator…" : "Pick a project first"}
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
  if (m.role === "tool" || (m.role === "assistant" && m.tools?.length)) {
    return (
      <Stack direction="row" spacing={0.5} sx={{ flexWrap: "wrap", gap: 0.5, my: 0.5 }}>
        {(m.tools ?? []).map((t, i) => (
          <Chip key={i} icon={<BuildIcon />} label={t} size="small" variant="outlined" />
        ))}
      </Stack>
    );
  }
  const isUser = m.role === "user";
  return (
    <Stack direction="row" spacing={1} sx={{ justifyContent: isUser ? "flex-end" : "flex-start", my: 0.5 }}>
      {!isUser && <Avatar sx={{ width: 24, height: 24, fontSize: 12, bgcolor: "primary.main" }}>S</Avatar>}
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