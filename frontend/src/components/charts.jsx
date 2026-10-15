import { useTheme } from "@mui/material/styles";
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
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

/** Daily activations by flagged agents and by everyone else (threat-intelligence timeline). */
export function ActivationTimelineChart({ days }) {
  const { theme, axis, grid, tooltip, legend } = useStyle();
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <LineChart data={days}>
        {grid}
        <XAxis dataKey="date" {...axis} minTickGap={24} />
        <YAxis {...axis} allowDecimals={false} />
        {tooltip}
        {legend}
        <Line type="monotone" dataKey="flagged_agents" name="Flagged agents" stroke={theme.palette.error.main} strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="other_agents" name="Other agents" stroke={theme.palette.chart.neutral} strokeWidth={2} strokeDasharray="5 3" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Regions with the highest flagged rate, as horizontal bars in percent. */
export function RegionRateChart({ regions }) {
  const { theme, axis, grid, tooltip } = useStyle();
  const data = regions.map((r) => ({ ...r, percent: Math.round(r.flagged_rate * 1000) / 10 }));
  return (
    <ResponsiveContainer width="100%" height={Math.max(CHART_HEIGHT, data.length * 28)}>
      <BarChart data={data} layout="vertical" margin={{ left: 8 }}>
        {grid}
        <XAxis type="number" {...axis} unit="%" />
        <YAxis type="category" dataKey="region" {...axis} width={110} />
        {tooltip}
        <Bar dataKey="percent" name="Flagged %" fill={theme.palette.error.main} radius={[0, 3, 3, 0]} />
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
