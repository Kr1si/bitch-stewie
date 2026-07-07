import { Box, Card, CardContent, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";

export default function StatCard({
  icon, label, value, sub,
}: { icon: ReactNode; label: string; value: ReactNode; sub?: string }) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Box sx={{ color: "primary.main", display: "flex" }}>{icon}</Box>
          <Box>
            <Typography variant="caption" sx={{ color: "text.secondary", textTransform: "uppercase", letterSpacing: 1 }}>
              {label}
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 700, lineHeight: 1.1 }}>{value}</Typography>
            {sub && <Typography variant="caption" sx={{ color: "text.secondary" }}>{sub}</Typography>}
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}