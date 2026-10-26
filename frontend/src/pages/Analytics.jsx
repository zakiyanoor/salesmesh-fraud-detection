import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { BarChart, Bar, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import PageHeader from "../components/PageHeader";
import SectionCard from "../components/SectionCard";
import { scoreDistributionTable, topFeatureTable } from "../chartTables";
import { CHART_HEIGHT, SimpleBarChart } from "../components/charts";
import { useApi } from "../hooks/useApi";
import { FEATURES, MODEL_FEATURE_LABELS, formatNumber } from "../format";
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

function ReviewOutcomes({ review }) {
  if (!review) return <Typography variant="body2" color="text.secondary">No review data.</Typography>;
  const decided = review.agreed + review.overruled;
  const counts = [["Open", review.open], ["Overdue", review.overdue], ["Withdrawn", review.withdrawn],
    ["Agreed", review.agreed], ["Overruled", review.overruled], ["Corrections", review.corrections]];
  return (
    <>
      <Typography variant="h5" component="p" sx={mono}>
        {review.overrule_rate == null ? "No compliance decisions yet" : `${(review.overrule_rate * 100).toFixed(1)}% overruled`}
      </Typography>
      {review.overrule_rate != null && (
        <Typography variant="body2" color="text.secondary">{`${review.overruled} of ${decided} compliance decisions`}</Typography>
      )}
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Overruled means a compliance officer disagreed with the analyst&apos;s proposal.
      </Typography>
      <Box component="dl" sx={{ m: 0, mt: 1, display: "grid", gridTemplateColumns: "auto 1fr", columnGap: 2, rowGap: 0.5 }}>
        {counts.map(([label, value]) => [
          <Typography key={`${label}-t`} component="dt" variant="body2" color="text.secondary">{label}</Typography>,
          <Typography key={`${label}-d`} component="dd" variant="body2" sx={{ ...mono, m: 0 }}>{value}</Typography>,
        ])}
      </Box>
    </>
  );
}

export default function Analytics() {
  const analytics = useApi(api.getAnalytics);
  const summary = useApi(api.getThreatSummary);
  const modelInfo = useApi(api.getModelInfo);
  const { theme, grid, axis, tooltip } = useChartStyle();
  const card = { p: 2.5 };

  return (
    <Box sx={{ maxWidth: 1100 }}>
      <PageHeader title="Analytics" subtitle="Aggregate view of agent behaviour across the platform, from the latest detection run" />

      <Box sx={{ display: "flex", gap: 3, mb: 3, flexWrap: "wrap" }}>
        <SectionCard
          panel
          title="Suspicion score distribution"
          table={scoreDistributionTable}
          subtitle={modelInfo.data?.cutoff != null ? `Agents per score range; the cutoff is ${modelInfo.data.cutoff.toFixed(3)}` : "Agents per score range"}
          result={analytics}
          isEmpty={(data) => !data?.score_distribution?.some((b) => b.count > 0)}
          emptyText="No agents are scored yet."
          sx={{ ...half, ...card }}
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
          panel
          title="What drives the flags"
          table={topFeatureTable}
          subtitle="Flagged agents by their strongest feature"
          result={summary}
          isEmpty={(d) => !d?.top_features?.as_top_feature?.length}
          emptyText="No flagged agents to explain yet."
          sx={{ ...half, ...card }}
        >
          {(d) => (
            <SimpleBarChart
              horizontal
              name="Agents"
              data={d.top_features.as_top_feature.map((f) => ({ name: MODEL_FEATURE_LABELS[f.feature] || f.feature, value: f.agents }))}
            />
          )}
        </SectionCard>
      </Box>

      <SectionCard
        panel
        title="Review outcomes"
        subtitle="Overrule rate: the share of compliance decisions that overruled the analyst. Withdrawn and open proposals are left out; corrections are counted separately."
        result={analytics}
        sx={{ ...card, mb: 3 }}
      >
        {(data) => <ReviewOutcomes review={data.review} />}
      </SectionCard>

      <SectionCard panel title="Platform average behaviour" subtitle="Mean of each model feature over all agents" result={analytics} sx={card}>
        {(data) => (
          <Box sx={{ display: "flex", gap: { xs: 3, md: 6 }, flexWrap: "wrap" }}>
            {FEATURES.filter((f) => data.platform_averages?.[f.key] != null).map((f) => (
              <Box key={f.key}>
                <Typography variant="h5" component="p" sx={{ ...mono, fontVariantNumeric: "tabular-nums" }}>{formatNumber(data.platform_averages[f.key], f.digits === 0 ? 1 : f.digits)}</Typography>
                <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{f.label}</Typography>
              </Box>
            ))}
          </Box>
        )}
      </SectionCard>
    </Box>
  );
}
