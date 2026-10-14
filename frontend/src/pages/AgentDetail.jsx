import { useCallback, useMemo } from "react";
import { useLocation, useParams, useNavigate, Link as RouterLink } from "react-router-dom";
import {
  Alert, Box, Button, Divider, Link, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography,
} from "@mui/material";
import PageHeader from "../components/PageHeader";
import RiskBadge from "../components/RiskBadge";
import ReviewPanel from "../components/ReviewPanel";
import DecisionTimeline from "../components/DecisionTimeline";
import SectionCard from "../components/SectionCard";
import { FlagSourceChip } from "../components/chips";
import { LoadStatus } from "../components/states";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../auth/authContext";
import { FRAUD_ANALYST, PAGES } from "../auth/roles";
import { CUTOFF, FEATURES, formatDate, formatNumber, initials } from "../format";
import { mono } from "../theme";
import { api } from "../api";

const CONFIRM_PATH = PAGES.find((p) => p.key === "confirm").path;

function ScoreCard({ score }) {
  const above = score != null && score >= CUTOFF;
  // The bar runs from 0 to twice the cutoff, so the cutoff sits in the middle.
  const position = score == null ? 0 : Math.min(score / (2 * CUTOFF), 1) * 100;
  return (
    <Paper component="section" aria-label="Score" sx={{ p: 3 }}>
      <Typography variant="overline" color="text.secondary" component="h2">Suspicion score</Typography>
      <Typography variant="h2" component="p" sx={{ ...mono, color: "primary.main" }}>{formatNumber(score, 3)}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        {score == null
          ? "Not scored in the latest run."
          : `${above ? "At or above" : "Below"} the model cutoff of ${CUTOFF.toFixed(3)}${above ? ", so the model flags this agent." : "."}`}
      </Typography>
      <Box sx={{ position: "relative", height: 8, bgcolor: "divider", borderRadius: 4 }} aria-hidden="true">
        <Box sx={{ height: "100%", width: `${position}%`, bgcolor: above ? "risk.high" : "primary.main", borderRadius: 4 }} />
        <Box sx={{ position: "absolute", left: "50%", top: -4, bottom: -4, width: 2, bgcolor: "text.primary" }} />
      </Box>
      <Typography variant="caption" color="text.secondary">
        A typical agent scores about 1. The marker is the cutoff. Scores are not probabilities.
      </Typography>
    </Paper>
  );
}

function FeatureList({ features, averages }) {
  return (
    <Box component="dl" sx={{ m: 0 }}>
      {FEATURES.map((f) => {
        const value = features?.[f.key];
        const average = averages?.[f.key];
        return (
          <Box key={f.key} sx={{ py: 1.5, borderBottom: 1, borderColor: "divider", "&:last-of-type": { borderBottom: 0 } }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2 }}>
              <Typography component="dt" variant="body2" sx={{ fontWeight: 500 }}>{f.label}</Typography>
              <Typography component="dd" variant="body2" sx={{ ...mono, m: 0 }}>{formatNumber(value, f.digits)}</Typography>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>{f.help}</Typography>
            {average != null && (
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", ...mono }}>
                Platform average {formatNumber(average, f.digits)}
              </Typography>
            )}
          </Box>
        );
      })}
    </Box>
  );
}

