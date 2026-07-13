import { useEffect, useRef, useState } from "react";
import {
  Box, Button, CircularProgress, FormControl, InputLabel, MenuItem, Paper,
  Select, Stack, TextField, Typography, Alert, Avatar,
} from "@mui/material";
import TravelExploreIcon from "@mui/icons-material/TravelExplore";
import StopIcon from "@mui/icons-material/Stop";
import { apiGet, streamResearch } from "../lib/api";

type Project = { id: string; name: string };
type Status = "idle" | "running" | "done" | "error";

export default function Research() {
  const [goal, setGoal] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [report, setReport] = useState("");
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiGet<Project[]>("/api/projects").then(setProjects).catch(() => {});
  }, []);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [report, status]);

  const run = async () => {
    if (!goal.trim() || status === "running") return;
    setStatus("running");
    setReport("");
    setError("");
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const project = projects.find((p) => p.id === projectId)?.name ?? "";
    try {
      await streamResearch(
        "/api/research/deep/stream",
        { goal: goal.trim(), project },
        {
          onStart: () => setStatus("running"),
          onDone: (r) => { setReport(r); setStatus("done"); },
          onError: (e) => { setError(e); setStatus("error"); },
        },
        ctrl.signal,
      );
    } catch (e) {
      if (!ctrl.signal.aborted) { setError(String(e)); setStatus("error"); }
      else { setStatus("idle"); }
    } finally {
      abortRef.current = null;
    }
  };

  const stop = () => {
    abortRef.current?.abort();
    setStatus("idle");
  };

  const running = status === "running";

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "calc(100vh - 112px)", gap: 2 }}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Avatar sx={{ bgcolor: "primary.main", width: 28, height: 28 }}>
          <TravelExploreIcon sx={{ fontSize: 18 }} />
        </Avatar>
        <Typography variant="h6" sx={{ fontWeight: 700 }}>Deep Research</Typography>
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          runs Claude Code&apos;s native <code>/deep-research</code> — minutes, cited Markdown report
        </Typography>
      </Stack>

      <FormControl size="small" sx={{ minWidth: 200 }}>
        <InputLabel>Project (optional)</InputLabel>
        <Select value={projectId} label="Project (optional)"
          onChange={(e) => setProjectId(e.target.value)} disabled={running}>
          <MenuItem value=""><em>none</em></MenuItem>
          {projects.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
        </Select>
      </FormControl>

      <TextField
        fullWidth multiline minRows={3} size="small"
        placeholder="State the research goal — e.g. 'Compare vector DB options for a 10M-doc RAG corpus, with cost and latency citations'"
        value={goal}
        onChange={(e) => setGoal(e.target.value)}
        disabled={running}
        onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) run(); }}
      />

      <Stack direction="row" spacing={1}>
        <Button variant="contained" onClick={run} disabled={running || !goal.trim()}
          startIcon={<TravelExploreIcon />}>
          Run Deep Research
        </Button>
        {running && (
          <Button variant="outlined" color="error" onClick={stop} startIcon={<StopIcon />}>
            Abort
          </Button>
        )}
        {status === "done" && (
          <Button variant="text" onClick={() => navigator.clipboard?.writeText(report)}>
            Copy report
          </Button>
        )}
      </Stack>

      {error && <Alert severity="error" sx={{ whiteSpace: "pre-wrap" }}>{error}</Alert>}

      <Paper sx={{ flex: 1, overflow: "auto", p: 2 }} ref={logRef as never}>
        {running && !report && (
          <Stack direction="row" spacing={1} alignItems="center" sx={{ opacity: 0.7, mb: 2 }}>
            <CircularProgress size={16} />
            <Typography variant="body2">researching… this can take several minutes</Typography>
          </Stack>
        )}
        {report && (
          <Typography component="pre" sx={{
            fontFamily: "monospace", fontSize: 13, lineHeight: 1.5,
            whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0,
          }}>
            {report}
          </Typography>
        )}
        {!report && !running && status !== "error" && (
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            Enter a goal above and run a deep research pass. The report is saved to the
            knowledge base automatically.
          </Typography>
        )}
      </Paper>
    </Box>
  );
}
