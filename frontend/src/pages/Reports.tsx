import { useEffect, useState } from "react";
import {
  Box, Chip, CircularProgress, FormControl, InputLabel, MenuItem, Paper,
  Select, Stack, Tab, Tabs, Typography, Alert, Avatar,
} from "@mui/material";
import AutoAwesomeMotionIcon from "@mui/icons-material/AutoAwesomeMotion";
import LightbulbIcon from "@mui/icons-material/Lightbulb";
import {
  listGoals, listReports, patchGoal, readReport, type Goal, type Report,
} from "../lib/api";

type TabKey = "digest" | "findings" | "market-ideas";

const MD = ({ md }: { md: string }) => (
  <Typography component="pre" sx={{
    fontFamily: "monospace", fontSize: 13, lineHeight: 1.6,
    whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0,
  }}>
    {md || <span style={{ opacity: 0.6 }}>Nothing here yet.</span>}
  </Typography>
);

export default function Reports() {
  const [dates, setDates] = useState<string[]>([]);
  const [date, setDate] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [tab, setTab] = useState<TabKey>("digest");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listReports().then((d) => {
      setDates(d);
      if (d.length) setDate(d[0]);
    }).catch((e) => setError(String(e)));
    listGoals().then(setGoals).catch(() => {});
  }, []);

  useEffect(() => {
    if (!date) return;
    setLoading(true);
    readReport(date)
      .then(setReport)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [date]);

  const toggleGoal = (g: Goal) => {
    const next = g.status === "active" ? "paused" : "active";
    patchGoal(g.id, { status: next })
      .then((updated) => setGoals(goals.map((x) => (x.id === updated.id ? updated : x))))
      .catch((e) => setError(String(e)));
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "calc(100vh - 112px)", gap: 2 }}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Avatar sx={{ bgcolor: "primary.main", width: 28, height: 28 }}>
          <AutoAwesomeMotionIcon sx={{ fontSize: 18 }} />
        </Avatar>
        <Typography variant="h6" sx={{ fontWeight: 700 }}>Daily AI Intelligence</Typography>
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          autonomous research — daily digest + market-ideas wiki
        </Typography>
      </Stack>

      {/* Goal controls */}
      <Paper sx={{ p: 1.5 }}>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          <Typography variant="body2" sx={{ fontWeight: 600, mr: 1 }}>Goals:</Typography>
          {goals.length === 0 && (
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              no goals yet (seeded on next boot)
            </Typography>
          )}
          {goals.map((g) => (
            <Chip key={g.id} size="small"
              icon={g.kind === "research" ? <AutoAwesomeMotionIcon sx={{ fontSize: 14 }} /> : undefined}
              label={`${g.title} · ${g.cadence}`}
              color={g.status === "active" ? "success" : "default"}
              variant={g.status === "active" ? "filled" : "outlined"}
              onClick={() => toggleGoal(g)}
            />
          ))}
        </Stack>
      </Paper>

      {/* Date selector */}
      <FormControl size="small" sx={{ minWidth: 200 }}>
        <InputLabel>Report date</InputLabel>
        <Select value={date} label="Report date" onChange={(e) => setDate(e.target.value)}>
          {dates.length === 0 && <MenuItem value=""><em>no reports yet</em></MenuItem>}
          {dates.map((d) => <MenuItem key={d} value={d}>{d}</MenuItem>)}
        </Select>
      </FormControl>

      {error && <Alert severity="error" sx={{ whiteSpace: "pre-wrap" }}>{error}</Alert>}

      {/* Tabs */}
      <Tabs value={tab} onChange={(_, v) => setTab(v)}>
        <Tab value="digest" label="Daily Digest" />
        <Tab value="findings" label="Findings" />
        <Tab value="market-ideas" label={<>Market Ideas <LightbulbIcon sx={{ fontSize: 14, ml: 0.5 }} /></>} />
      </Tabs>

      <Paper sx={{ flex: 1, overflow: "auto", p: 2 }}>
        {loading && (
          <Stack direction="row" spacing={1} alignItems="center" sx={{ opacity: 0.7 }}>
            <CircularProgress size={16} />
            <Typography variant="body2">loading report…</Typography>
          </Stack>
        )}
        {!loading && report && tab === "digest" && <MD md={report.digest} />}
        {!loading && report && tab === "findings" && (
          <Stack spacing={2}>
            {report.findings.length === 0 && (
              <Typography variant="body2" sx={{ color: "text.secondary" }}>no findings.</Typography>
            )}
            {report.findings.map((f) => (
              <Paper key={f.category} variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1, textTransform: "capitalize" }}>
                  {f.category.replace(/-/g, " ")}
                </Typography>
                <MD md={f.markdown} />
              </Paper>
            ))}
          </Stack>
        )}
        {!loading && report && tab === "market-ideas" && (
          <MD md={report.market_ideas || "No market ideas yet."} />
        )}
        {!loading && !report && (
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            No report for this date yet. The daily pipeline runs at 07:00 UTC.
          </Typography>
        )}
      </Paper>
    </Box>
  );
}
