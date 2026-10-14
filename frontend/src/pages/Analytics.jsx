import { useEffect, useState } from "react";
import { Box, Typography, Paper, CircularProgress } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import Sidebar, { DRAWER_WIDTH } from "../components/Sidebar";
import { api } from "../api";

export default function Analytics({ username, onLogout }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const theme = useTheme();
  const tooltipStyle = {
    background: theme.palette.background.paper,
    border: `1px solid ${theme.palette.divider}`,
    color: theme.palette.text.primary,
  };

  useEffect(() => {
    api.getAnalytics().then(setData).catch(onLogout).finally(() => setLoading(false));
  }, [onLogout]);

  if (loading) {
    return <Box sx={{ display: "flex", justifyContent: "center", mt: 10 }}><CircularProgress /></Box>;
  }

  return (
    <Box sx={{ display: "flex" }}>
      <Sidebar username={username} onLogout={onLogout} />
      <Box sx={{ flexGrow: 1, p: 5, ml: `${DRAWER_WIDTH}px`, maxWidth: 1100 }}>
        <Typography variant="h4" gutterBottom>Analytics</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Aggregate view of agent behaviour across the platform
        </Typography>

        <Box sx={{ display: "flex", gap: 3, mb: 4, flexWrap: "wrap" }}>
          <Paper sx={{ p: 3, flex: "1 1 300px" }}>
            <Typography variant="overline" color="text.secondary">Suspicion score distribution</Typography>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={data.score_distribution}>
                <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                <XAxis dataKey="bucket" stroke={theme.palette.text.secondary} fontSize={12} />
                <YAxis stroke={theme.palette.text.secondary} fontSize={12} allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="count" fill={theme.palette.primary.main} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Paper>

          <Paper sx={{ p: 3, flex: "1 1 300px" }}>
            <Typography variant="overline" color="text.secondary">Flagged agents by region</Typography>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={data.region_breakdown}>
                <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                <XAxis dataKey="region" stroke={theme.palette.text.secondary} fontSize={12} />
                <YAxis stroke={theme.palette.text.secondary} fontSize={12} allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="flagged" fill={theme.palette.error.main} radius={[3, 3, 0, 0]} />
                <Bar dataKey="total" fill={theme.palette.grey[400]} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Box>

        <Paper sx={{ p: 3 }}>
          <Typography variant="overline" color="text.secondary">Platform average behaviour</Typography>
          <Box sx={{ display: "flex", gap: 6, mt: 2 }}>
            {[
              ["Submission frequency", data.platform_averages.submission_frequency],
              ["Time-of-day distribution", data.platform_averages.time_of_day_dist],
              ["Customer similarity", data.platform_averages.customer_similarity],
            ].map(([label, value]) => (
              <Box key={label}>
                <Typography variant="h5" sx={{ fontFamily: '"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace' }}>{value}</Typography>
                <Typography variant="caption" color="text.secondary">{label}</Typography>
              </Box>
            ))}
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}