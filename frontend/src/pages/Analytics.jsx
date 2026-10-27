import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { BarChart, Bar, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import PageHeader from "../components/PageHeader";
import SectionCard from "../components/SectionCard";
import { scoreDistributionTable, topFeatureTable } from "../chartTables";
import { CHART_HEIGHT, SimpleBarChart } from "../components/charts";
import { useApi } from "../hooks/useApi";
import { FEATURES, MODEL_FEATURE_LABELS, formatNumber, formatRate } from "../format";
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

function CountTile({ label, value, warn = false }) {
  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: "8px", px: 2, py: 1.5, minWidth: 0 }}>
      <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{label}</Typography>
      <Typography sx={{ fontSize: 22, fontWeight: 500, lineHeight: 1.3, fontVariantNumeric: "tabular-nums", color: warn ? "warning.main" : "text.primary" }}>
        {value}
      </Typography>
    </Box>
  );
}

/**
 * Review outcomes (issue #28), from /api/analytics review: the overrule rate among compliance decisions with a
 * two part bar of agreed and overruled, and counts for the other states. Open and withdrawn proposals are not
 * part of the rate.
 */
function ReviewOutcomes({ review }) {
  const theme = useTheme();
  if (!review) return <Typography variant="body2" color="text.secondary">No review data.</Typography>;
  const decided = (review.agreed || 0) + (review.overruled || 0);
  const accent = theme.palette.mode === "dark" ? theme.palette.primary.main : theme.palette.primary.dark;
  const overruledColour = theme.palette.info.main;
  const share = decided ? review.overruled / decided : 0;
  return (
    <Box sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "minmax(0, 1.2fr) minmax(0, 1fr)" }, alignItems: "start" }}>
      <Box>
        {decided === 0 ? (
          <Typography data-testid="overrule-rate" sx={{ fontSize: 28, fontWeight: 500, lineHeight: 1.2 }}>No decisions yet</Typography>
        ) : (
          <>
            <Box sx={{ display: "flex", alignItems: "baseline", gap: 1.5, flexWrap: "wrap" }}>
              <Typography data-testid="overrule-rate" sx={{ fontSize: 40, fontWeight: 500, lineHeight: 1.1, fontVariantNumeric: "tabular-nums" }}>
                {formatRate(share)}
              </Typography>
              <Typography sx={{ fontSize: 15 }}>of compliance decisions overruled</Typography>
            </Box>
            <Typography sx={{ fontSize: 14, color: "text.secondary", mt: 0.5, fontVariantNumeric: "tabular-nums" }}>{`${review.overruled} of ${decided}`}</Typography>
            <Box aria-hidden="true" sx={{ display: "flex", height: 8, borderRadius: 4, overflow: "hidden", mt: 2, bgcolor: "divider", gap: share > 0 && share < 1 ? "2px" : 0 }}>
              <Box sx={{ flex: review.agreed, bgcolor: accent }} />
              <Box sx={{ flex: review.overruled, bgcolor: overruledColour }} />
            </Box>
            <Box sx={{ display: "flex", justifyContent: "space-between", mt: 0.75, fontSize: 13, fontVariantNumeric: "tabular-nums" }}>
              <Box component="span" sx={{ color: "text.secondary" }}>{`Agreed ${review.agreed}`}</Box>
              <Box component="span" sx={{ color: "text.secondary" }}>{`Overruled ${review.overruled}`}</Box>
            </Box>
          </>
        )}
        <Typography sx={{ fontSize: 14, mt: 2 }}>Overruled means a compliance officer disagreed with the analyst&apos;s proposal.</Typography>
        <Typography sx={{ fontSize: 13, color: "text.secondary", mt: 0.5 }}>Open and withdrawn proposals are not counted.</Typography>
      </Box>
      <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
        <CountTile label="Open" value={review.open ?? 0} />
        <CountTile label="Overdue" value={review.overdue ?? 0} warn={review.overdue > 0} />
        <CountTile label="Withdrawn" value={review.withdrawn ?? 0} />
        <CountTile label="Corrections" value={review.corrections ?? 0} />
      </Box>
    </Box>
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
        subtitle="How compliance decisions compare with analyst proposals."
        result={analytics}
        sx={{ ...card, mb: 3 }}
      >
        {(data) => <ReviewOutcomes review={data.review} />}
      </SectionCard>

      <SectionCard panel title="Average behaviour across all agents" subtitle="From the latest detection run." result={analytics} sx={card}>
        {(data) => (
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "minmax(0, 1fr)", sm: "repeat(2, minmax(0, 1fr))", md: "repeat(4, minmax(0, 1fr))" } }}>
            {FEATURES.filter((f) => data.platform_averages?.[f.key] != null).map((f) => (
              <Box key={f.key} component="article" aria-label={f.label} sx={{ border: 1, borderColor: "divider", borderRadius: "8px", p: 2, minWidth: 0 }}>
                <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 0.5 }}>{f.label}</Typography>
                <Typography sx={{ fontSize: 28, fontWeight: 500, lineHeight: 1.2, fontVariantNumeric: "tabular-nums" }}>
                  {formatNumber(data.platform_averages[f.key], f.digits === 0 ? 1 : 2)}
                </Typography>
                <Typography sx={{ fontSize: 12, color: "text.secondary", mt: 0.5 }}>{f.unit}</Typography>
              </Box>
            ))}
          </Box>
        )}
      </SectionCard>
    </Box>
  );
}
