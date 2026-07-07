import { useEffect, useState } from "react";
import { Box, FormControl, InputLabel, MenuItem, Select, Stack, Typography } from "@mui/material";
import { apiGet } from "../lib/api";
import SectionPanel from "../components/SectionPanel";
import ExampleUploader from "../components/ExampleUploader";
import ExampleGallery, { fetchExamples, type Example } from "../components/ExampleGallery";

type Project = { id: string; name: string };

export default function Examples() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [kind, setKind] = useState<"" | "diagram" | "doc">("");
  const [examples, setExamples] = useState<Example[]>([]);

  useEffect(() => { apiGet<Project[]>("/api/projects").then(setProjects).catch(() => {}); }, []);
  useEffect(() => {
    fetchExamples(projectId || undefined, kind || undefined).then(setExamples).catch(() => {});
  }, [projectId, kind]);

  const reload = () => fetchExamples(projectId || undefined, kind || undefined).then(setExamples);

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2, fontWeight: 700 }}>Examples</Typography>
      <Typography variant="body2" sx={{ color: "text.secondary", mb: 2 }}>
        The reference library the architect and doc-writer load when creating a new diagram or doc.
        Upload high-quality examples — the agent mimics their style/layout/structure.
      </Typography>

      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Project</InputLabel>
          <Select value={projectId} label="Project" onChange={(e) => setProjectId(e.target.value)}>
            <MenuItem value=""><em>all / global</em></MenuItem>
            {projects.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Kind</InputLabel>
          <Select value={kind} label="Kind" onChange={(e) => setKind(e.target.value as "" | "diagram" | "doc")}>
            <MenuItem value=""><em>all</em></MenuItem>
            <MenuItem value="diagram">diagram</MenuItem>
            <MenuItem value="doc">doc</MenuItem>
          </Select>
        </FormControl>
      </Stack>

      <SectionPanel title="Upload" defaultExpanded={false}>
        <Box sx={{ width: 320 }}>
          <ExampleUploader
            kind={kind === "diagram" || kind === "doc" ? kind : "diagram"}
            projects={projects} onUploaded={reload}
          />
        </Box>
      </SectionPanel>

      <SectionPanel title="Gallery" subtitle={`${examples.length} example(s)`}>
        <ExampleGallery examples={examples} onDeleted={reload} />
      </SectionPanel>
    </Box>
  );
}