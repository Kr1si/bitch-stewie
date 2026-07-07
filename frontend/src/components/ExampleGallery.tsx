import { useState } from "react";
import {
  Box, Card, CardContent, Chip, Grid, IconButton, Typography, Tooltip,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import { apiDelete, apiGet } from "../lib/api";

export type Example = {
  id: string; filename: string; kind: "diagram" | "doc";
  note: string; mime: string; project_id: string | null; created_at: string;
};

export default function ExampleGallery({
  examples, onDeleted,
}: { examples: Example[]; onDeleted: () => void }) {
  const [preview, setPreview] = useState<{ id: string; text: string; xml: string; img: string } | null>(null);

  const open = async (ex: Example) => {
    const isText = /\.(md|markdown|txt|rst|drawio|xml|svg)$/i.test(ex.filename);
    const url = `/api/examples/${ex.id}/content`;
    if (!isText) {
      // image or binary: show as <img> for png/svg
      setPreview({ id: ex.id, text: "", xml: "",
        img: /\.(png|svg)$/i.test(ex.filename) ? url : "" });
      return;
    }
    const resp = await fetch((import.meta.env.VITE_API_BASE ?? "http://localhost:8000") + url);
    const text = await resp.text();
    const xml = /\.(drawio|xml)$/i.test(ex.filename) ? text : "";
    setPreview({ id: ex.id, text: xml ? "" : text, xml, img: "" });
  };

  const del = async (id: string) => {
    await apiDelete(`/api/examples/${id}`);
    onDeleted();
  };

  if (examples.length === 0) {
    return <Typography variant="body2" sx={{ color: "text.secondary", py: 2 }}>
      No examples yet. Upload reference {examples.length} files for the agent to learn from.
    </Typography>;
  }

  return (
    <Box>
      <Grid container spacing={1.5}>
        {examples.map((ex) => (
          <Grid key={ex.id} size={{ xs: 12, sm: 6, md: 4 }}>
            <Card onClick={() => open(ex)} sx={{ cursor: "pointer", "&:hover": { borderColor: "primary.main" } }}>
              <CardContent>
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <Typography variant="subtitle2" sx={{ wordBreak: "break-all" }}>{ex.filename}</Typography>
                  <Tooltip title="delete">
                    <IconButton size="small" onClick={(e) => { e.stopPropagation(); del(ex.id); }}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
                {ex.note && <Typography variant="caption" sx={{ color: "text.secondary" }}>{ex.note}</Typography>}
                <Box sx={{ mt: 0.5 }}>
                  <Chip size="small" label={ex.kind} color="primary" variant="outlined" />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {preview && (
        <Box sx={{ mt: 2, p: 2, border: (t) => `1px solid ${t.palette.divider}`, borderRadius: 2,
          maxHeight: 400, overflow: "auto", bgcolor: "background.default" }}>
          {preview.img && <img src={preview.img} alt="preview" style={{ maxWidth: "100%" }} />}
          {preview.xml && (
            <DrawioPreview xml={preview.xml} />
          )}
          {preview.text && <pre style={{ whiteSpace: "pre-wrap", margin: 0, fontSize: 13 }}>{preview.text}</pre>}
        </Box>
      )}
    </Box>
  );
}

/** Lightweight, read-only draw.io XML preview (renders the shapes as text). */
function DrawioPreview({ xml }: { xml: string }) {
  return (
    <pre style={{ whiteSpace: "pre-wrap", margin: 0, fontSize: 12, fontFamily: "monospace" }}>
      {xml.slice(0, 4000)}
    </pre>
  );
}

// re-export so callers can refetch the list shape from one place
export async function fetchExamples(projectId?: string, kind?: string): Promise<Example[]> {
  const q = new URLSearchParams();
  if (projectId) q.set("project_id", projectId);
  if (kind) q.set("kind", kind);
  return apiGet<Example[]>(`/api/examples${q.size ? `?${q}` : ""}`);
}