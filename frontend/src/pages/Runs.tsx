import { useEffect, useState } from "react";
import {
  Alert, Box, Button, Chip, Collapse, Dialog, DialogContent, DialogTitle,
  IconButton, MenuItem, Paper, Stack, TextField, Typography,
} from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import CloseIcon from "@mui/icons-material/Close";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import PlayCircleOutlineIcon from "@mui/icons-material/PlayCircleOutline";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import BoltOutlinedIcon from "@mui/icons-material/BoltOutlined";
import { apiGet, apiPost } from "../lib/api";
import { usePoll } from "../hooks/usePoll";
import {
  groupEvents, laneDuration, timeLabel,
  type Lane, type LaneItem, type RunEvent,
} from "../lib/eventsGrouping";

type Run = {
  id: string; status: string; model: string; repo_path: string;
  review_iterations: number; result: Record<string, unknown>; created_at: string;
};
type ProjectOpt = { id: string; name: string; repo_path: string | null };

const STATUS_COLOR: Record<string, "warning" | "info" | "success" | "error" | "default"> = {
  queued: "default", running: "info", reviewing: "warning",
  succeeded: "success", failed: "error", aborted: "error",
};

function StartRunForm({ onStarted }: { onStarted: () => void }) {
  const [projects, setProjects] = useState<ProjectOpt[]>([]);
  const [projectId, setProjectId] = useState("");
  const [goal, setGoal] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<ProjectOpt[]>("/api/projects").then((rows) => {
      setProjects(rows);
      // bitch-stewie is seeded as a project preset so self-improvement runs
      // are the default target; fall back to the first project otherwise.
      const stewie = rows.find((p) => p.name === "bitch-stewie");
      setProjectId((stewie ?? rows[0])?.id ?? "");
    }).catch(() => {});
  }, []);

  const start = async () => {
    if (!projectId || !goal.trim()) return;
    setBusy(true); setError(null);
    try {
      await apiPost("/api/cc-runs", { project_id: projectId, goal: goal.trim() });
      setGoal("");
      onStarted();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "flex-start" }}>
        <TextField
          select label="Project" value={projectId} onChange={(e) => setProjectId(e.target.value)}
          sx={{ minWidth: 220 }} size="small"
        >
          {projects.map((p) => (
            <MenuItem key={p.id} value={p.id} disabled={!p.repo_path}>
              {p.name}{!p.repo_path ? " (no repo_path)" : ""}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Goal" placeholder="e.g. add a dark mode toggle to the settings page"
          value={goal} onChange={(e) => setGoal(e.target.value)}
          fullWidth multiline minRows={1} size="small"
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); start(); } }}
        />
        <Button variant="contained" onClick={start} disabled={busy || !projectId || !goal.trim()}
          sx={{ whiteSpace: "nowrap" }}>
          {busy ? "Starting..." : "Run"}
        </Button>
      </Stack>
      {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}
    </Paper>
  );
}

// --- Events dialog: per-agent lanes ---------------------------------------

// Accent colors for subagent lanes; main orchestrator uses the theme primary.
const LANE_COLORS = [
  "#7c5cff", "#2f7d32", "#c06000", "#0277bd",
  "#ad1457", "#6a1b9a", "#00838f", "#5d4037",
];
const colorCache = new Map<string, string>();
function laneAccent(key: string, isMain: boolean): string {
  if (isMain) return "#7c5cff";
  const hit = colorCache.get(key);
  if (hit) return hit;
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  const c = LANE_COLORS[h % LANE_COLORS.length];
  colorCache.set(key, c);
  return c;
}

const NOTE_COLOR: Record<string, "info" | "warning" | "success" | "default"> = {
  stop: "success",
  notification: "info",
  permission: "warning",
};

