import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";

type Run = {
  id: string; status: string; model: string; repo_path: string;
  review_iterations: number; result: Record<string, unknown>; created_at: string;
};
type Event = { type: string; payload: Record<string, unknown>; at: string };

export default function Runs() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [events, setEvents] = useState<Event[] | null>(null);
  const [selected, setSelected] = useState("");

  const load = () => apiGet<Run[]>("/api/cc-runs").then(setRuns).catch(() => {});
  useEffect(() => {
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  const show = async (id: string) => {
    setSelected(id);
    setEvents(await apiGet<Event[]>(`/api/cc-runs/${id}/events`));
  };

  return (
    <section>
      <h2>Claude Code Runs</h2>
      <table>
        <thead><tr><th>When</th><th>Status</th><th>Repo</th><th>Reviews</th><th>Branch</th><th></th></tr></thead>
        <tbody>
          {runs.map((r) => (
            <tr key={r.id}>
              <td>{new Date(r.created_at).toLocaleString()}</td>
              <td>{r.status}</td>
              <td>{r.repo_path.split(/[\\/]/).pop()}</td>
              <td>{r.review_iterations}</td>
              <td>{String(r.result?.branch ?? "")}</td>
              <td><button onClick={() => show(r.id)}>events</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      {events && (
        <>
          <h3>Events — {selected.slice(0, 8)}</h3>
          <div style={{ maxHeight: "40vh", overflow: "auto" }}>
            {events.map((e, i) => (
              <div key={i}><code>{e.at.slice(11, 19)} [{e.type}] {JSON.stringify(e.payload).slice(0, 160)}</code></div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
