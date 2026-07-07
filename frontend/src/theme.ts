import { createTheme } from "@mui/material/styles";

// Reuse the existing accent purple as the MUI primary.
export const ACCENT = "#7c5cff";

export type Mode = "light" | "dark";

export function getTheme(mode: Mode) {
  return createTheme({
    palette: {
      mode,
      primary: { main: ACCENT },
      secondary: { main: "#26c6da" },
      background: {
        default: mode === "light" ? "#f6f7fb" : "#0f1117",
        paper: mode === "light" ? "#ffffff" : "#1b1e28",
      },
    },
    shape: { borderRadius: 10 },
    typography: {
      fontFamily: "Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
      h5: { fontWeight: 700 },
      h6: { fontWeight: 700 },
    },
    components: {
      MuiCard: { styleOverrides: { root: { boxShadow: "0 1px 3px rgba(0,0,0,.08)" } } },
    },
  });
}