/** One paired pre_tool/post_tool block: tool name + args summary, output collapsed. */
function ToolBlock({ item }: { item: Extract<LaneItem, { kind: "tool" }> }) {
  const [open, setOpen] = useState(false);
  const running = item.output === null;
  return (
    <Box sx={{ mb: 0.5 }}>
      <Stack
        direction="row" spacing={1} alignItems="center"
        onClick={() => setOpen((o) => !o)}
        sx={{ cursor: "pointer", "&:hover": { opacity: 0.85 } }}
      >
        {running
          ? <PlayCircleOutlineIcon fontSize="small" color="action" />
          : <CheckCircleIcon fontSize="small" color="success" />}
        <Chip label={item.tool} size="small" variant="outlined" />
        <Typography
          variant="caption" noWrap sx={{ flex: 1, fontFamily: "monospace", color: "text.secondary" }}
        >
          {item.input || "(no args)"}
        </Typography>
        {running
          ? <Chip label="running" size="small" color="info" variant="outlined" />
          : (item.input || item.output ? (open ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />) : null)}
      </Stack>
      <Collapse in={open} sx={{ pl: 4 }}>
        {item.input && (
          <Typography variant="caption" component="pre" sx={{ m: 0, mt: 0.5, whiteSpace: "pre-wrap", wordBreak: "break-word", fontFamily: "monospace" }}>
            <Box component="span" sx={{ color: "text.secondary" }}>args: </Box>{item.input}
          </Typography>
        )}
        {item.output != null && (
          <Typography variant="caption" component="pre" sx={{ m: 0, mt: 0.5, whiteSpace: "pre-wrap", wordBreak: "break-word", fontFamily: "monospace" }}>
            <Box component="span" sx={{ color: "text.secondary" }}>out: </Box>{item.output}
          </Typography>
        )}
      </Collapse>
    </Box>
  );
}

/** A single lane (main orchestrator, or one subagent instance). */
function LaneView({ lane }: { lane: Lane }) {
  const [open, setOpen] = useState(!lane.isMain ? false : true);
  const accent = laneAccent(lane.key, lane.isMain);
  const dur = laneDuration(lane);
  const subId = lane.agentId ? lane.agentId.slice(0, 8) : "";

  const header = (
    <Stack
      direction="row" spacing={1} alignItems="center"
      onClick={() => setOpen((o) => !o)}
      sx={{ cursor: "pointer", py: 0.5 }}
    >
      {!lane.isMain && (open ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />)}
      <Chip
        label={lane.isMain ? lane.label : `${lane.label}${subId ? ` · ${subId}` : ""}`}
        size="small"
        sx={{ bgcolor: accent, color: "#fff", fontWeight: 600 }}
      />
      {lane.isMain && <Typography variant="caption" sx={{ color: "text.secondary" }}>main orchestrator</Typography>}
      {!lane.isMain && dur && (
        <Typography variant="caption" sx={{ color: "text.secondary" }}>⏱ {dur}</Typography>
      )}
      {!lane.isMain && lane.running && (
        <Chip label="still running" size="small" color="warning" variant="outlined" />
      )}
      <Typography variant="caption" sx={{ color: "text.secondary", ml: "auto" }}>
        {lane.items.length} item{lane.items.length === 1 ? "" : "s"}
      </Typography>
    </Stack>
  );

  if (lane.isMain) {
    // main lane: always-expanded section, no collapse toggle
    return (
      <Box sx={{ borderLeft: 3, borderColor: accent, pl: 1.5, mb: 1.5 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ py: 0.5 }}>
          <Chip label={lane.label} size="small" sx={{ bgcolor: accent, color: "#fff", fontWeight: 600 }} />
          <Typography variant="caption" sx={{ color: "text.secondary" }}>main orchestrator</Typography>
          <Typography variant="caption" sx={{ color: "text.secondary", ml: "auto" }}>
            {lane.items.length} item{lane.items.length === 1 ? "" : "s"}
          </Typography>
        </Stack>
        <LaneItems lane={lane} />
      </Box>
    );
  }

  // subagent lane: collapsible, collapsed by default; activity nested/indented
  return (
    <Box sx={{ borderLeft: 3, borderColor: accent, pl: 1.5, mb: 1.5 }}>
      {header}
      <Collapse in={open}>
        <Box sx={{ pl: 1, pt: 0.5 }}>
          <LaneItems lane={lane} />
        </Box>
      </Collapse>
    </Box>
  );
}

function LaneItems({ lane }: { lane: Lane }) {
  if (!lane.items.length) {
    return <Typography variant="caption" sx={{ color: "text.secondary", pl: 1 }}>no activity</Typography>;
  }
  return (
    <Stack spacing={0.5} sx={{ pt: 0.5 }}>
      {lane.items.map((it) => <LaneItemView key={it.id} item={it} />)}
    </Stack>
  );
}

