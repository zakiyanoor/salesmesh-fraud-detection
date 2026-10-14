import { Box, Paper, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { PieChart, Pie, Tooltip } from "recharts";
import { mono } from "../theme";

const CHART_SIZE = 140;

export default function DonutCard({ title, subtitle, slices }) {
  const theme = useTheme();
  const total = slices.reduce((sum, s) => sum + s.value, 0);
  const visible = slices.filter((s) => s.value > 0);
  // With nothing to plot, draw a single muted ring so the card keeps its shape.
  const pieData = total > 0 ? visible : [{ name: "No data", value: 1, fill: theme.palette.divider }];

  return (
    <Paper sx={{ p: 3, flex: "1 1 320px", minWidth: 0 }}>
      <Typography variant="overline" color="text.secondary">{title}</Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>{subtitle}</Typography>

      <Box sx={{ display: "flex", alignItems: "center", gap: { xs: 2, sm: 3 }, mt: 2 }}>
        <Box sx={{ position: "relative", width: CHART_SIZE, height: CHART_SIZE, flexShrink: 0 }}>
          <PieChart width={CHART_SIZE} height={CHART_SIZE}>
            <Pie
              data={pieData}
              dataKey="value"
              nameKey="name"
              innerRadius={44}
              outerRadius={64}
              paddingAngle={visible.length > 1 ? 2 : 0}
              stroke="none"
            />
            {total > 0 && (
              <Tooltip
                contentStyle={{
                  background: theme.palette.background.paper,
                  border: `1px solid ${theme.palette.divider}`,
                  color: theme.palette.text.primary,
                }}
              />
            )}
          </PieChart>
          <Box sx={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", pointerEvents: "none" }}>
            <Typography variant="h5" sx={mono}>{total}</Typography>
          </Box>
        </Box>

        <Box sx={{ flex: 1, minWidth: 0 }}>
          {slices.map((s) => (
            <Box key={s.name} sx={{ display: "flex", alignItems: "center", gap: 1, py: 0.5 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: s.fill, flexShrink: 0 }} />
              <Typography variant="body2" noWrap title={s.name} sx={{ flex: 1, minWidth: 0 }}>{s.name}</Typography>
              <Typography variant="body2" sx={mono}>{s.value}</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ ...mono, width: 40, textAlign: "right" }}>
                {total > 0 ? `${Math.round((s.value / total) * 100)}%` : "—"}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>
    </Paper>
  );
}
