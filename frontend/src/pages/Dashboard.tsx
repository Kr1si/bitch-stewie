import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api";

type Project = { id: string; name: string; status: string; repo_path: string | null; description: string };

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [repo, setRepo] = useState("");

  const load = () => apiGet<Project[]>("/api/projects").then(setProjects).catch(() => {});
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!name.trim()) return;
    await apiPost("/api/projects", { name, repo_path: repo || null });
    setName(""); setRepo("");
    load();
  };

  // Pop the host-side native folder dialog (browser inputs can't return an
  // absolute path); the backend returns it and we just fill the field.
  const browse = async () => {
    try {
      const r = await apiGet<{ path: string | null }>("/api/util/pick-folder");
      if (r.path) setRepo(r.path);
    } catch (e) {
      console.error("pick-folder failed", e);
    }
  };

  return (
    <section>
      <h2>Projects</h2>
      <table>
        <thead><tr><th>Name</th><th>Status</th><th>Repo</th><th>Description</th></tr></thead>
        <tbody>
          {projects.map((p) => (
            <tr key={p.id}><td>{p.name}</td><td>{p.status}</td><td>{p.repo_path}</td><td>{p.description}</td></tr>
          ))}
        </tbody>
      </table>
      <h3>Register project</h3>
      <input placeholder="name" value={name} onChange={(e) => setName(e.target.value)} />
      <input placeholder="repo path (optional)" value={repo} onChange={(e) => setRepo(e.target.value)} />
      <button onClick={browse}>Browse…</button>
      <button onClick={create}>Create</button>
    </section>
  );
}
