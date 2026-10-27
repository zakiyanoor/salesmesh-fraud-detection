import { Box, useMediaQuery } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import {
  Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

// Shared charts in the style of docs/FRONTEND.md (Charts): 220px high, dashed grid, 12px axes.
export const CHART_HEIGHT = 220;

function useStyle() {
  const theme = useTheme();
  return {
    theme,
    axis: { stroke: theme.palette.chart.axis, fontSize: 12 },
    grid: <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.chart.grid} />,
    tooltip: (
      <Tooltip
        cursor={{ fill: theme.palette.action.selected }}
        contentStyle={{
          background: theme.palette.background.paper,
          border: `1px solid ${theme.palette.divider}`,
          color: theme.palette.text.primary,
        }}
      />
    ),
    legend: <Legend wrapperStyle={{ fontSize: 12, color: theme.palette.text.secondary }} />,
  };
}

/** A county name under its column, split onto lines at spaces and hyphens so it is never tilted. */
function CountyTick({ x, y, payload, fill }) {
  const words = String(payload.value).split(/(?<=-)|\s+/).filter(Boolean);
  return (
    <text x={x} y={y + 12} textAnchor="middle" fontSize={12} fill={fill}>
      {words.map((w, i) => <tspan key={i} x={x} dy={i === 0 ? 0 : 14}>{w}</tspan>)}
    </text>
  );
}

function CountyTooltip({ active, payload, palette }) {
  if (!active || !payload?.length) return null;
  const c = payload[0].payload;
  return (
    <Box sx={{ bgcolor: palette.background.paper, border: `1px solid ${palette.divider}`, borderRadius: "6px", px: 1.25, py: 0.75, fontSize: 13 }}>
      <Box sx={{ fontWeight: 600 }}>{c.county}</Box>
      <Box>{`${c.flagged} of ${c.agents} agents flagged (${Math.round(c.rate * 1000) / 10}%)`}</Box>
    </Box>
  );
}

/**
 * Flagged agents against all agents per county, for the counties with the highest flagged rate (the API's
 * top_by_flagged_rate: the top 10 among counties with at least 5 agents). Upright grouped columns with the
 * county names written flat under them; below 700px, horizontal bars so the names never tilt.
 */
export function CountyChart({ counties }) {
  const { theme, axis, legend } = useStyle();
  const narrow = useMediaQuery("(max-width:699.95px)");
  const palette = theme.palette;
  const accent = palette.mode === "dark" ? palette.primary.main : palette.primary.dark;
  const data = counties.map((c) => ({ county: c.region, flagged: c.flagged, agents: c.agents, rate: c.flagged_rate }));
  const tooltip = <Tooltip cursor={{ fill: palette.action.selected }} content={<CountyTooltip palette={palette} />} />;
  const bars = [
    <Bar key="agents" dataKey="agents" name="All agents" fill={alpha(palette.chart.neutral, 0.55)} radius={narrow ? [0, 2, 2, 0] : [2, 2, 0, 0]} isAnimationActive={false} />,
    <Bar key="flagged" dataKey="flagged" name="Flagged agents" fill={accent} radius={narrow ? [0, 2, 2, 0] : [2, 2, 0, 0]} isAnimationActive={false} />,
  ];
  if (narrow) {
    return (
      <ResponsiveContainer width="100%" height={Math.max(CHART_HEIGHT, data.length * 40 + 40)}>
        <BarChart data={data} layout="vertical" margin={{ left: 4, right: 12 }} barGap={2}>
          <CartesianGrid horizontal={false} stroke={palette.divider} />
          <XAxis type="number" {...axis} allowDecimals={false} />
          <YAxis type="category" dataKey="county" {...axis} width={96} />
          {tooltip}
          {legend}
          {bars}
        </BarChart>
      </ResponsiveContainer>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 24, left: 0 }} barGap={2} barCategoryGap="22%">
        <CartesianGrid vertical={false} stroke={palette.divider} />
        <XAxis dataKey="county" interval={0} height={48} tickLine={false} axisLine={{ stroke: palette.divider }}
          tick={<CountyTick fill={palette.text.secondary} />} />
        <YAxis {...axis} allowDecimals={false} axisLine={false} tickLine={false} width={36} />
        {tooltip}
        {legend}
        {bars}
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Vertical bars for a simple { name, value } series in one colour (or one per bar via fill). */
export function SimpleBarChart({ data, name, color, horizontal = false }) {
  const { theme, axis, grid, tooltip } = useStyle();
  const fill = color || theme.palette.primary.main;
  if (horizontal) {
    return (
      <ResponsiveContainer width="100%" height={Math.max(CHART_HEIGHT, data.length * 32)}>
        <BarChart data={data} layout="vertical" margin={{ left: 8 }}>
          {grid}
          <XAxis type="number" {...axis} allowDecimals={false} />
          <YAxis type="category" dataKey="name" {...axis} width={150} />
          {tooltip}
          <Bar dataKey="value" name={name} fill={fill} radius={[0, 3, 3, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <BarChart data={data}>
        {grid}
        <XAxis dataKey="name" {...axis} />
        <YAxis {...axis} allowDecimals={false} />
        {tooltip}
        <Bar dataKey="value" name={name} fill={fill} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
