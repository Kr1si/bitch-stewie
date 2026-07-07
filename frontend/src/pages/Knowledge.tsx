import { useState } from "react";
import { apiPost } from "../lib/api";

type Hit = { text: string; source: string; kind: string; score: number };

export default function Knowledge() {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [ingestPath, setIngestPath] = useState("");
  const [status, setStatus] = useState("");

  const search = async () => {
    if (!query.trim()) return;
    setHits(await apiPost<Hit[]>("/api/knowledge/search", { query }));
  };

  const ingest = async () => {
    if (!ingestPath.trim()) return;
    setStatus("ingesting…");
    const r = await apiPost<{ files: number; chunks: number }>("/api/knowledge/ingest-path", { path: ingestPath });
    setStatus(`ingested ${r.files} file(s), ${r.chunks} chunk(s)`);
  };

  return (
    <section>
      <h2>Knowledge</h2>
      <div>
        <input placeholder="search the knowledge base…" value={query}
               onChange={(e) => setQuery(e.target.value)}
               onKeyDown={(e) => e.key === "Enter" && search()} style={{ width: "50%" }} />
        <button onClick={search}>Search</button>
      </div>
      {hits.map((h, i) => (
        <div key={i} style={{ margin: "0.8rem 0" }}>
          <div><b>{h.source}</b> <small>({h.kind}, {h.score.toFixed(3)})</small></div>
          <p>{h.text.slice(0, 400)}</p>
        </div>
      ))}
      <h3>Ingest</h3>
      <input placeholder="absolute path to file or folder" value={ingestPath}
             onChange={(e) => setIngestPath(e.target.value)} style={{ width: "50%" }} />
      <button onClick={ingest}>Ingest</button> <span>{status}</span>
    </section>
  );
}
