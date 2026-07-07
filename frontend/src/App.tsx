import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import Chat from "./pages/Chat";
import Dashboard from "./pages/Dashboard";
import Runs from "./pages/Runs";
import Knowledge from "./pages/Knowledge";
import Diagrams from "./pages/Diagrams";
import "./App.css";

const pages = [
  { path: "/", label: "Chat", element: <Chat /> },
  { path: "/dashboard", label: "Projects", element: <Dashboard /> },
  { path: "/runs", label: "CC Runs", element: <Runs /> },
  { path: "/knowledge", label: "Knowledge", element: <Knowledge /> },
  { path: "/diagrams", label: "Diagrams", element: <Diagrams /> },
];

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <nav className="sidebar">
          <h1>Assistant</h1>
          {pages.map((p) => (
            <NavLink key={p.path} to={p.path} end={p.path === "/"}>
              {p.label}
            </NavLink>
          ))}
        </nav>
        <main className="content">
          <Routes>
            {pages.map((p) => (
              <Route key={p.path} path={p.path} element={p.element} />
            ))}
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