function Evidence({ detail }) {
  const evidence = detail.duplicate_evidence || [];
  return (
    <>
      {detail.score?.reasons && (
        <Typography variant="body2" sx={{ mb: 2 }}>
          <Box component="span" sx={{ color: "text.secondary" }}>Model reasons: </Box>{detail.score.reasons}
        </Typography>
      )}
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Duplicate rule: {detail.score?.rule_flagged ? `flagged, ${detail.score.duplicate_pairs} customer and client pairs` : "not flagged"}
      </Typography>
      {evidence.length > 0 && (
        <TableContainer>
          <Table size="small" aria-label="Duplicate activation evidence">
            <TableHead>
              <TableRow>
                <TableCell>Customer</TableCell>
                <TableCell>Client</TableCell>
                <TableCell>Reason</TableCell>
                <TableCell>Other agent</TableCell>
                <TableCell>Records</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {evidence.map((e) => (
                <TableRow key={`${e.customer_id}-${e.client_id}-${e.other_agent_id}`}>
                  <TableCell sx={mono}>{e.customer_id}</TableCell>
                  <TableCell sx={mono}>{e.client_id}</TableCell>
                  <TableCell>{e.reason}</TableCell>
                  <TableCell sx={mono}>
                    {e.other_agent_id ? (
                      <Link component={RouterLink} to={`/agents/${e.other_agent_id}`} color="primary.dark">{e.other_agent_id}</Link>
                    ) : "—"}
                  </TableCell>
                  <TableCell sx={mono}>{e.record_ids?.length ?? 0}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </>
  );
}

function ReviewSection({ role, detail, onProposed }) {
  const flagId = detail.flag?.flag_id;
  const source = detail.score?.flag_source ?? detail.flag_source;

  if (!flagId) {
    const why = source === "Rule"
      ? "Only the duplicate rule flagged this agent. The model did not, so there is no model flag to review. The evidence on this page is read-only."
      : "This agent is not flagged by the model in the latest run, so there is nothing to review.";
    return <Alert severity="info" variant="outlined">{why}</Alert>;
  }
  if (role === FRAUD_ANALYST) return <ReviewPanel flagId={flagId} onProposed={onProposed} />;
  return (
    <Paper component="section" aria-label="Review" sx={{ p: 3 }}>
      <Typography variant="overline" color="text.secondary" component="h2">Review</Typography>
      <Divider sx={{ mb: 2, mt: 1 }} />
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Fraud analysts propose decisions here. Compliance officers confirm them from the confirm queue.
      </Typography>
      <Button component={RouterLink} to={CONFIRM_PATH} variant="outlined">Open the confirm queue</Button>
    </Paper>
  );
}

export default function AgentDetail() {
  const { agentId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const load = useCallback(() => Promise.all([api.getAgentDetail(agentId), api.getAnalytics()]), [agentId]);
  const result = useApi(load);
  const decisions = useApi(api.getReviewDecisions);
  const own = useMemo(
    () => ({ ...decisions, data: decisions.data && decisions.data.decisions.filter((d) => d.agent_id === agentId) }),
    [decisions, agentId],
  );

  // Back keeps the list's filters; opened directly, it goes to the flagged list.
  const goBack = () => (location.key === "default" ? navigate("/flagged") : navigate(-1));
  const back = <Button onClick={goBack} sx={{ mb: 3, px: 0 }}>← Back</Button>;
  if (!result.data) {
    return (
      <Box sx={{ maxWidth: 1100 }}>
        {back}
        <PageHeader title={`Agent ${agentId}`} />
        <LoadStatus result={result} />
      </Box>
    );
  }

  const [detail, analytics] = result.data;
  const identity = detail.identity || {};
  const score = detail.score?.anomaly_score ?? detail.flag?.suspicion_score;

  return (
    <Box sx={{ maxWidth: 1100 }}>
      {back}
      <PageHeader
        title={`Agent ${detail.agent_id}`}
        subtitle={`${detail.region ?? "Unknown region"} · Registered ${formatDate(detail.registration_timestamp)}${detail.account_status ? ` · Account ${detail.account_status}` : ""}`}
      >
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1.5 }}>
          <RiskBadge band={detail.score?.risk_band ?? detail.risk_band} />
          <FlagSourceChip source={detail.score?.flag_source ?? detail.flag_source} />
        </Box>
      </PageHeader>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 3, mb: 3, alignItems: "start" }}>
        <Box sx={{ display: "grid", gap: 3, minWidth: 0 }}>
          <ScoreCard score={score} />
          <Paper component="section" aria-label="Features" sx={{ p: 3 }}>
            <Typography variant="overline" color="text.secondary" component="h2">Features the model uses</Typography>
            <FeatureList features={detail.features} averages={analytics.platform_averages} />
          </Paper>
        </Box>
        <Box sx={{ display: "grid", gap: 3, minWidth: 0 }}>
          <ReviewSection role={user?.role} detail={detail} onProposed={decisions.retry} />
          <SectionCard title="Decision history" result={own}>
            {(list) => <DecisionTimeline decisions={list} />}
          </SectionCard>
          <Paper component="section" aria-label="Identity" sx={{ p: 3 }}>
            <Typography variant="overline" color="text.secondary" component="h2">Identity (masked)</Typography>
            <Box component="dl" sx={{ m: 0, mt: 1, display: "grid", gridTemplateColumns: "auto 1fr", columnGap: 2, rowGap: 0.5 }}>
              <Typography component="dt" variant="body2" color="text.secondary">Name</Typography>
              <Typography component="dd" variant="body2" sx={{ m: 0 }}>{initials(identity.full_name)}</Typography>
              <Typography component="dt" variant="body2" color="text.secondary">Phone</Typography>
              <Typography component="dd" variant="body2" sx={{ ...mono, m: 0 }}>{identity.phone_number ?? "—"}</Typography>
              <Typography component="dt" variant="body2" color="text.secondary">National ID</Typography>
              <Typography component="dd" variant="body2" sx={{ ...mono, m: 0 }}>{identity.national_id_number ?? "—"}</Typography>
            </Box>
          </Paper>
        </Box>
      </Box>

      <Paper component="section" aria-label="Evidence" sx={{ p: 3 }}>
        <Typography variant="overline" color="text.secondary" component="h2">Evidence</Typography>
        <Box sx={{ mt: 1 }}><Evidence detail={detail} /></Box>
      </Paper>
    </Box>
  );
}
