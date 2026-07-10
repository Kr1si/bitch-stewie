import { useState } from "react";
import {
  Box, Button, Chip, Dialog, DialogContent, DialogTitle, IconButton, Stack, Typography,
} from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import CloseIcon from "@mui/icons-material/Close";
import { apiGet } from "../lib/api";
import { usePoll } from "../hooks/usePoll";

type Run = {
  id: string; status: string; model: string; repo_path: string;
  review_iterations: number; result: Record<string, unknown>; created_at: string;
};
type Event = { type: string; payload: Record<string, unknown>; at: string };

const STATUS_COLOR: Record<string, "warning" | "info" | "success" | "error" | "default"> = {
  queued: "default", running: "info", reviewing: "warning",
  succeeded: "success", failed: "error", aborted: "error",
};

export default function Runs() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [events, setEvents] = useState<Event[] | null>(null);
  const [open, setOpen] = useState(false);
  const [sel, setSel] = useState<Run | null>(null);

  // lifecycle hooks write events near-real-time now: poll fast while a run is
  // active, ease off when everything is terminal
  const anyActive = runs.some((r) => r.status === "running" || r.status === "reviewing");
  const load = () => apiGet<Run[]>("/api/cc-runs").then(setRuns).catch(() => {});
  usePoll(load, anyActive ? 2000 : 15000, [anyActive]);

  const loadEvents = (id: string) =>
    apiGet<Event[]>(`/api/cc-runs/${id}/events`).then(setEvents).catch(() => setEvents([]));

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
      <Box sx={{ height: 560, width: "100%", bgcolor: "background.paper" }}>
        <DataGrid
          rows={runs} columns={cols} getRowId={(r) => r.id}
          pageSizeOptions={[10, 25, 50]} initialState={{
            pagination: { paginationModel: { pageSize: 25, page: 0 } },
          }}
        />
      </Box>

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>
          <Stack direction="row" alignItems="center" justifyContent="space-between">
            <span>Events — {sel?.id.slice(0, 8)}</span>
            <IconButton onClick={() => setOpen(false)}><CloseIcon /></IconButton>
          </Stack>
        </DialogTitle>
        <DialogContent dividers>
          <Box sx={{ maxHeight: 500, overflow: "auto", fontFamily: "monospace", fontSize: 12 }}>
            {(events ?? []).map((e, i) => (
              <Box key={i} sx={{ py: 0.3, borderBottom: (t) => `1px solid ${t.palette.divider}` }}>
                <span style={{ opacity: 0.6 }}>{e.at.slice(11, 19)}</span>{" "}
                <span style={{ color: "#7c5cff" }}>[{e.type}]</span>{" "}
                {JSON.stringify(e.payload).slice(0, 200)}
              </Box>
            ))}
            {events && !events.length && <Typography sx={{ color: "text.secondary" }}>No events.</Typography>}
          </Box>
        </DialogContent>
      </Dialog>
    </Box>
  );
}