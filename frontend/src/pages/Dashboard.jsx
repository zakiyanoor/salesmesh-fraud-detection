import { Link as RouterLink } from "react-router-dom";
import {
  Box, Button, Link, Paper, Skeleton, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography, useMediaQuery,
} from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from "recharts";
import AgentId from "../components/AgentId";
import PageHeader from "../components/PageHeader";
import RiskBadge from "../components/RiskBadge";
import ScoreWithRank from "../components/ScoreWithRank";
import SectionCard from "../components/SectionCard";
import { FlagSourceChip } from "../components/chips";
import { flagSourceTable, riskBandTable } from "../chartTables";
import { DonutChart } from "../components/DonutCard";
import { useApi } from "../hooks/useApi";
import { useLatestRun } from "../latestRun/latestRunContext";
import { useAuth } from "../auth/authContext";
import { canAccess } from "../auth/roles";
import { FLAG_SOURCE_LABELS, formatDateTime, formatNumber } from "../format";
import { api } from "../api";

const NEEDS_ATTENTION = 8;
const STALE_HOURS = 48;
const loadTopScores = () => api.getAgentScores({ limit: 50 });
const RUN_STATUS = { succeeded: "Succeeded", failed: "Failed", running: "Running" };
const RUN_DOT = { succeeded: "success.main", failed: "error.main", running: "warning.main" };

const figureFont = (th) => th.typography.h1.fontFamily;
const tabular = { fontVariantNumeric: "tabular-nums" };
const visuallyHidden = {
  position: "absolute", width: "1px", height: "1px", p: 0, m: "-1px", overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap", border: 0,
};

/** Hours since the run finished (or started), or null. */
function runAgeHours(run, now = Date.now()) {
  const at = run && Date.parse(`${run.finished_at || run.started_at}${/Z|[+-]\d\d:\d\d$/.test(run.finished_at || run.started_at) ? "" : "Z"}`);
  return Number.isFinite(at) ? (now - at) / 3_600_000 : null;
}

/** One cell of the instrument bar: a 13px label above a large figure. edge is a status colour for the left edge. */
function Figure({ label, value, loading, large = false, edge, children, sx }) {
  return (
    <Box sx={{
      bgcolor: "background.paper", px: 2.5, py: 2.25, minWidth: 0,
      borderLeft: edge ? 3 : 0, borderLeftColor: edge, borderLeftStyle: "solid", ...sx,
    }}>
      <Typography sx={{ fontSize: 13, color: "text.secondary", lineHeight: 1.4 }}>{label}</Typography>
      {loading ? (
        <Skeleton variant="text" width={72} height={large ? 52 : 44} />
      ) : (
        value !== undefined && (
          <Typography component="p" sx={{
            fontFamily: figureFont, ...tabular, fontWeight: 500, color: "text.primary",
            fontSize: large ? 40 : 32, lineHeight: 1.15, mt: 0.5, letterSpacing: "-0.01em",
          }}>
            {value}
          </Typography>
        )
      )}
      {children}
    </Box>
  );
}

/** The five summary figures as one connected instrument bar, cells separated by hairlines. */
function InstrumentBar({ summary, run }) {
  const s = summary.data;
  const lastRun = run.data?.run;
  const loading = summary.loading;
  return (
    <Paper component="section" aria-label="Summary" sx={{ borderRadius: "8px", boxShadow: "none", overflow: "hidden", mb: 3 }}>
      <Box sx={{
        display: "grid", gap: "1px", bgcolor: "divider",
        gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", md: "minmax(0, 1fr) minmax(0, 1.35fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1.25fr)" },
      }}>
        <Figure label="Agents scored" value={s?.agents_scored ?? "—"} loading={loading} />
        <Figure label="Flagged (high risk)" value={s?.risk_bands?.high ?? "—"} loading={loading} large edge="risk.high">
          <Typography sx={{ fontSize: 13, color: "text.secondary", mt: 0.75, lineHeight: 1.45 }}>
            Flagged by the model. Rule only flags are counted separately.
          </Typography>
        </Figure>
        <Figure label="Review band" value={s?.risk_bands?.review ?? "—"} loading={loading} edge="risk.review" />
        <Figure label="Rule-only flags" value={s?.flag_sources?.Rule ?? "—"} loading={loading} />
        <Figure label="Last detection run" loading={run.loading} sx={{ gridColumn: { xs: "1 / -1", md: "auto" } }}>
          {!run.loading && (
            <>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 1 }}>
                {lastRun && <Box aria-hidden="true" sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: RUN_DOT[lastRun.status] || "text.secondary", flexShrink: 0 }} />}
                <Typography component="p" sx={{ fontFamily: figureFont, fontSize: 20, fontWeight: 500, lineHeight: 1.3 }}>
                  {lastRun ? RUN_STATUS[lastRun.status] || lastRun.status : run.error ? "Unavailable" : "None yet"}
                </Typography>
              </Box>
              {lastRun && (
                <Typography sx={{ fontSize: 14, color: "text.secondary", mt: 0.5, ...tabular }}>
                  {formatDateTime(lastRun.finished_at || lastRun.started_at)}
                </Typography>
              )}
            </>
          )}
        </Figure>
      </Box>
    </Paper>
  );
}

