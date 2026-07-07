import { useEffect, useState } from "react";
import {
  Box, Grid, Stack, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Typography, Chip, Button, Link,
} from "@mui/material";
import FolderIcon from "@mui/icons-material/Folder";
import PlayCircleIcon from "@mui/icons-material/PlayCircle";
import PendingActionsIcon from "@mui/icons-material/PendingActions";
import GavelIcon from "@mui/icons-material/Gavel";
import HubIcon from "@mui/icons-material/Hub";
import SourceIcon from "@mui/icons-material/Source";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip,
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { apiGet, apiPost } from "../lib/api";
import StatCard from "../components/StatCard";
import SectionPanel from "../components/SectionPanel";
import { usePoll } from "../hooks/usePoll";

type Stats = {
  projects: number; runs_total: number; runs_by_status: Record<string, number>;
  pending_approvals: number; decisions: number; kb_points: number; kb_sources: number;
  collections: { name: string; points: number; sources: { source: string; chunks: number }[] }[];
  recent: {
    runs: { id: string; status: string; model: string; repo_path: string; created_at: string }[];
    approvals: { id: string; kind: string; status: string; created_at: string }[];
    decisions: { id: string; title: string; status: string; created_at: string }[];
  };
};

type Project = { id: string; name: string; status: string; repo_path: string | null; description: string };

