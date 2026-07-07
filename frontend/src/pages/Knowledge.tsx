import { useEffect, useState } from "react";
import {
  Box, Button, Card, CardContent, Chip, Grid, Stack, TextField, Typography,
} from "@mui/material";
import FolderIcon from "@mui/icons-material/Folder";
import { apiGet, apiPost } from "../lib/api";
import SectionPanel from "../components/SectionPanel";
import ExampleUploader from "../components/ExampleUploader";
import ExampleGallery, { fetchExamples, type Example } from "../components/ExampleGallery";

type Collection = { name: string; points: number; sources: { source: string; chunks: number }[] };
type Hit = { text: string; source: string; kind: string; score: number };
type Project = { id: string; name: string };

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export default function Knowledge() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [ingestPath, setIngestPath] = useState("");
  const [status, setStatus] = useState("");
  const [docExamples, setDocExamples] = useState<Example[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  const loadCollections = () => apiGet<Collection[]>("/api/knowledge/collections").then(setCollections).catch(() => {});
  useEffect(() => {
    loadCollections();
    apiGet<Project[]>("/api/projects").then(setProjects).catch(() => {});
    fetchExamples(undefined, "doc").then(setDocExamples).catch(() => {});
  }, []);

  const search = async () => {
    if (!query.trim()) return;
    setHits(await apiPost<Hit[]>("/api/knowledge/search", { query }));
  };
  const ingest = async () => {
    if (!ingestPath.trim()) return;
    setStatus("ingesting…");
    try {
      const r = await apiPost<{ files: number; chunks: number }>("/api/knowledge/ingest-path", { path: ingestPath });
      setStatus(`ingested ${r.files} file(s), ${r.chunks} chunk(s)`);
      loadCollections();
    } catch (e) { setStatus(`error: ${String(e)}`); }
  };
  const browse = async () => {
    const path = await (await fetch(`${API_BASE}/api/util/pick-folder`)).json().catch(() => null);
    if (path?.path) setIngestPath(path.path);
  };
  const reloadDocs = () => fetchExamples(undefined, "doc").then(setDocExamples);

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2, fontWeight: 700 }}>Knowledge</Typography>

      <SectionPanel title="Collections" subtitle={`${collections.length} knowledge bases`}>
        <Grid container spacing={1.5}>
          {collections.map((c) => (
            <Grid key={c.name} size={{ xs: 12, sm: 6, md: 4 }}>
              <Card>
                <CardContent>
                  <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
                    <Typography fontWeight={700} sx={{ fontFamily: "monospace" }}>{c.name}</Typography>
                    <Chip size="small" label={`${c.points} pts`} color="primary" variant="outlined" />
                  </Stack>
                  <Typography variant="caption" sx={{ color: "text.secondary" }}>
                    {c.sources.length} source(s)
                  </Typography>
                  <Button size="small" sx={{ mt: 0.5 }} onClick={() =>
                    setExpanded(expanded === c.name ? null : c.name)}>
                    {expanded === c.name ? "hide" : "sources"}
                  </Button>
                  {expanded === c.name && (
                    <Stack spacing={0.5} sx={{ mt: 1 }}>
                      {c.sources.map((s) => (
                        <Stack key={s.source} direction="row" justifyContent="space-between"
                          sx={{ fontSize: 12, fontFamily: "monospace" }}>
                          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.source}</span>
                          <Chip size="small" label={s.chunks} sx={{ height: 18 }} />
                        </Stack>
                      ))}
                    </Stack>
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
          {!collections.length && <Typography sx={{ color: "text.secondary" }}>No collections yet.</Typography>}
        </Grid>
      </SectionPanel>

      <SectionPanel title="Search" subtitle="hybrid dense + sparse (RRF)">
        <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
          <TextField fullWidth size="small" placeholder="search the knowledge base…"
            value={query} onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()} />
          <Button variant="contained" onClick={search}>Search</Button>
        </Stack>
        <Grid container spacing={1.5}>
          {hits.map((h, i) => (
            <Grid key={i} size={{ xs: 12, md: 6 }}>
              <Card variant="outlined">
                <CardContent>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1, flexWrap: "wrap", gap: 1 }}>
                    <Typography fontWeight={700} sx={{ wordBreak: "break-all" }}>{h.source}</Typography>
                    <Chip size="small" label={h.kind} />
                    <Box sx={{ flex: 1 }} />
                    <Box sx={{ width: 80, height: 6, bgcolor: "divider", borderRadius: 3, overflow: "hidden" }}>
                      <Box sx={{ width: `${Math.round(h.score * 100)}%`, height: "100%", bgcolor: "primary.main" }} />
                    </Box>
                    <Typography variant="caption" sx={{ fontFamily: "monospace" }}>{h.score.toFixed(3)}</Typography>
                  </Stack>
                  <Typography variant="body2" sx={{ color: "text.secondary" }}>{h.text.slice(0, 280)}…</Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </SectionPanel>

      <SectionPanel title="Ingest" subtitle="index a file or folder on the host">
        <Stack direction="row" spacing={1}>
          <TextField fullWidth size="small" placeholder="absolute path to file or folder"
            value={ingestPath} onChange={(e) => setIngestPath(e.target.value)} />
          <Button variant="outlined" startIcon={<FolderIcon />} onClick={browse}>Browse…</Button>
          <Button variant="contained" onClick={ingest}>Ingest</Button>
        </Stack>
        {status && <Typography variant="caption" sx={{ color: "text.secondary", mt: 1, display: "block" }}>{status}</Typography>}
      </SectionPanel>

      <SectionPanel title="Doc examples" subtitle="reference docs the doc-writer mimics">
        <Stack direction="row" spacing={2}>
          <Box sx={{ width: 280 }}>
            <ExampleUploader kind="doc" projects={projects} onUploaded={reloadDocs} />
          </Box>
          <Box sx={{ flex: 1 }}>
            <ExampleGallery examples={docExamples} onDeleted={reloadDocs} />
          </Box>
        </Stack>
      </SectionPanel>
    </Box>
  );
}