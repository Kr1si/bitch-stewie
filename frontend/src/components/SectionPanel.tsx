import { Accordion, AccordionDetails, AccordionSummary, Box, Stack, Typography } from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import type { ReactNode } from "react";

export default function SectionPanel({
  title, subtitle, defaultExpanded = true, children, right,
}: {
  title: string; subtitle?: string; defaultExpanded?: boolean;
  children: ReactNode; right?: ReactNode;
}) {
  return (
    <Accordion defaultExpanded={defaultExpanded} disableGutters elevation={0}
      sx={{ border: (t) => `1px solid ${t.palette.divider}`, borderRadius: 2, mb: 2 }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ width: 1, pr: 1 }}>
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{title}</Typography>
            {subtitle && <Typography variant="caption" sx={{ color: "text.secondary" }}>{subtitle}</Typography>}
          </Box>
          {right}
        </Stack>
      </AccordionSummary>
      <AccordionDetails>{children}</AccordionDetails>
    </Accordion>
  );
}