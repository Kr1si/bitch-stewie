import { useEffect, useRef, useState } from "react";
import {
  Alert, Avatar, Box, Button, Chip, CircularProgress, Divider, IconButton, Paper,
  Stack, TextField, Tooltip, Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import AutoAwesomeMotionIcon from "@mui/icons-material/AutoAwesomeMotion";
import DeleteIcon from "@mui/icons-material/Delete";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SendIcon from "@mui/icons-material/Send";
import {
  deleteGoal, listGoals, patchGoal, streamGoalChat, type Goal,
} from "../lib/api";

const KIND_COLOR: Record<string, "success" | "info" | "warning" | "default"> = {
  research: "success", coding: "info", testing: "warning",
};

type Msg = { role: "user" | "assistant"; text: string };

export default function Goals() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // interview state
  const [creating, setCreating] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [chatting, setChatting] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  const refresh = async () => {
    setLoading(true);
    try { setGoals(await listGoals()); } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  };

  useEffect(() => { refresh(); }, []);
  useEffect(() => { logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" }); }, [msgs, chatting]);

  const toggle = async (g: Goal) => {
    const next = g.status === "active" ? "paused" : "active";
    try { await patchGoal(g.id, { status: next }); await refresh(); } catch (e) { setError(String(e)); }
  };

  const remove = async (g: Goal) => {
    try { await deleteGoal(g.id); await refresh(); } catch (e) { setError(String(e)); }
  };

  const startCreating = () => {
    setCreating(true);
    setThreadId(null);
    setMsgs([]);
    setInput("");
  };

  const send = async () => {
    if (!input.trim() || chatting) return;
    const text = input.trim();
    setMsgs((m) => [...m, { role: "user", text }]);
    setInput("");
    setChatting(true);
    const tid = threadId || undefined;
    let assistant = "";
    try {
      await streamGoalChat(
        { message: text, thread_id: tid },
        {
          onToken: (t) => { assistant += t; setMsgs((m) => { const c = [...m]; const last = c[c.length - 1]; if (last?.role === "assistant") { c[c.length - 1] = { ...last, text: last.text + t }; } else { c.push({ role: "assistant", text: t }); } return c; }); },
          onDone: () => setThreadId(tid || crypto.randomUUID()),
          onError: (e) => setError(e),
        },
      );
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError(String(e));
    } finally {
      setChatting(false);
    }
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "calc(100vh - 112px)", gap: 2 }}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Avatar sx={{ bgcolor: "primary.main", width: 28, height: 28 }}>
          <AutoAwesomeMotionIcon sx={{ fontSize: 18 }} />
        </Avatar>
        <Typography variant="h6" sx={{ fontWeight: 700 }}>Goals</Typography>
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          scheduleable objectives for the autonomous agent
        </Typography>
      </Stack>

      {error && <Alert severity="error" sx={{ whiteSpace: "pre-wrap" }}>{error}</Alert>}

      <Paper sx={{ p: 2 }}>
        <Stack direction="row" alignItems="center" sx={{ mb: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, flexGrow: 1 }}>
            {loading ? "loading…" : `${goals.length} goal(s)`}
          </Typography>
          <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={startCreating}>
            New Goal
          </Button>
        </Stack>
        {goals.length === 0 && (
          <Typography variant="body2" sx={{ color: "text.secondary", py: 2 }}>
            No goals yet. Click <strong>New Goal</strong> to create one with the AI interviewer.
          </Typography>
        )}
        <Stack spacing={1}>
          {goals.map((g) => (
            <Paper key={g.id} variant="outlined" sx={{ p: 1.5 }}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Chip size="small" color={KIND_COLOR[g.kind] || "default"} label={g.kind} />
                <Typography variant="body2" sx={{ fontWeight: 600, flexGrow: 1 }}>{g.title}</Typography>
                <Chip size="small" variant={g.status === "active" ? "filled" : "outlined"}
                  color={g.status === "active" ? "success" : "default"} label={g.status} />
                <Typography variant="caption" sx={{ color: "text.secondary", fontFamily: "monospace" }}>
                  {g.cadence}
                </Typography>
                <Tooltip title={g.status === "active" ? "pause" : "resume"}>
                  <IconButton size="small" onClick={() => toggle(g)}>
                    {g.status === "active" ? <PauseIcon fontSize="small" /> : <PlayArrowIcon fontSize="small" />}
                  </IconButton>
                </Tooltip>
                <Tooltip title="delete">
                  <IconButton size="small" color="error" onClick={() => remove(g)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Stack>
              {g.description && (
                <Typography variant="caption" sx={{ color: "text.secondary", mt: 0.5, display: "block" }}>
                  {g.description}
                </Typography>
              )}
            </Paper>
          ))}
        </Stack>
      </Paper>

      {creating && (
        <Paper sx={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
          <Stack direction="row" alignItems="center" sx={{ px: 2, py: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>New Goal — AI Interviewer</Typography>
            <Typography variant="caption" sx={{ color: "text.secondary", ml: 1 }}>asks questions until the goal is defined</Typography>
          </Stack>
          <Divider />
          <Box sx={{ flex: 1, overflow: "auto", p: 2 }} ref={logRef}>
            {msgs.length === 0 && (
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                Describe what you want to automate. The interviewer will ask a few questions, then create the goal.
              </Typography>
            )}
            {msgs.map((m, i) => (
              <Box key={i} sx={{ mb: 1.5, display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
                <Paper variant="outlined" sx={{ p: 1, maxWidth: "75%", bgcolor: m.role === "user" ? "primary.dark" : "background.default" }}>
                  <Typography component="pre" sx={{ fontFamily: "monospace", fontSize: 13, whiteSpace: "pre-wrap", margin: 0 }}>
                    {m.text}
                  </Typography>
                </Paper>
              </Box>
            ))}
            {chatting && <CircularProgress size={16} />}
          </Box>
          <Divider />
          <Stack direction="row" spacing={1} sx={{ p: 1 }}>
            <TextField fullWidth size="small" placeholder="your answer…" value={input}
              onChange={(e) => setInput(e.target.value)} disabled={chatting}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
            <Button variant="contained" onClick={send} disabled={chatting || !input.trim()} endIcon={<SendIcon />}>
              Send
            </Button>
          </Stack>
        </Paper>
      )}
    </Box>
  );
}
