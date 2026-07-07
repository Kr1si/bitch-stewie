import { useEffect, useRef, useState } from "react";
import {
  Box, Button, CircularProgress, FormControl, InputLabel, MenuItem, Paper, Select,
  Stack, TextField, Typography, Chip,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import { DrawIoEmbed } from "react-drawio";
import { apiGet } from "../lib/api";
import { useStreamChat } from "../hooks/useStreamChat";
import SectionPanel from "../components/SectionPanel";
import ExampleUploader from "../components/ExampleUploader";
import ExampleGallery, { fetchExamples, type Example } from "../components/ExampleGallery";

type Project = { id: string; name: string; repo_path: string | null };
type Diagram = { name: string; modified: number };
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export default function Diagrams() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [diagrams, setDiagrams] = useState<Diagram[]>([]);
  const [current, setCurrent] = useState("");
  const [xml, setXml] = useState("");
  const [examples, setExamples] = useState<Example[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLog, setChatLog] = useState<{ role: string; text: string }[]>([]);
  const [draft, setDraft] = useState("");
  const logRef = useRef<HTMLDivElement>(null);

  const { busy, run, gate, tools } = useStreamChat();

  useEffect(() => { apiGet<Project[]>("/api/projects").then(setProjects).catch(() => {}); }, []);

  const loadDiagrams = (pid: string) => {
    if (!pid) { setDiagrams([]); setCurrent(""); setXml(""); return; }
    apiGet<Diagram[]>(`/api/projects/${pid}/diagrams`)
      .then((d) => {
        setDiagrams(d);
        if (!d.find((x) => x.name === current)) setCurrent(d[0]?.name ?? "");
      }).catch(() => setDiagrams([]));
  };

  useEffect(() => { loadDiagrams(projectId); }, [projectId]); // eslint-disable-line
  useEffect(() => {
    if (!projectId || !current) { setXml(""); return; }
    fetch(`${API_BASE}/api/projects/${projectId}/diagrams/${encodeURIComponent(current)}`)
      .then((r) => (r.ok ? r.text() : ""))
      .then(setXml).catch(() => setXml(""));
  }, [projectId, current]);

  useEffect(() => { logRef.current?.scrollTo({ top: 99999, behavior: "smooth" }); }, [chatLog, draft, busy]);

  const refresh = () => loadDiagrams(projectId);

  const send = async () => {
    if (!chatInput.trim() || busy || !projectId) return;
    const text = `For project ${projects.find(p => p.id === projectId)?.name ?? ""}: ${chatInput.trim()}`;
    setChatLog((p) => [...p, { role: "user", text: chatInput.trim() }]);
    setChatInput("");
    setDraft("");
    await run("/api/chat/stream", { message: text }, {
      onToken: (t) => setDraft((p) => p + t),
      onDone: (reply) => {
        setChatLog((p) => [...p, { role: "assistant", text: reply }]);
        setDraft("");
        // live refresh: the architect may have regenerated .drawio files
        loadDiagrams(projectId);
      },
    });
  };

  const resolveGate = async (approved: boolean) => {
    await run("/api/chat/resume/stream", { thread_id: "", approved, note: approved ? "" : "rejected" }, {
      onToken: (t) => setDraft((p) => p + t),
      onDone: (reply) => {
        setChatLog((p) => [...p, { role: "assistant", text: reply }]);
        setDraft("");
        loadDiagrams(projectId);
      },
    });
  };

  const reloadExamples = () => fetchExamples(projectId || undefined, "diagram").then(setExamples).catch(() => {});
  useEffect(() => { if (projectId !== undefined) reloadExamples(); }, [projectId]); // eslint-disable-line

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "calc(100vh - 112px)" }}>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>Diagrams</Typography>
        <FormControl size="small" sx={{ minWidth: 220 }}>
          <InputLabel>Project</InputLabel>
          <Select value={projectId} label="Project" onChange={(e) => setProjectId(e.target.value)}>
            <MenuItem value=""><em>select a project…</em></MenuItem>
            {projects.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 240 }} disabled={!diagrams.length}>
          <InputLabel>Diagram</InputLabel>
          <Select value={current} label="Diagram" onChange={(e) => setCurrent(e.target.value)}>
            {diagrams.map((d) => (
              <MenuItem key={d.name} value={d.name}>{d.name}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button size="small" startIcon={<RefreshIcon />} onClick={refresh} disabled={!projectId}>Refresh</Button>
      </Stack>

      <Box sx={{ display: "flex", gap: 2, flex: 1, minHeight: 0 }}>
        {/* Left: streaming chat with the architect */}
        <Paper sx={{ width: 380, display: "flex", flexDirection: "column", p: 1.5 }}>
          <Typography variant="subtitle2" sx={{ mb: 1, color: "text.secondary" }}>
            Chat with the architect — ask for diagram changes
          </Typography>
          <Box ref={logRef as never} sx={{ flex: 1, overflow: "auto", pr: 0.5 }}>
            {chatLog.map((m, i) => (
              <Box key={i} sx={{
                my: 0.5, p: 1, borderRadius: 1.5, fontSize: 13,
                bgcolor: m.role === "user" ? "primary.main" : "action.hover",
                color: m.role === "user" ? "primary.contrastText" : "text.primary",
                ml: m.role === "user" ? 4 : 0, mr: m.role === "user" ? 0 : 4,
                whiteSpace: "pre-wrap",
              }}>{m.text}</Box>
            ))}
            {draft && (
              <Box sx={{ my: 0.5, p: 1, borderRadius: 1.5, fontSize: 13,
                bgcolor: "action.hover", whiteSpace: "pre-wrap" }}>{draft}▍</Box>
            )}
            {tools.length > 0 && (
              <Stack direction="row" spacing={0.5} sx={{ flexWrap: "wrap", gap: 0.5, my: 0.5 }}>
                {tools.map((t, i) => <Chip key={i} label={t.name} size="small" variant="outlined" />)}
              </Stack>
            )}
            {busy && !draft && <CircularProgress size={14} sx={{ my: 1 }} />}
          </Box>

          {gate && (
            <Box sx={{ p: 1, border: 1, borderColor: "warning.main", borderRadius: 1.5, my: 1 }}>
              <Typography variant="caption" fontWeight={700}>Approval required</Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
                <Button size="small" variant="contained" color="success" onClick={() => resolveGate(true)}>Approve</Button>
                <Button size="small" variant="outlined" color="error" onClick={() => resolveGate(false)}>Reject</Button>
              </Stack>
            </Box>
          )}

          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
            <TextField size="small" fullWidth placeholder="change the diagram…"
              value={chatInput} onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()} disabled={busy || !projectId} />
            <Button size="small" variant="contained" onClick={send} disabled={busy || !projectId || !chatInput.trim()}>Send</Button>
          </Stack>
        </Paper>

        {/* Right: draw.io embed with live XML */}
        <Paper sx={{ flex: 1, minWidth: 0, overflow: "hidden" }}>
          {projectId ? (
            current && xml ? (
              <Box sx={{ height: "100%", width: "100%" }}>
                <DrawIoEmbed baseUrl="http://localhost:8080" xml={xml} />
              </Box>
            ) : (
              <Box sx={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Typography sx={{ color: "text.secondary" }}>
                  {diagrams.length ? "Loading…" : "No .drawio diagrams yet — ask the architect to regenerate them, or run update_diagrams."}
                </Typography>
              </Box>
            )
          ) : (
            <Box sx={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Typography sx={{ color: "text.secondary" }}>Select a project to view its diagrams.</Typography>
            </Box>
          )}
        </Paper>
      </Box>

      {/* Collapsible examples gallery */}
      <Box sx={{ mt: 1 }}>
        <SectionPanel title="Diagram examples" subtitle="reference diagrams the architect mimics"
          defaultExpanded={false}>
          <Stack direction="row" spacing={2}>
            <Box sx={{ width: 280 }}>
              <ExampleUploader kind="diagram" projects={projects} onUploaded={reloadExamples} />
            </Box>
            <Box sx={{ flex: 1 }}>
              <ExampleGallery examples={examples} onDeleted={reloadExamples} />
            </Box>
          </Stack>
        </SectionPanel>
      </Box>
    </Box>
  );
}