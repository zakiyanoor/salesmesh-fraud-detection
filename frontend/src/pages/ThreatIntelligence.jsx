import { Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import GroupsOutlined from "@mui/icons-material/GroupsOutlined";
import ReportOutlined from "@mui/icons-material/ReportOutlined";
import PercentOutlined from "@mui/icons-material/PercentOutlined";
import PaymentsOutlined from "@mui/icons-material/PaymentsOutlined";
import AgentId from "../components/AgentId";
import KpiCard from "../components/KpiCard";
import PageHeader from "../components/PageHeader";
import RiskBadge from "../components/RiskBadge";
import ScoreWithRank from "../components/ScoreWithRank";
import SectionCard from "../components/SectionCard";
import { flagSourceTable, regionRateTable, timelineTable, topFeatureTable } from "../chartTables";
import { DonutChart } from "../components/DonutCard";
import { ActivationTimelineChart, RegionRateChart, SimpleBarChart } from "../components/charts";
import { FlagSourceChip } from "../components/chips";
import { useApi } from "../hooks/useApi";
import { FLAG_SOURCE_LABELS, MODEL_FEATURE_LABELS, formatPercent } from "../format";
import { mono } from "../theme";
import { api } from "../api";

const TOP_AGENTS = 10;
const loadTopAgents = () => api.getAgentScores({ limit: TOP_AGENTS });
const half = { flex: "1 1 320px" };
const noRun = "No successful detection run yet.";

function TopAgents({ scores }) {
  return (
    <TableContainer>
      <Table size="small" aria-label="Top risk agents">
        <TableHead>
          <TableRow>
            <TableCell>Agent ID</TableCell>
            <TableCell>Score (rank)</TableCell>
            <TableCell>Risk</TableCell>
            <TableCell>Flagged by</TableCell>
            <TableCell>Top features</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {scores.map((a) => (
            <TableRow key={a.agent_id} hover>
              <TableCell><AgentId id={a.agent_id} /></TableCell>
              <TableCell><ScoreWithRank score={a.anomaly_score} percentile={a.score_percentile} /></TableCell>
              <TableCell><RiskBadge band={a.risk_band} /></TableCell>
              <TableCell><FlagSourceChip source={a.flag_source} /></TableCell>
              <TableCell>{(a.top_features || []).map((f) => MODEL_FEATURE_LABELS[f] || f).join(", ") || "—"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

function Clusters({ data }) {
  return (
    <>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {data.shared_customers} customers were activated by more than one agent for the same client, linking agents into {data.clusters_total} groups.
        {data.clusters_total > data.clusters.length ? ` The ${data.clusters.length} largest are shown.` : ""}
      </Typography>
      <TableContainer>
        <Table size="small" aria-label="Connected agent groups">
          <TableHead>
            <TableRow>
              <TableCell>Agents</TableCell>
              <TableCell>Size</TableCell>
              <TableCell>Flagged</TableCell>
              <TableCell>Shared customers</TableCell>
              <TableCell>Clients</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.clusters.map((c) => (
              <TableRow key={c.agent_ids.join("-")}>
                <TableCell>
                  <Box sx={{ display: "flex", flexWrap: "wrap", columnGap: 1.5, rowGap: 0.5 }}>
                    {c.agent_ids.map((id) => <AgentId key={id} id={id} />)}
                  </Box>
                </TableCell>
                <TableCell sx={mono}>{c.size}</TableCell>
                <TableCell sx={mono}>{c.flagged_agents}</TableCell>
                <TableCell sx={mono}>{c.customer_count}</TableCell>
                <TableCell sx={mono}>{(c.client_ids || []).join(", ")}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
}

/** Threat intelligence for every role, from the latest successful detection run. */
export default function ThreatIntelligence() {
  const theme = useTheme();
  const summary = useApi(api.getThreatSummary);
  const timeline = useApi(api.getThreatTimeline);
  const regions = useApi(api.getThreatByRegion);
  const top = useApi(loadTopAgents);
  const sharing = useApi(api.getCustomerSharing);
  const s = summary.data;

  return (
    <>
      <PageHeader title="Threat intelligence" subtitle="Where flagged activity concentrates, from the latest successful detection run" />

      <Box component="section" aria-label="Summary" sx={{ display: "flex", gap: 3, mb: 4, flexWrap: "wrap" }}>
        <KpiCard icon={<GroupsOutlined fontSize="large" />} loading={summary.loading} value={s?.agents_scored ?? "—"} label="Agents scored" />
        <KpiCard icon={<ReportOutlined fontSize="large" />} loading={summary.loading} value={s?.flagged ?? "—"} label="Flagged by the model" color="risk.high" />
        <KpiCard icon={<PercentOutlined fontSize="large" />} loading={summary.loading} value={formatPercent(s?.flagged_rate)} label="Flagged rate" />
        <KpiCard
          icon={<PaymentsOutlined fontSize="large" />}
          loading={summary.loading}
          value={formatPercent(s?.commission_kes?.flagged_share)}
          label="Commission paid on flagged agents' records"
        />
      </Box>

      <Box sx={{ display: "flex", gap: 3, mb: 3, flexWrap: "wrap" }}>
        <SectionCard
          title="Flag sources"
          table={flagSourceTable}
          subtitle="Who flagged each agent"
          result={summary}
          isEmpty={(d) => !d?.agents_scored}
          emptyText={noRun}
          sx={half}
        >
          {(d) => (
            <DonutChart
              slices={["ML", "Both", "Rule", "None"].map((source, i) => ({
                name: FLAG_SOURCE_LABELS[source],
                value: d.flag_sources?.[source] ?? 0,
                fill: source === "None" ? theme.palette.chart.neutral : theme.palette.chart.region[i],
              }))}
            />
          )}
        </SectionCard>
        <SectionCard
          title="What drives the flags"
          table={topFeatureTable}
          subtitle="Flagged agents by their strongest feature"
          result={summary}
          isEmpty={(d) => !d?.top_features?.as_top_feature?.length}
          emptyText="No flagged agents to explain yet."
          sx={half}
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
        title="Activation timeline"
        table={timelineTable}
        subtitle="Activations per day by agents the model flagged and by all other agents"
        result={timeline}
        isEmpty={(d) => !d?.days?.length}
        emptyText="No activation records are loaded yet."
        sx={{ mb: 3 }}
      >
        {(d) => <ActivationTimelineChart days={d.days} />}
      </SectionCard>

      <SectionCard
        title="Regional flagged rates"
        table={regionRateTable}
        subtitle="The 10 highest flagged rates among regions with at least 5 agents"
        result={regions}
        isEmpty={(d) => !d?.top_by_flagged_rate?.length}
        emptyText="No region has enough agents yet."
        sx={{ mb: 3 }}
      >
        {(d) => <RegionRateChart regions={d.top_by_flagged_rate} />}
      </SectionCard>

      <SectionCard
        title="Top risk agents"
        subtitle={`The ${TOP_AGENTS} highest anomaly scores in the latest run`}
        result={top}
        isEmpty={(d) => !d?.scores?.length}
        emptyText={noRun}
        sx={{ mb: 3 }}
      >
        {(d) => <TopAgents scores={d.scores} />}
      </SectionCard>

      <SectionCard
        title="Connected agents"
        subtitle="Groups of agents linked by customers they share for the same client"
        result={sharing}
        isEmpty={(d) => !d?.clusters?.length}
        emptyText="No agents share customers."
      >
        {(d) => <Clusters data={d} />}
      </SectionCard>
    </>
  );
}
