import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { PieChart, Pie, Tooltip } from "recharts";
import { mono } from "../theme";

const CHART_SIZE = 140;

/**
 * The donut and its legend (docs/FRONTEND.md, Charts). thickness is the ring width in px and gap the angle
 * between segments; totalSx styles the figure in the centre. Legend counts use the text colour with aligned digits.
 * stackNarrow puts the legend under the ring on phones; animate: false draws the ring at once.
 */
export function DonutChart({ slices, thickness = 20, gap = 2, totalSx, stackNarrow = false, animate = true }) {
  const theme = useTheme();
  const total = slices.reduce((sum, s) => sum + s.value, 0);
  const visible = slices.filter((s) => s.value > 0);
  // With nothing to plot, draw a single muted ring so the card keeps its shape.
  const pieData = total > 0 ? visible : [{ name: "No data", value: 1, fill: theme.palette.divider }];

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: { xs: 2, sm: 3 }, flexDirection: stackNarrow ? { xs: "column", sm: "row" } : "row" }}>
      <Box sx={{ position: "relative", width: CHART_SIZE, height: CHART_SIZE, flexShrink: 0 }}>
        <PieChart width={CHART_SIZE} height={CHART_SIZE}>
          <Pie
            data={pieData}
            dataKey="value"
            nameKey="name"
            innerRadius={64 - thickness}
            outerRadius={64}
            paddingAngle={visible.length > 1 ? gap : 0}
            stroke="none"
            isAnimationActive={animate}
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
          <Typography variant="h5" component="p" sx={{ ...mono, ...totalSx }}>{total}</Typography>
        </Box>
      </Box>

      <Box sx={{ flex: 1, minWidth: 0, width: stackNarrow ? { xs: "100%", sm: "auto" } : undefined }}>
        {slices.map((s) => (
          <Box key={s.name} sx={{ display: "flex", alignItems: "center", gap: 1, py: 0.5 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: s.fill, flexShrink: 0 }} />
            <Typography variant="body2" noWrap title={s.name} sx={{ flex: 1, minWidth: 0 }}>{s.name}</Typography>
            <Typography variant="body2" sx={{ ...mono, color: "text.primary", fontVariantNumeric: "tabular-nums", minWidth: 36, textAlign: "right" }}>{s.value}</Typography>
            <Typography variant="caption" color="text.secondary" sx={{ ...mono, width: 40, textAlign: "right" }}>
              {total > 0 ? `${Math.round((s.value / total) * 100)}%` : "—"}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}
