import { Link as RouterLink } from "react-router-dom";
import {
  Box, Button, Link, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography, useMediaQuery,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import GroupsOutlined from "@mui/icons-material/GroupsOutlined";
import ReportOutlined from "@mui/icons-material/ReportOutlined";
import WarningAmberOutlined from "@mui/icons-material/WarningAmberOutlined";
import RuleOutlined from "@mui/icons-material/RuleOutlined";
import UpdateOutlined from "@mui/icons-material/UpdateOutlined";
import AgentId from "../components/AgentId";
import KpiCard from "../components/KpiCard";
import PageHeader from "../components/PageHeader";
import RiskBadge from "../components/RiskBadge";
import ScoreWithRank from "../components/ScoreWithRank";
import SectionCard from "../components/SectionCard";
import { flagSourceTable, riskBandTable } from "../chartTables";
import { DonutChart } from "../components/DonutCard";
import { useApi } from "../hooks/useApi";
import { useLatestRun } from "../latestRun/latestRunContext";
import { FlagSourceChip } from "../components/chips";
import { useAuth } from "../auth/authContext";
import { canAccess } from "../auth/roles";
import { FLAG_SOURCE_LABELS, formatDateTime } from "../format";
import { api } from "../api";

const NEEDS_ATTENTION = 8;
const loadTopScores = () => api.getAgentScores({ limit: 50 });
const RUN_STATUS = { succeeded: "Succeeded", failed: "Failed", running: "Running" };
const STALE_HOURS = 48;
const tabular = { fontVariantNumeric: "tabular-nums" };

/** Hours since the run finished (or started). The API sends run times in UTC without a zone. */
function runAgeHours(run, now = Date.now()) {
  const at = run && (run.finished_at || run.started_at);
  if (!at) return null;
  const time = Date.parse(/Z|[+-]\d\d:\d\d$/.test(at) ? at : `${at}Z`);
  return Number.isFinite(time) ? (now - time) / 3_600_000 : null;
}

function RiskBandChart({ bands }) {
  const theme = useTheme();
  const data = [
    { name: "High risk", count: bands.high ?? 0, fill: theme.palette.risk.high },
    { name: "Review", count: bands.review ?? 0, fill: theme.palette.risk.review },
    { name: "Low risk", count: bands.low ?? 0, fill: theme.palette.risk.low },
  ];
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 24, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} stroke={theme.palette.divider} />
        <XAxis dataKey="name" axisLine={{ stroke: theme.palette.divider }} tickLine={false} tick={{ fill: theme.palette.text.secondary, fontSize: 13 }} />
        <YAxis axisLine={false} tickLine={false} tick={{ fill: theme.palette.text.secondary, fontSize: 12 }} allowDecimals={false} width={40} />
        <Tooltip
          cursor={{ fill: theme.palette.action.selected }}
          contentStyle={{
            background: theme.palette.background.paper,
            border: `1px solid ${theme.palette.divider}`,
            color: theme.palette.text.primary,
          }}
        />
        <Bar dataKey="count" name="Agents" radius={[3, 3, 0, 0]} barSize={36} isAnimationActive={false}>
          {data.map((d) => <Cell key={d.name} fill={d.fill} />)}
          <LabelList dataKey="count" position="top" fill={theme.palette.text.primary} fontSize={13} style={tabular} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Needs attention: four balanced columns with hairline rows, or a compact list on phones. */
function AttentionRows({ agents }) {
  const theme = useTheme();
  const narrow = useMediaQuery(theme.breakpoints.down("sm"));
  if (narrow) {
    return (
      <Box component="ul" aria-label="Agents that need attention" sx={{ listStyle: "none", m: 0, p: 0 }}>
        {agents.map((agent) => (
          <Box component="li" key={agent.agent_id} sx={{ py: 1.5, borderBottom: 1, borderColor: "divider", "&:last-of-type": { borderBottom: 0 } }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 1 }}>
              <AgentId id={agent.agent_id} />
              <Box sx={{ fontSize: 15, ...tabular }}><ScoreWithRank score={agent.anomaly_score} percentile={agent.score_percentile} /></Box>
            </Box>
            <Box sx={{ display: "flex", gap: 1, mt: 1, flexWrap: "wrap" }}>
              <RiskBadge band={agent.risk_band} />
              <FlagSourceChip source={agent.flag_source} />
            </Box>
          </Box>
        ))}
      </Box>
    );
  }
  const cell = { py: 1.25, px: 2, fontSize: 14, borderColor: "divider" };
  const head = { ...cell, py: 1, fontSize: 13, fontWeight: 500, color: "text.secondary" };
  return (
    <TableContainer>
      <Table size="small" aria-label="Agents that need attention" sx={{ tableLayout: "fixed" }}>
        <colgroup>
          <col style={{ width: "22%" }} />
          <col style={{ width: "28%" }} />
          <col style={{ width: "24%" }} />
          <col style={{ width: "26%" }} />
        </colgroup>
        <TableHead>
          <TableRow>
            <TableCell sx={head}>Agent ID</TableCell>
            <TableCell sx={head}>Score (rank)</TableCell>
            <TableCell sx={head}>Risk</TableCell>
            <TableCell sx={head}>Flagged by</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {agents.map((agent) => (
            <TableRow key={agent.agent_id} hover sx={{ "&:last-of-type td": { borderBottom: 0 } }}>
              <TableCell sx={cell}><AgentId id={agent.agent_id} /></TableCell>
              <TableCell sx={{ ...cell, ...tabular, fontSize: 15 }}><ScoreWithRank score={agent.anomaly_score} percentile={agent.score_percentile} /></TableCell>
              <TableCell sx={cell}><RiskBadge band={agent.risk_band} /></TableCell>
              <TableCell sx={cell}><FlagSourceChip source={agent.flag_source} /></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

/** Overview: the latest detection run at a glance, for every role. */
export default function Dashboard() {
  const theme = useTheme();
  const { user } = useAuth();
  const summary = useApi(api.getThreatSummary);
  const run = useLatestRun();
  const scores = useApi(loadTopScores);

  const s = summary.data;
  const lastRun = run.data?.run;
  const summaryLoading = summary.loading;
  const age = runAgeHours(lastRun);

  return (
    <>
      <PageHeader title="Overview" subtitle="The latest detection run at a glance" />
      {age != null && age > STALE_HOURS && (
        <Typography data-testid="stale-run" sx={{ fontSize: 14, color: "text.secondary", mt: -1, mb: 3 }}>
          {`The figures below are from a detection run ${Math.floor(age / 24)} days ago.`}
        </Typography>
      )}

      <Box component="section" aria-label="Summary" sx={{ display: "flex", gap: 3, mb: 3, flexWrap: "wrap" }}>
        <KpiCard icon={<GroupsOutlined fontSize="large" />} loading={summaryLoading} value={s?.agents_scored ?? "—"} label="Agents scored" refined />
        <KpiCard icon={<ReportOutlined fontSize="large" />} loading={summaryLoading} value={s?.risk_bands?.high ?? "—"} label="Flagged (high risk)" color="risk.high" refined />
        <KpiCard icon={<WarningAmberOutlined fontSize="large" />} loading={summaryLoading} value={s?.risk_bands?.review ?? "—"} label="Review band" color="risk.review" refined />
        <KpiCard icon={<RuleOutlined fontSize="large" />} loading={summaryLoading} value={s?.flag_sources?.Rule ?? "—"} label="Rule-only flags" refined />
        <KpiCard
          icon={<UpdateOutlined fontSize="large" />}
          loading={run.loading}
          value={lastRun ? RUN_STATUS[lastRun.status] || lastRun.status : run.error ? "Unavailable" : "None yet"}
          label="Last detection run"
          compact
          refined
          detail={lastRun ? formatDateTime(lastRun.finished_at || lastRun.started_at) : null}
        />
      </Box>
      {summary.error && summary.error.status !== 401 && (
        <Box role="alert" sx={{ display: "flex", alignItems: "center", gap: 2, mt: -1, mb: 3, flexWrap: "wrap" }}>
          <Typography variant="body2" color="text.secondary">
            Summary figures could not be loaded: {summary.error.message}
          </Typography>
          <Button size="small" variant="outlined" onClick={summary.retry}>Try again</Button>
        </Box>
      )}

      <Box sx={{ display: "flex", gap: 3, mb: 3, flexWrap: "wrap" }}>
        <SectionCard
          title="Flag sources"
          table={flagSourceTable}
          subtitle="Who flagged each agent in the latest run"
          result={summary}
          isEmpty={(data) => !data?.agents_scored}
          emptyText="No detection run has scored any agents yet."
          sx={{ flex: "1 1 320px" }}
          panel
        >
          {(data) => (
            <DonutChart
              refined
              slices={["ML", "Both", "Rule", "None"].map((source, i) => ({
                name: FLAG_SOURCE_LABELS[source],
                value: data.flag_sources?.[source] ?? 0,
                fill: source === "None" ? theme.palette.chart.neutral : theme.palette.chart.region[i],
              }))}
            />
          )}
        </SectionCard>
        <SectionCard
          title="Risk bands"
          table={riskBandTable}
          subtitle={(
            <>
              <Box component="span" sx={{ display: "block" }}>High: model flagged</Box>
              <Box component="span" sx={{ display: "block" }}>Review: rule only or score 1.3 and above</Box>
              <Box component="span" sx={{ display: "block" }}>Low: the rest</Box>
            </>
          )}
          result={summary}
          isEmpty={(data) => !data?.agents_scored}
          emptyText="No detection run has scored any agents yet."
          sx={{ flex: "1 1 320px" }}
          panel
        >
          {(data) => <RiskBandChart bands={data.risk_bands || {}} />}
        </SectionCard>
      </Box>

      <SectionCard
        title="Needs attention"
        subtitle={`The ${NEEDS_ATTENTION} highest-scoring high-risk agents in the latest run`}
        result={scores}
        isEmpty={(data) => !data?.scores?.some((a) => a.risk_band === "high")}
        emptyText="No agent is in the high-risk band."
        panel
      >
        {(data) => <AttentionRows agents={data.scores.filter((a) => a.risk_band === "high").slice(0, NEEDS_ATTENTION)} />}
      </SectionCard>
      {canAccess(user?.role, "flagged") && (
        <Link component={RouterLink} to="/flagged" color="primary.dark" sx={{ display: "inline-block", mt: 2, fontSize: 14, fontWeight: 500 }}>
          See all flagged agents
        </Link>
      )}
    </>
  );
}
