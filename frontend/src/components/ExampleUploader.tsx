import { useState } from "react";
import {
  Box, Button, FormControl, InputLabel, MenuItem, Select, Stack, TextField, Typography,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import { apiGet, apiPostForm } from "../lib/api";

type Project = { id: string; name: string };

export default function ExampleUploader({
  kind, projects, onUploaded,
}: { kind: "diagram" | "doc"; projects: Project[]; onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [projectId, setProjectId] = useState("");
  const [note, setNote] = useState("");
  const [status, setStatus] = useState("");

  const upload = async () => {
    if (!file) return;
    setStatus("uploading…");
    const form = new FormData();
    form.append("file", file);
    form.append("kind", kind);
    if (projectId) form.append("project_id", projectId);
    if (note) form.append("note", note);
    try {
      await apiPostForm("/api/examples", form);
      setStatus(`uploaded: ${file.name}`);
      setFile(null);
      setNote("");
      onUploaded();
    } catch (e) {
      setStatus(`error: ${String(e)}`);
    }
  };

  return (
    <Stack spacing={2} direction="column">
      <FormControl fullWidth size="small">
        <InputLabel>Project (optional)</InputLabel>
        <Select value={projectId} label="Project (optional)" onChange={(e) => setProjectId(e.target.value)}>
          <MenuItem value=""><em>global</em></MenuItem>
          {projects.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
        </Select>
      </FormControl>
      <Box>
        <input
          type="file"
          accept={kind === "diagram" ? ".drawio,.xml,.png,.svg" : ".md,.markdown,.txt,.rst,.docx,.pdf"}
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          style={{ display: "none" }}
          id={`ex-up-${kind}`}
        />
        <label htmlFor={`ex-up-${kind}`}>
          <Button variant="outlined" component="span" startIcon={<CloudUploadIcon />} fullWidth>
            {file ? file.name : `Choose a ${kind} file`}
          </Button>
        </label>
      </Box>
      <TextField size="small" placeholder="note (optional)" value={note}
        onChange={(e) => setNote(e.target.value)} />
      <Button variant="contained" onClick={upload} disabled={!file}>
        Upload {kind} example
      </Button>
      {status && <Typography variant="caption" sx={{ color: "text.secondary" }}>{status}</Typography>}
    </Stack>
  );
}

// helper for callers that also want to browse folders on the host
export async function pickFolder(): Promise<string | null> {
  const r = await apiGet<{ path: string | null }>("/api/util/pick-folder");
  return r.path;
}