function LaneItemView({ item }: { item: LaneItem }) {
  if (item.kind === "tool") return <ToolBlock item={item} />;
  if (item.kind === "text") {
    return (
      <Typography variant="body2" sx={{ fontStyle: "italic", color: "text.secondary", pl: 1 }}>
        {item.text}
      </Typography>
    );
  }
  // note
  return (
    <Stack direction="row" spacing={1} alignItems="center" sx={{ pl: 1 }}>
      <BoltOutlinedIcon fontSize="small" color="action" />
      <Chip label={item.noteType} size="small" color={NOTE_COLOR[item.noteType] ?? "default"} variant="outlined" />
      <Typography variant="caption" sx={{ color: "text.secondary", fontFamily: "monospace" }}>
        {item.text}
      </Typography>
    </Stack>
  );
}

function EventsDialog({
  open, runId, events, onClose,
}: {
  open: boolean; runId?: string; events: RunEvent[] | null; onClose: () => void;
}) {
  const lanes = events ? groupEvents(events) : [];

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <span>Events — {runId?.slice(0, 8)}</span>
          <IconButton onClick={onClose}><CloseIcon /></IconButton>
        </Stack>
      </DialogTitle>
      <DialogContent dividers>
        <Box sx={{ maxHeight: 520, overflow: "auto", fontSize: 12 }}>
          {lanes.map((lane) => <LaneView key={lane.key} lane={lane} />)}
          {events && !events.length && (
            <Typography sx={{ color: "text.secondary" }}>No events.</Typography>
          )}
          {events && events.length > 0 && (
            <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mt: 1 }}>
              {events.length} events · subagent lanes collapsed by default · {timeLabel(events[0].at)} → {timeLabel(events[events.length - 1].at)}
            </Typography>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  );
}

export default function Runs() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [events, setEvents] = useState<RunEvent[] | null>(null);
  const [open, setOpen] = useState(false);
  const [sel, setSel] = useState<Run | null>(null);

  // lifecycle hooks write events near-real-time now: poll fast while a run is
  // active, ease off when everything is terminal
  const anyActive = runs.some((r) => r.status === "running" || r.status === "reviewing");
  const load = () => apiGet<Run[]>("/api/cc-runs").then(setRuns).catch(() => {});
  usePoll(load, anyActive ? 2000 : 15000, [anyActive]);

  const loadEvents = (id: string) =>
    apiGet<RunEvent[]>(`/api/cc-runs/${id}/events`).then(setEvents).catch(() => setEvents([]));

  // keep the open events dialog live while its run is active
  usePoll(
    async () => { if (open && sel && anyActive) await loadEvents(sel.id); },
    2000, [open, sel?.id, anyActive],
  );

  const show = async (r: Run) => {
    setSel(r); setOpen(true);
    await loadEvents(r.id);
  };

  const cols: GridColDef<Run>[] = [
    { field: "created_at", headerName: "When", width: 160,
      valueFormatter: (v) => new Date(v as string).toLocaleString() },
    { field: "status", headerName: "Status", width: 110,
      renderCell: (p) => <Chip label={p.value} color={STATUS_COLOR[p.value] ?? "default"} size="small" /> },
    { field: "repo_path", headerName: "Repo", width: 180, flex: 1,
      valueFormatter: (v) => String(v).split(/[\\/]/).pop() },
    { field: "model", headerName: "Model", width: 130 },
    { field: "review_iterations", headerName: "Reviews", width: 80, type: "number" },
    { field: "branch", headerName: "Branch", width: 140,
      valueGetter: (_v, r) => String(r.result?.branch ?? "") },
    { field: "act", headerName: "", width: 90, sortable: false, disableColumnMenu: true,
      renderCell: (p) => <Button size="small" onClick={() => show(p.row)}>events</Button> },
  ];

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2, fontWeight: 700 }}>Claude Code Runs</Typography>
      <StartRunForm onStarted={load} />
      <Box sx={{ height: 560, width: "100%", bgcolor: "background.paper" }}>
        <DataGrid
          rows={runs} columns={cols} getRowId={(r) => r.id}
          pageSizeOptions={[10, 25, 50]} initialState={{
            pagination: { paginationModel: { pageSize: 25, page: 0 } },
          }}
        />
      </Box>

      <EventsDialog
        open={open} runId={sel?.id} events={events} onClose={() => setOpen(false)}
      />
    </Box>
  );
}