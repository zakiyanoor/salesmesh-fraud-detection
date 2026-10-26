import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { PieChart, Pie, Tooltip } from "recharts";
import { mono } from "../theme";

const CHART_SIZE = 140;

/**
 * The donut and its legend (docs/FRONTEND.md, Charts). refined (Overview): a thicker ring with small gaps, the
 * total in the display font labelled "Total agents scored", and the legend directly beside the ring with aligned
 * counts and percentages in neutral text colours.
 */
export function DonutChart({ slices, refined = false }) {
  const theme = useTheme();
  const total = slices.reduce((sum, s) => sum + s.value, 0);
  const visible = slices.filter((s) => s.value > 0);
  // With nothing to plot, draw a single muted ring so the card keeps its shape.
  const pieData = total > 0 ? visible : [{ name: "No data", value: 1, fill: theme.palette.divider }];

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: { xs: 2, sm: 3 }, ...(refined ? { flexWrap: { xs: "wrap", sm: "nowrap" } } : {}) }}>
      <Box sx={{ position: "relative", width: CHART_SIZE, height: CHART_SIZE, flexShrink: 0 }}>
        <PieChart width={CHART_SIZE} height={CHART_SIZE}>
          <Pie
            data={pieData}
            dataKey="value"
            nameKey="name"
            innerRadius={refined ? 40 : 44}
            outerRadius={64}
            paddingAngle={visible.length > 1 ? 2 : 0}
            stroke="none"
            isAnimationActive={!refined}
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
          {refined ? (
            <Box role="group" aria-label="Total agents scored" sx={{
              fontFamily: (th) => th.typography.h1.fontFamily, fontSize: 22, fontWeight: 500, fontVariantNumeric: "tabular-nums", color: "text.primary",
            }}>
              {total}
            </Box>
          ) : (
            <Typography variant="h5" component="p" sx={mono}>{total}</Typography>
          )}
        </Box>
      </Box>

      <Box sx={refined ? { flex: "0 1 240px", minWidth: 0 } : { flex: 1, minWidth: 0 }}>
        {refined && slices.map((s) => (
          <Box key={s.name} sx={{ display: "grid", gridTemplateColumns: "10px minmax(0, 1fr) auto 44px", alignItems: "center", columnGap: 1.25, py: 0.6 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: "3px", bgcolor: s.fill }} />
            <Typography noWrap title={s.name} sx={{ fontSize: 14, minWidth: 0 }}>{s.name}</Typography>
            <Typography sx={{ fontSize: 14, color: "text.primary", fontVariantNumeric: "tabular-nums", textAlign: "right" }}>{s.value}</Typography>
            <Typography sx={{ fontSize: 13, color: "text.secondary", fontVariantNumeric: "tabular-nums", textAlign: "right" }}>
              {total > 0 ? `${Math.round((s.value / total) * 100)}%` : "—"}
            </Typography>
          </Box>
        ))}
        {!refined && slices.map((s) => (
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
  );
}
