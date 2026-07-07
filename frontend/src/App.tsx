import { useEffect, useState } from "react";
import {
  Box, AppBar, Avatar, Drawer, IconButton, List, ListItemButton,
  ListItemIcon, ListItemText, Toolbar, Typography, Tooltip,
} from "@mui/material";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import LightModeIcon from "@mui/icons-material/LightMode";
import ChatIcon from "@mui/icons-material/Chat";
import DashboardIcon from "@mui/icons-material/Dashboard";
import PlayCircleIcon from "@mui/icons-material/PlayCircle";
import LibraryBooksIcon from "@mui/icons-material/LibraryBooks";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import ExtensionIcon from "@mui/icons-material/Extension";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import { getTheme, type Mode } from "./theme";
import { ThemeProvider, CssBaseline } from "@mui/material";
import Chat from "./pages/Chat";
import Dashboard from "./pages/Dashboard";
import Runs from "./pages/Runs";
import Knowledge from "./pages/Knowledge";
import Diagrams from "./pages/Diagrams";
import Examples from "./pages/Examples";
import { apiGet } from "./lib/api";

const NAV = [
  { path: "/dashboard", label: "Dashboard", icon: <DashboardIcon /> },
  { path: "/", label: "Chat", icon: <ChatIcon /> },
  { path: "/diagrams", label: "Diagrams", icon: <AccountTreeIcon /> },
  { path: "/knowledge", label: "Knowledge", icon: <LibraryBooksIcon /> },
  { path: "/examples", label: "Examples", icon: <ExtensionIcon /> },
  { path: "/runs", label: "CC Runs", icon: <PlayCircleIcon /> },
];

const DRAWER_W = 230;

export default function App({ initialMode = "dark" as Mode }) {
  const [mode, setMode] = useState<Mode>(initialMode);
  const [model, setModel] = useState<string>("");

  useEffect(() => {
    apiGet<{ status: string; default_model: string }>("/health")
      .then((h) => setModel(h.default_model))
      .catch(() => {});
  }, []);

  const toggle = () => {
    const next = mode === "dark" ? "light" : "dark";
    localStorage.setItem("mode", next);
    setMode(next);
  };

  return (
    <ThemeProvider theme={getTheme(mode)}>
      <CssBaseline />
      <BrowserRouter>
        <Box sx={{ display: "flex", minHeight: "100vh" }}>
          <AppBar position="fixed" elevation={0}
            sx={{ zIndex: (t) => t.zIndex.drawer + 1, backdropFilter: "blur(6px)" }}>
            <Toolbar>
              <Avatar sx={{ bgcolor: "primary.main", width: 28, height: 28, mr: 1.5, fontSize: 14 }}>
                S
              </Avatar>
              <Typography variant="h6" sx={{ fontWeight: 700, flexGrow: 1 }}>
                Stewie&nbsp;
                <Typography component="span" variant="body2" sx={{ opacity: 0.6 }}>
                  architecture assistant
                </Typography>
              </Typography>
              {model && (
                <Tooltip title="active model">
                  <Typography variant="caption" sx={{ mr: 2, px: 1, py: 0.3,
                    bgcolor: "rgba(255,255,255,.1)", borderRadius: 1, fontFamily: "monospace" }}>
                    {model}
                  </Typography>
                </Tooltip>
              )}
              <IconButton color="inherit" onClick={toggle}>
                {mode === "dark" ? <LightModeIcon /> : <DarkModeIcon />}
              </IconButton>
            </Toolbar>
          </AppBar>

          <Drawer variant="permanent"
            sx={{ width: DRAWER_W, [`& .MuiDrawer-paper`]: { width: DRAWER_W, boxSizing: "border-box" } }}>
            <Toolbar />
            <List sx={{ px: 1 }}>
              {NAV.map((n) => (
                <ListItemButton
                  key={n.path}
                  component={NavLink}
                  to={n.path}
                  end={n.path === "/"}
                  sx={{
                    borderRadius: 2, mb: 0.5, py: 1.1,
                    "&.active": { bgcolor: "primary.main", color: "primary.contrastText",
                      "& .MuiListItemIcon-root": { color: "primary.contrastText" } },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 38 }}>{n.icon}</ListItemIcon>
                  <ListItemText primary={n.label} primaryTypographyProps={{ fontWeight: 600 }} />
                </ListItemButton>
              ))}
            </List>
          </Drawer>

          <Box component="main" sx={{ flexGrow: 1, p: 3, minWidth: 0, mt: "64px" }}>
            <Routes>
              <Route path="/" element={<Chat />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/runs" element={<Runs />} />
              <Route path="/knowledge" element={<Knowledge />} />
              <Route path="/diagrams" element={<Diagrams />} />
              <Route path="/examples" element={<Examples />} />
            </Routes>
          </Box>
        </Box>
      </BrowserRouter>
    </ThemeProvider>
  );
}