const PIE_COLORS = ["#7c5cff", "#26c6da", "#ffb74d", "#ef5350", "#66bb6a", "#90a4ae"];

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [repo, setRepo] = useState("");

  const loadStats = () => apiGet<Stats>("/api/stats").then(setStats).catch(() => {});
  const loadProjects = () => apiGet<Project[]>("/api/projects").then(setProjects).catch(() => {});
  usePoll(loadStats, 10000);
  useEffect(() => { loadProjects(); }, []); // eslint-disable-line

  const browse = async () => {
    try {
      const r = await apiGet<{ path: string | null }>("/api/util/pick-folder");
      if (r.path) setRepo(r.path);
    } catch (e) { console.error(e); }
  };
  const create = async () => {
    if (!name.trim()) return;
    await apiPost("/api/projects", { name, repo_path: repo || null });
    setName(""); setRepo(""); loadProjects(); loadStats();
  };

  const runStatusRows = stats ? Object.entries(stats.runs_by_status) : [];
  const // bucket recent runs by day for the area chart
    byDay = (stats?.recent.runs ?? []).reduce<Record<string, number>>((acc, r) => {
      const d = r.created_at.slice(0, 10);
      acc[d] = (acc[d] ?? 0) + 1; return acc;
    }, {});
  const areaData = Object.entries(byDay).sort().map(([day, n]) => ({ day, runs: n }));

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2, fontWeight: 700 }}>Dashboard</Typography>
      <Grid container spacing={2}>
        <Grid size={{ xs: 6, md: 2 }}>
          <StatCard icon={<FolderIcon />} label="Projects" value={stats?.projects ?? "—"} />
        </Grid>
        <Grid size={{ xs: 6, md: 2 }}>
          <StatCard icon={<PlayCircleIcon />} label="CC Runs" value={stats?.runs_total ?? "—"} />
        </Grid>
        <Grid size={{ xs: 6, md: 2 }}>
          <StatCard icon={<PendingActionsIcon />} label="Pending" value={stats?.pending_approvals ?? "—"} />
        </Grid>
        <Grid size={{ xs: 6, md: 2 }}>
          <StatCard icon={<GavelIcon />} label="Decisions" value={stats?.decisions ?? "—"} />
        </Grid>
        <Grid size={{ xs: 6, md: 2 }}>
          <StatCard icon={<HubIcon />} label="KB Chunks" value={stats?.kb_points ?? "—"} />
        </Grid>
        <Grid size={{ xs: 6, md: 2 }}>
          <StatCard icon={<SourceIcon />} label="KB Sources" value={stats?.kb_sources ?? "—"} />
        </Grid>
      </Grid>

      <Grid container spacing={2} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 4 }}>
          <SectionPanel title="Runs by status">
            {runStatusRows.length ? (
              <Box sx={{ height: 240 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={runStatusRows.map(([k, v]) => ({ name: k, value: v }))}
                      dataKey="value" nameKey="name" innerRadius={45} outerRadius={80} paddingAngle={2}>
                      {runStatusRows.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                    </Pie>
                    <Tooltip /><Legend />
                  </PieChart>
                </ResponsiveContainer>
              </Box>
            ) : <Typography sx={{ color: "text.secondary" }}>No runs yet.</Typography>}
          </SectionPanel>
        </Grid>

        <Grid size={{ xs: 12, md: 8 }}>
          <SectionPanel title="Runs over time" subtitle="recent CC runs bucketed by day">
            <Box sx={{ height: 240 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={areaData}>
                  <defs>
                    <linearGradient id="rg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#7c5cff" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="#7c5cff" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#8884" />
                  <XAxis dataKey="day" fontSize={11} />
                  <YAxis allowDecimals={false} fontSize={11} />
                  <Tooltip />
                  <Area type="monotone" dataKey="runs" stroke="#7c5cff" fill="url(#rg)" />
                </AreaChart>
              </ResponsiveContainer>
            </Box>
          </SectionPanel>
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <SectionPanel title="Recent decisions">
            <TableContainer>
              <Table size="small">
                <TableHead><TableRow><TableCell>Title</TableCell><TableCell>Status</TableCell><TableCell>When</TableCell></TableRow></TableHead>
                <TableBody>
                  {(stats?.recent.decisions ?? []).map((d) => (
                    <TableRow key={d.id}>
                      <TableCell>{d.title}</TableCell>
                      <TableCell><Chip size="small" label={d.status} /></TableCell>
                      <TableCell>{new Date(d.created_at).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                  {!(stats?.recent.decisions?.length) && (
                    <TableRow><TableCell colSpan={3} sx={{ color: "text.secondary" }}>None yet.</TableCell></TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </SectionPanel>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <SectionPanel title="Pending approvals"
            right={stats && stats.pending_approvals > 0 ? (
              <Button size="small" component={Link} href="/" color="primary">Resolve in Chat →</Button>
            ) : undefined}>
            {(stats?.recent.approvals ?? []).length ? (
              <Stack spacing={1}>
                {stats!.recent.approvals.map((a) => (
                  <Stack key={a.id} direction="row" spacing={1} alignItems="center">
                    <Chip size="small" label={a.kind} color={a.status === "pending" ? "warning" : "default"} />
                    <Typography variant="caption" sx={{ color: "text.secondary" }}>
                      {new Date(a.created_at).toLocaleString()} · {a.status}
                    </Typography>
                  </Stack>
                ))}
              </Stack>
            ) : <Typography sx={{ color: "text.secondary" }}>No approvals pending.</Typography>}
          </SectionPanel>
        </Grid>
      </Grid>

      <SectionPanel title="Projects" subtitle={`${projects.length} registered`}>
        <TableContainer>
          <Table size="small">
            <TableHead><TableRow><TableCell>Name</TableCell><TableCell>Status</TableCell><TableCell>Repo</TableCell><TableCell>Description</TableCell></TableRow></TableHead>
            <TableBody>
              {projects.map((p) => (
                <TableRow key={p.id}>
                  <TableCell>{p.name}</TableCell>
                  <TableCell><Chip size="small" label={p.status} /></TableCell>
                  <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>{p.repo_path ?? "—"}</TableCell>
                  <TableCell>{p.description}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <Stack direction="row" spacing={1} sx={{ mt: 2, flexWrap: "wrap", gap: 1 }}>
          <input placeholder="project name" value={name} onChange={(e) => setName(e.target.value)}
            style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid #8885", background: "inherit" }} />
          <input placeholder="repo path (optional)" value={repo} onChange={(e) => setRepo(e.target.value)}
            style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid #8885", background: "inherit", minWidth: 320 }} />
          <Button variant="outlined" onClick={browse}>Browse…</Button>
          <Button variant="contained" onClick={create}>Create</Button>
        </Stack>
      </SectionPanel>
    </Box>
  );
}