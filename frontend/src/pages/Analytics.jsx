import { Box, Typography, Paper } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import PageHeader from "../components/PageHeader";
import { LoadStatus, PageSkeleton } from "../components/states";
import { useApi } from "../hooks/useApi";
import { mono } from "../theme";
import { api } from "../api";

export default function Analytics() {
  const result = useApi(api.getAnalytics);
  const theme = useTheme();
  const tooltipStyle = {
    background: theme.palette.background.paper,
    border: `1px solid ${theme.palette.divider}`,
    color: theme.palette.text.primary,
  };

  const header = <PageHeader title="Analytics" subtitle="Aggregate view of agent behaviour across the platform" />;
  if (!result.data) {
    return (
      <Box sx={{ maxWidth: 1100 }}>
        {header}
        <LoadStatus result={result} skeleton={<PageSkeleton cards={2} rows={3} />} />
      </Box>
    );
  }
  const data = result.data;

  return (
    <Box sx={{ maxWidth: 1100 }}>
      {header}
      <Box sx={{ display: "flex", gap: 3, mb: 4, flexWrap: "wrap" }}>
        <Paper sx={{ p: 3, flex: "1 1 300px", minWidth: 0 }}>
          <Typography variant="overline" color="text.secondary">Suspicion score distribution</Typography>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data.score_distribution}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.chart.grid} />
              <XAxis dataKey="bucket" stroke={theme.palette.chart.axis} fontSize={12} />
              <YAxis stroke={theme.palette.chart.axis} fontSize={12} allowDecimals={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="count" fill={theme.palette.primary.main} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Paper>

        <Paper sx={{ p: 3, flex: "1 1 300px", minWidth: 0 }}>
          <Typography variant="overline" color="text.secondary">Flagged agents by region</Typography>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data.region_breakdown}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.chart.grid} />
              <XAxis dataKey="region" stroke={theme.palette.chart.axis} fontSize={12} />
              <YAxis stroke={theme.palette.chart.axis} fontSize={12} allowDecimals={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="flagged" fill={theme.palette.error.main} radius={[3, 3, 0, 0]} />
              <Bar dataKey="total" fill={theme.palette.chart.neutral} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Paper>
      </Box>

      <Paper sx={{ p: 3 }}>
        <Typography variant="overline" color="text.secondary">Platform average behaviour</Typography>
        <Box sx={{ display: "flex", gap: { xs: 3, md: 6 }, mt: 2, flexWrap: "wrap" }}>
          {[
            ["Submission frequency", data.platform_averages?.submission_frequency],
            ["Time-of-day distribution", data.platform_averages?.time_of_day_dist],
            ["Customer similarity", data.platform_averages?.customer_similarity],
          ].map(([label, value]) => (
            <Box key={label}>
              <Typography variant="h5" component="p" sx={mono}>{value ?? "—"}</Typography>
              <Typography variant="caption" color="text.secondary">{label}</Typography>
            </Box>
          ))}
        </Box>
      </Paper>
    </Box>
  );
}