/** Risk bands as horizontal bars with the count at the end of each bar; no value axis. */
function RiskBandChart({ bands }) {
  const theme = useTheme();
  const data = [
    { name: "High risk", count: bands.high ?? 0, fill: theme.palette.risk.high },
    { name: "Review", count: bands.review ?? 0, fill: theme.palette.risk.review },
    { name: "Low risk", count: bands.low ?? 0, fill: theme.palette.chart.neutral },
  ];
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <ResponsiveContainer width="100%" height={168}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 56, bottom: 4, left: 4 }} barCategoryGap={14}>
        <CartesianGrid horizontal={false} stroke={theme.palette.divider} />
        <XAxis type="number" hide domain={[0, max]} />
        <YAxis type="category" dataKey="name" width={76} axisLine={false} tickLine={false}
          tick={{ fill: theme.palette.text.secondary, fontSize: 13 }} />
        <Bar dataKey="count" name="Agents" radius={[0, 2, 2, 0]} isAnimationActive={false}>
          {data.map((d) => <Cell key={d.name} fill={d.fill} />)}
          <LabelList dataKey="count" position="right" fill={theme.palette.text.primary} fontSize={13}
            style={{ fontVariantNumeric: "tabular-nums" }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** A thin bar of the score against the model cutoff, with a tick at the cutoff; the text is for screen readers. */
function ScoreBar({ score, cutoff }) {
  if (score == null || cutoff == null) return null;
  const position = Math.min(score / (2 * cutoff), 1) * 100;
  const above = score >= cutoff;
  return (
    <Box sx={{ mt: 0.75, width: 120, position: "relative" }}>
      <Box aria-hidden="true" sx={{ height: 4, borderRadius: 2, bgcolor: "divider", position: "relative" }}>
        <Box sx={{ height: "100%", width: `${position}%`, borderRadius: 2, bgcolor: above ? "risk.high" : "text.secondary" }} />
        <Box sx={{ position: "absolute", left: "50%", top: -3, width: "1px", height: 10, bgcolor: "text.primary" }} />
      </Box>
      <Box component="span" sx={visuallyHidden}>
        {`${above ? "At or above" : "Below"} the model cutoff of ${formatNumber(cutoff, 3)}`}
      </Box>
    </Box>
  );
}

function ScoreCell({ agent, cutoff }) {
  return (
    <>
      <Box sx={{ ...tabular, fontSize: 15 }}><ScoreWithRank score={agent.anomaly_score} percentile={agent.score_percentile} /></Box>
      <ScoreBar score={agent.anomaly_score} cutoff={cutoff} />
    </>
  );
}

/** Needs attention: a tight table, or a compact list on narrow screens. */
function AttentionRows({ agents, cutoff }) {
  const theme = useTheme();
  const narrow = useMediaQuery(theme.breakpoints.down("sm"));
  if (narrow) {
    return (
      <Box component="ul" aria-label="Agents that need attention" sx={{ listStyle: "none", m: 0, p: 0 }}>
        {agents.map((agent) => (
          <Box component="li" key={agent.agent_id} sx={{ py: 1.5, borderBottom: 1, borderColor: "divider", "&:last-of-type": { borderBottom: 0 } }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 1 }}>
              <AgentId id={agent.agent_id} />
              <RiskBadge band={agent.risk_band} />
            </Box>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 1, mt: 1, flexWrap: "wrap" }}>
              <Box><ScoreCell agent={agent} cutoff={cutoff} /></Box>
              <FlagSourceChip source={agent.flag_source} />
            </Box>
          </Box>
        ))}
      </Box>
    );
  }
  const cell = { py: 1, px: 1.5, fontSize: 14, borderColor: "divider" };
  return (
    <TableContainer>
      <Table size="small" aria-label="Agents that need attention">
        <TableHead>
          <TableRow>
            {["Agent ID", "Score (rank)", "Risk", "Flagged by"].map((h) => (
              <TableCell key={h} sx={{ ...cell, fontSize: 13, color: "text.secondary", fontWeight: 500 }}>{h}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {agents.map((agent) => (
            <TableRow key={agent.agent_id} hover>
              <TableCell sx={cell}><AgentId id={agent.agent_id} /></TableCell>
              <TableCell sx={cell}><ScoreCell agent={agent} cutoff={cutoff} /></TableCell>
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
  const modelInfo = useApi(api.getModelInfo);
  const lastRun = run.data?.run;
  const age = runAgeHours(lastRun);
  const cutoff = modelInfo.data?.cutoff;
  const testAgents = modelInfo.data?.test_agents;
  // One blue family for the flag sources, and a neutral grey for agents nobody flagged.
  const blue = theme.palette.primary.main;
  const sourceFill = { Both: blue, ML: alpha(blue, 0.62), Rule: alpha(blue, 0.32), None: alpha(theme.palette.chart.neutral, 0.45) };

  return (
    <>
      <PageHeader title="Overview" subtitle="The latest detection run at a glance" />
      {age != null && age > STALE_HOURS && (
        <Typography data-testid="stale-run" sx={{ fontSize: 14, color: "text.secondary", mt: -1.5, mb: 2.5 }}>
          {`The latest detection run is ${Math.floor(age / 24)} days old. The figures below describe that run.`}
        </Typography>
      )}

      <InstrumentBar summary={summary} run={run} />

      {summary.error && summary.error.status !== 401 && (
        <Box role="alert" sx={{ display: "flex", alignItems: "center", gap: 2, mt: -1, mb: 3, flexWrap: "wrap" }}>
          <Typography variant="body2" color="text.secondary">
            Summary figures could not be loaded: {summary.error.message}
          </Typography>
          <Button size="small" variant="outlined" onClick={summary.retry}>Try again</Button>
        </Box>
      )}

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "repeat(2, minmax(0, 1fr))" }, gap: 3, mb: 3 }}>
        <SectionCard
          panel
          title="Flag sources"
          table={flagSourceTable}
          subtitle="Who flagged each agent in the latest run"
          result={summary}
          isEmpty={(data) => !data?.agents_scored}
          emptyText="No detection run has scored any agents yet."
        >
          {(data) => (
            <DonutChart
              thickness={12}
              stackNarrow
              animate={false}
              gap={2}
              totalSx={{ fontFamily: figureFont, ...tabular, fontWeight: 500 }}
              slices={["ML", "Both", "Rule", "None"].map((source) => ({
                name: FLAG_SOURCE_LABELS[source],
                value: data.flag_sources?.[source] ?? 0,
                fill: sourceFill[source],
              }))}
            />
          )}
        </SectionCard>
        <SectionCard
          panel
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
        >
          {(data) => <RiskBandChart bands={data.risk_bands || {}} />}
        </SectionCard>
      </Box>

      <SectionCard
        panel
        title="Needs attention"
        subtitle={`The ${NEEDS_ATTENTION} highest-scoring high-risk agents in the latest run`}
        result={scores}
        isEmpty={(data) => !data?.scores?.some((a) => a.risk_band === "high")}
        emptyText="No agent is in the high-risk band."
      >
        {(data) => (
          <AttentionRows agents={data.scores.filter((a) => a.risk_band === "high").slice(0, NEEDS_ATTENTION)} cutoff={cutoff} />
        )}
      </SectionCard>
      <Box sx={{ mt: 2, display: "grid", gap: 1 }}>
        {canAccess(user?.role, "flagged") && (
          <Link component={RouterLink} to="/flagged" color="primary.dark" sx={{ fontSize: 14, fontWeight: 500, justifySelf: "start" }}>
            See all flagged agents
          </Link>
        )}
        <Typography data-testid="training-note" sx={{ fontSize: 13, color: "text.secondary" }}>
          {"These figures include agents the model learned from."}
          {testAgents ? ` Accuracy figures come only from the ${testAgents} test agents.` : ""}
        </Typography>
      </Box>
    </>
  );
}
