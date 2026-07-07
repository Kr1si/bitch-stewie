import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { getTheme, type Mode } from "./theme";
import App from "./App.tsx";

const stored = (localStorage.getItem("mode") as Mode) || "dark";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider theme={getTheme(stored)}>
      <CssBaseline />
      <App initialMode={stored} />
    </ThemeProvider>
  </StrictMode>,
);