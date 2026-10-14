import { Box, Button, Link, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { Link as RouterLink } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import GroupsOutlined from "@mui/icons-material/GroupsOutlined";
import ReportOutlined from "@mui/icons-material/ReportOutlined";
import WarningAmberOutlined from "@mui/icons-material/WarningAmberOutlined";
import RuleOutlined from "@mui/icons-material/RuleOutlined";
import UpdateOutlined from "@mui/icons-material/UpdateOutlined";
import KpiCard from "../components/KpiCard";
import PageHeader from "../components/PageHeader";
import RiskBadge from "../components/RiskBadge";
import SectionCard from "../components/SectionCard";
import { DonutChart } from "../components/DonutCard";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../auth/authContext";
import { canAccess } from "../auth/roles";
import { FLAG_SOURCE_LABELS, formatDateTime, formatNumber } from "../format";
import { mono } from "../theme";
import { api } from "../api";

const NEEDS_ATTENTION = 8;
const loadTopScores = () => api.getAgentScores({ limit: 50 });
const RUN_STATUS = { succeeded: "Succeeded", failed: "Failed", running: "Running" };

function RiskBandChart({ bands }) {
  const theme = useTheme();
  const data = [
    { name: "High risk", count: bands.high ?? 0, fill: theme.palette.risk.high },
    { name: "Review", count: bands.review ?? 0, fill: theme.palette.risk.review },
    { name: "Low risk", count: bands.low ?? 0, fill: theme.palette.risk.low },
  ];
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.chart.grid} />
        <XAxis dataKey="name" stroke={theme.palette.chart.axis} fontSize={12} />
        <YAxis stroke={theme.palette.chart.axis} fontSize={12} allowDecimals={false} />
        <Tooltip
          cursor={{ fill: theme.palette.action.selected }}
          contentStyle={{
            background: theme.palette.background.paper,
            border: `1px solid ${theme.palette.divider}`,
            color: theme.palette.text.primary,
          }}
        />
        <Bar dataKey="count" name="Agents" radius={[3, 3, 0, 0]}>
          {data.map((d) => <Cell key={d.name} fill={d.fill} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Overview: the latest detection run at a glance, for every role. */
export default function Dashboard() {
  const theme = useTheme();
  const { user } = useAuth();
  const summary = useApi(api.getThreatSummary);
  const run = useApi(api.getLatestDetectionRun);
  const scores = useApi(loadTopScores);
  const canOpenAgents = canAccess(user?.role, "agentDetail");

  const s = summary.data;
  const lastRun = run.data?.run;
  const summaryLoading = summary.loading;

  return (
    <>
      <PageHeader title="Overview" subtitle="The latest detection run at a glance" />

      <Box component="section" aria-label="Summary" sx={{ display: "flex", gap: 3, mb: 4, flexWrap: "wrap" }}>
        <KpiCard icon={<GroupsOutlined fontSize="large" />} loading={summaryLoading} value={s?.agents_scored ?? "—"} label="Agents scored" />
        <KpiCard icon={<ReportOutlined fontSize="large" />} loading={summaryLoading} value={s?.risk_bands?.high ?? "—"} label="Flagged (high risk)" color="risk.high" />
        <KpiCard icon={<WarningAmberOutlined fontSize="large" />} loading={summaryLoading} value={s?.risk_bands?.review ?? "—"} label="Review band" color="risk.review" />
        <KpiCard icon={<RuleOutlined fontSize="large" />} loading={summaryLoading} value={s?.flag_sources?.Rule ?? "—"} label="Rule-only flags" />
        <KpiCard
          icon={<UpdateOutlined fontSize="large" />}
          loading={run.loading}
          value={lastRun ? RUN_STATUS[lastRun.status] || lastRun.status : run.error ? "Unavailable" : "None yet"}
          label="Last detection run"
          detail={lastRun ? formatDateTime(lastRun.finished_at || lastRun.started_at) : null}
        />
      </Box>
      {summary.error && summary.error.status !== 401 && (
        <Box role="alert" sx={{ display: "flex", alignItems: "center", gap: 2, mt: -2, mb: 3, flexWrap: "wrap" }}>
          <Typography variant="body2" color="text.secondary">
            Summary figures could not be loaded: {summary.error.message}
          </Typography>
          <Button size="small" variant="outlined" onClick={summary.retry}>Try again</Button>
        </Box>
      )}

      <Box sx={{ display: "flex", gap: 3, mb: 4, flexWrap: "wrap" }}>
        <SectionCard
          title="Flag sources"
          subtitle="Who flagged each agent in the latest run"
          result={summary}
          isEmpty={(data) => !data?.agents_scored}
          emptyText="No detection run has scored any agents yet."
          sx={{ flex: "1 1 320px" }}
        >
          {(data) => (
            <DonutChart
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
          subtitle="High: model flagged · Review: rule only or score 1.3 and above · Low: the rest"
          result={summary}
          isEmpty={(data) => !data?.agents_scored}
          emptyText="No detection run has scored any agents yet."
          sx={{ flex: "1 1 320px" }}
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
      >
        {(data) => (
          <TableContainer>
            <Table size="small" aria-label="Agents that need attention">
              <TableHead>
                <TableRow>
                  <TableCell>Agent ID</TableCell>
                  <TableCell>Score</TableCell>
                  <TableCell>Risk</TableCell>
                  <TableCell>Flagged by</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.scores
                  .filter((a) => a.risk_band === "high")
                  .slice(0, NEEDS_ATTENTION)
                  .map((agent) => (
                    <TableRow key={agent.agent_id} hover>
                      <TableCell sx={mono}>
                        {canOpenAgents ? (
                          <Link component={RouterLink} to={`/agents/${agent.agent_id}`} color="primary.dark">{agent.agent_id}</Link>
                        ) : (
                          agent.agent_id
                        )}
                      </TableCell>
                      <TableCell sx={mono}>{formatNumber(agent.anomaly_score, 3)}</TableCell>
                      <TableCell><RiskBadge band={agent.risk_band} /></TableCell>
                      <TableCell>{FLAG_SOURCE_LABELS[agent.flag_source] || agent.flag_source}</TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </SectionCard>
    </>
  );
}
