import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { BarChart, Bar, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import PageHeader from "../components/PageHeader";
import SectionCard from "../components/SectionCard";
import { regionBreakdownTable, regionRateTable, scoreDistributionTable, timelineTable } from "../chartTables";
import { ActivationTimelineChart, CHART_HEIGHT, RegionRateChart } from "../components/charts";
import { useApi } from "../hooks/useApi";
import { FEATURES, formatNumber } from "../format";
import { mono } from "../theme";
import { api } from "../api";

const half = { flex: "1 1 300px" };

function useChartStyle() {
  const theme = useTheme();
  return {
    theme,
    grid: <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.chart.grid} />,
    axis: { stroke: theme.palette.chart.axis, fontSize: 12 },
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

export default function Analytics() {
  const analytics = useApi(api.getAnalytics);
  const timeline = useApi(api.getThreatTimeline);
  const regions = useApi(api.getThreatByRegion);
  const { theme, grid, axis, tooltip, legend } = useChartStyle();

  return (
    <Box sx={{ maxWidth: 1100 }}>
      <PageHeader title="Analytics" subtitle="Aggregate view of agent behaviour across the platform, from the latest detection run" />

      <SectionCard
        title="Daily activations"
        table={timelineTable}
        subtitle="Activations per day by agents the model flagged and by all other agents"
        result={timeline}
        isEmpty={(data) => !data?.days?.length}
        emptyText="No activation records are loaded yet."
        sx={{ mb: 3 }}
      >
        {(data) => (
          <ActivationTimelineChart days={data.days} />
        )}
      </SectionCard>

      <Box sx={{ display: "flex", gap: 3, mb: 3, flexWrap: "wrap" }}>
        <SectionCard
          title="Suspicion score distribution"
          table={scoreDistributionTable}
          subtitle="Agents per score range; the cutoff is 1.445"
          result={analytics}
          isEmpty={(data) => !data?.score_distribution?.some((b) => b.count > 0)}
          emptyText="No agents are scored yet."
          sx={half}
        >
          {(data) => (
            <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
              <BarChart data={data.score_distribution}>
                {grid}
                <XAxis dataKey="bucket" {...axis} />
                <YAxis {...axis} allowDecimals={false} />
                {tooltip}
                <Bar dataKey="count" name="Agents" fill={theme.palette.primary.main} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </SectionCard>

        <SectionCard
          title="Highest flagged rates by region"
          table={regionRateTable}
          subtitle="Share of each region's agents the model flagged; regions with at least 5 agents"
          result={regions}
          isEmpty={(data) => !data?.top_by_flagged_rate?.length}
          emptyText="No region has enough agents yet."
          sx={half}
        >
          {(data) => (
            <RegionRateChart regions={data.top_by_flagged_rate} />
          )}
        </SectionCard>
      </Box>

      <SectionCard
        title="Flagged agents by region"
        table={regionBreakdownTable}
        subtitle="Flagged and total agents per region"
        result={analytics}
        isEmpty={(data) => !data?.region_breakdown?.length}
        emptyText="No agents are loaded yet."
        sx={{ mb: 3 }}
      >
        {(data) => (
          <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
            <BarChart data={data.region_breakdown}>
              {grid}
              <XAxis dataKey="region" {...axis} />
              <YAxis {...axis} allowDecimals={false} />
              {tooltip}
              {legend}
              <Bar dataKey="flagged" name="Flagged" fill={theme.palette.error.main} radius={[3, 3, 0, 0]} />
              <Bar dataKey="total" name="Total" fill={theme.palette.chart.neutral} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </SectionCard>

      <SectionCard title="Platform average behaviour" subtitle="Mean of each model feature over all agents" result={analytics}>
        {(data) => (
          <Box sx={{ display: "flex", gap: { xs: 3, md: 6 }, flexWrap: "wrap" }}>
            {FEATURES.filter((f) => data.platform_averages?.[f.key] != null).map((f) => (
              <Box key={f.key}>
                <Typography variant="h5" component="p" sx={mono}>{formatNumber(data.platform_averages[f.key], f.digits === 0 ? 1 : f.digits)}</Typography>
                <Typography variant="caption" color="text.secondary">{f.label}</Typography>
              </Box>
            ))}
          </Box>
        )}
      </SectionCard>
    </Box>
  );
}
