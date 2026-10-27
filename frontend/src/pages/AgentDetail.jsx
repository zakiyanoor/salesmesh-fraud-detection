import { useCallback, useMemo, useState } from "react";
import { useLocation, useParams, useNavigate, Link as RouterLink } from "react-router-dom";
import {
  Alert, Box, Button, Chip, Link, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography,
} from "@mui/material";
import PageHeader from "../components/PageHeader";
import RiskBadge from "../components/RiskBadge";
import ReviewPanel from "../components/ReviewPanel";
import NoteDialog from "../components/NoteDialog";
import CustomerDialog from "../components/CustomerDialog";
import AgentActivity from "../components/AgentActivity";
import DecisionTimeline from "../components/DecisionTimeline";
import SectionCard from "../components/SectionCard";
import { FlagSourceChip } from "../components/chips";
import { LoadStatus } from "../components/states";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../auth/authContext";
import { COMPLIANCE_OFFICER, FRAUD_ANALYST, PAGES } from "../auth/roles";
import { FEATURES, OUTCOME_LABELS, formatDate, formatNumber, initials } from "../format";
import { PROPOSED_MESSAGE, WITHDRAWN_MESSAGE, correctedMessage, otherOutcome } from "../review";
import { alpha } from "@mui/material/styles";
import { mono } from "../theme";
import { api } from "../api";

const CONFIRM_PATH = PAGES.find((p) => p.key === "confirm").path;

/** A card with a 16px sentence case title: 8px radius, 1px border, 20px padding, no shadow. */
function Panel({ label, title, children, sx }) {
  return (
    <Paper component="section" aria-label={label} sx={{ p: 2.5, borderRadius: "8px", boxShadow: "none", minWidth: 0, ...sx }}>
      <Typography component="h2" sx={{ fontSize: 16, fontWeight: 600, lineHeight: 1.4, mb: 1.5 }}>{title}</Typography>
      {children}
    </Paper>
  );
}

/**
 * The score against the model cutoff, read from GET /api/model-info. The bar runs from a typical agent's
 * score (about 1) at the left end to as far again past the cutoff, so the cutoff marker sits in the middle.
 */
function ScoreCard({ score, percentile, cutoff, cutoffError }) {
  const known = score != null && cutoff != null;
  const above = known && score >= cutoff;
  const span = cutoff != null ? 2 * (cutoff - 1) : 1;
  const position = known ? Math.min(Math.max((score - 1) / span, 0), 1) * 100 : 0;
  return (
    <Panel label="Score" title="Suspicion score">
      <Typography component="p" sx={{
        fontFamily: (th) => th.typography.h1.fontFamily, fontSize: 44, fontWeight: 500, lineHeight: 1.1,
        fontVariantNumeric: "tabular-nums", color: "text.primary", mb: 1,
      }}>
        {formatNumber(score, 3)}
      </Typography>
      <Typography sx={{ fontSize: 15, fontWeight: 500, mb: 1 }}>
        {score == null
          ? "Not scored in the latest run."
          : known
            ? `${above ? "At or above" : "Below"} the model cutoff of ${cutoff.toFixed(3)}${above ? ", so the model flags this agent." : "."}`
            : cutoffError ? "The model cutoff could not be loaded." : "Reading the model cutoff…"}
      </Typography>
      {score != null && percentile != null && (
        <Typography sx={{ fontSize: 14, color: "text.secondary", mb: 2 }}>
          {`Higher than ${Number(percentile).toFixed(1)}% of agents scored in the latest run. This is a rank, not a probability.`}
        </Typography>
      )}
      {cutoff != null && (
        <Box sx={{ mb: 1.5 }}>
          <Box sx={{ position: "relative", height: 16, mb: 0.5 }}>
            <Typography component="span" sx={{ position: "absolute", left: "50%", transform: "translateX(-50%)", fontSize: 12, color: "text.secondary", whiteSpace: "nowrap" }}>
              {`Cutoff ${cutoff.toFixed(3)}`}
            </Typography>
          </Box>
          <Box sx={{ position: "relative", height: 8, bgcolor: "divider", borderRadius: 4 }} aria-hidden="true">
            <Box sx={{ height: "100%", width: `${position}%`, bgcolor: above ? "risk.high" : "primary.main", borderRadius: 4 }} />
            <Box sx={{ position: "absolute", left: "50%", top: -4, bottom: -4, width: 2, bgcolor: "text.primary" }} />
          </Box>
          <Typography sx={{ fontSize: 12, color: "text.secondary", mt: 0.75 }}>Typical agent, about 1</Typography>
        </Box>
      )}
      <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
        A typical agent scores about 1. The marker is the cutoff. Scores are not probabilities.
      </Typography>
    </Panel>
  );
}

/** One aligned row per feature: name and help on the left, the value and the platform average on the right. */
function FeatureList({ features, averages }) {
  return (
    <Box component="dl" sx={{ m: 0 }}>
      {FEATURES.map((f) => {
        const value = features?.[f.key];
        const average = averages?.[f.key];
        return (
          <Box key={f.key} sx={{
            py: 1.5, borderBottom: 1, borderColor: "divider", "&:last-of-type": { borderBottom: 0, pb: 0 }, "&:first-of-type": { pt: 0 },
            display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", columnGap: 3, alignItems: "start",
          }}>
            {/* dt and dd sit directly in the row, as a description list allows; the grid places them. */}
            <Typography component="dt" sx={{ fontSize: 14, fontWeight: 500, gridColumn: 1, gridRow: 1 }}>{f.label}</Typography>
            <Typography component="dd" sx={{ fontSize: 13, color: "text.secondary", m: 0, mt: 0.25, gridColumn: 1, gridRow: 2 }}>{f.help}</Typography>
            <Box component="dd" sx={{ m: 0, textAlign: "right", gridColumn: 2, gridRow: "1 / span 2" }}>
              <Typography sx={{ ...mono, fontSize: 15, fontVariantNumeric: "tabular-nums" }}>{formatNumber(value, f.digits)}</Typography>
              {average != null && (
                <Typography sx={{ fontSize: 12, color: "text.secondary", whiteSpace: "nowrap", fontVariantNumeric: "tabular-nums" }}>
                  Platform average {formatNumber(average, f.digits)}
                </Typography>
              )}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}

function Evidence({ detail }) {
  const evidence = detail.duplicate_evidence || [];
  const [customer, setCustomer] = useState(null);
  return (
    <>
      {detail.score?.reasons && (
        <Box sx={{
          mb: 2, px: 2, py: 1.5, borderRadius: "6px", border: 1, borderColor: "divider",
          bgcolor: (th) => alpha(th.palette.primary.main, th.palette.mode === "dark" ? 0.08 : 0.04),
        }}>
          <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 0.25 }}>Model reasons</Typography>
          <Typography sx={{ fontSize: 14 }}>{detail.score.reasons}</Typography>
        </Box>
      )}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", mb: 1.5 }}>
        <Typography sx={{ fontSize: 14, color: "text.secondary" }}>Duplicate rule</Typography>
        {detail.score?.rule_flagged ? (
          <>
            <Chip size="small" variant="outlined" color="warning" label="Flagged" />
            <Typography sx={{ fontSize: 14, color: "text.secondary" }}>{`${detail.score.duplicate_pairs} customer and client pairs`}</Typography>
          </>
        ) : (
          <Chip size="small" variant="outlined" label="Not flagged" />
        )}
      </Box>
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
                  <TableCell sx={mono}>
                    {e.customer_ref ? (
                      <Link
                        component="button"
                        type="button"
                        color="primary.dark"
                        sx={{ ...mono, verticalAlign: "baseline" }}
                        onClick={() => setCustomer(e)}
                        aria-label={`Open customer ${e.customer_id}`}
                      >
                        {e.customer_id}
                      </Link>
                    ) : e.customer_id}
                  </TableCell>
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
      {customer && (
        <CustomerDialog
          customerRef={customer.customer_ref}
          customerId={customer.customer_id}
          fromAgent={detail.agent_id}
          onClose={() => setCustomer(null)}
        />
      )}
    </>
  );
}

function ReviewNote({ children, action }) {
  return (
    <Panel label="Review" title="Review">
      <Typography sx={{ fontSize: 14, color: "text.secondary", mb: action ? 2 : 0 }}>{children}</Typography>
      {action}
    </Panel>
  );
}

/**
 * What this viewer can do with the agent's flag (issue #28), from the server's review block: an analyst
 * proposes on any flagged agent or withdraws their own open proposal; a compliance officer corrects a
 * final decision here and agrees or overrules in the confirm queue.
 */
function ReviewSection({ role, detail, onDone }) {
  const review = detail.review || {};
  const [dialog, setDialog] = useState(null);
  const queue = <Button component={RouterLink} to={CONFIRM_PATH} variant="outlined">Open the confirm queue</Button>;
  const outcome = OUTCOME_LABELS[review.effective_outcome];

  if (role === FRAUD_ANALYST) {
    if (review.reviewable) {
      return <ReviewPanel flagId={review.flag_id} flagSource={review.flag_source} onProposed={() => onDone(PROPOSED_MESSAGE)} />;
    }
    if (review.open_decision_id) {
      return (
        <>
          <ReviewNote
            action={review.open_is_mine && (
              <Button variant="outlined" onClick={() => setDialog("withdraw")}>Withdraw proposal</Button>
            )}
          >
            {review.open_is_mine
              ? "Your proposal is waiting for a compliance officer. You can withdraw it until they act."
              : `A proposal by ${review.open_proposed_by} is waiting for a compliance officer.`}
          </ReviewNote>
          {dialog === "withdraw" && (
            <NoteDialog
              id="withdraw"
              title="Withdraw this proposal?"
              description="Say why you are withdrawing it. The history keeps the proposal and your note."
              noteRequired
              submitLabel="Withdraw proposal"
              onClose={() => setDialog(null)}
              onSubmit={async ({ notes }) => {
                await api.withdrawDecision({ decisionId: review.open_decision_id, notes });
                setDialog(null);
                onDone(WITHDRAWN_MESSAGE);
              }}
            />
          )}
        </>
      );
    }
    if (review.final_decision_id) {
      return <ReviewNote>{`Final outcome: ${outcome}. Only a compliance officer can correct it.`}</ReviewNote>;
    }
    return <Alert severity="info" variant="outlined">{review.reason || "There is nothing to review for this agent."}</Alert>;
  }

  if (role === COMPLIANCE_OFFICER && review.final_decision_id) {
    return (
      <>
        <ReviewNote action={<Button variant="outlined" onClick={() => setDialog("correct")}>Record a correction</Button>}>
          {`Final outcome: ${outcome}. A correction never changes the decision; it is added to the history with your note.`}
        </ReviewNote>
        {dialog === "correct" && (
          <NoteDialog
            id="correct"
            title="Record a correction"
            description={`The outcome in force is ${outcome}. Choose the corrected outcome and explain why.`}
            outcome={otherOutcome(review.effective_outcome)}
            noteRequired
            submitLabel="Record correction"
            onClose={() => setDialog(null)}
            onSubmit={async ({ outcome: newOutcome, notes }) => {
              await api.correctDecision({
                decisionId: review.final_decision_id, newOutcome, expectedCurrentOutcome: review.effective_outcome, notes,
              });
              setDialog(null);
              onDone(correctedMessage(detail.agent_id, OUTCOME_LABELS[newOutcome]));
            }}
          />
        )}
      </>
    );
  }
  if (role === COMPLIANCE_OFFICER && review.open_decision_id) {
    return <ReviewNote action={queue}>A proposal on this agent is waiting in the confirm queue.</ReviewNote>;
  }
  return (
    <ReviewNote action={queue}>
      Fraud analysts propose decisions here. Compliance officers agree or overrule them from the confirm queue.
    </ReviewNote>
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
  const modelInfo = useApi(api.getModelInfo);
  // After a review action the detail is fetched again quietly, so the page keeps its place and the message.
  const [fresh, setFresh] = useState(null);
  const [notice, setNotice] = useState(null);
  const own = useMemo(
    () => ({ ...decisions, data: decisions.data && decisions.data.decisions.filter((d) => d.agent_id === agentId) }),
    [decisions, agentId],
  );

  // Back keeps the list's filters; opened directly, it goes to the flagged list.
  const goBack = () => (location.key === "default" ? navigate("/flagged") : navigate(-1));
  const back = (
    <Link component="button" type="button" onClick={goBack} color="primary.dark" sx={{ display: "inline-block", mb: 2, fontSize: 14, fontWeight: 500 }}>
      Back to flagged agents
    </Link>
  );
  if (!result.data) {
    return (
      <Box sx={{ maxWidth: 1100 }}>
        {back}
        <PageHeader title={`Agent ${agentId}`} />
        <LoadStatus result={result} />
      </Box>
    );
  }

  const [loaded, analytics] = result.data;
  const detail = fresh?.agent_id === agentId ? fresh : loaded;
  const reviewDone = async (message) => {
    setNotice({ agentId, message });
    decisions.retry();
    setFresh(await api.getAgentDetail(agentId));
  };
  const identity = detail.identity || {};
  const score = detail.score?.anomaly_score ?? detail.flag?.suspicion_score;

  return (
    <Box sx={{ maxWidth: 1100 }}>
      {back}
      <PageHeader
        title={`Agent ${detail.agent_id}`}
        subtitle={`${detail.region ?? "Unknown county"}, registered ${formatDate(detail.registration_timestamp, { recorded: true })}${detail.account_status ? `, account ${detail.account_status}` : ""}`}
      >
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1.5 }}>
          <RiskBadge band={detail.score?.risk_band ?? detail.risk_band} />
          <FlagSourceChip source={detail.score?.flag_source ?? detail.flag_source} />
        </Box>
      </PageHeader>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "repeat(2, minmax(0, 1fr))" }, gap: 3, mb: 3, alignItems: "start" }}>
        <Box sx={{ display: "grid", gap: 3, minWidth: 0 }}>
          <ScoreCard score={score} percentile={detail.score?.score_percentile} cutoff={modelInfo.data?.cutoff} cutoffError={Boolean(modelInfo.error)} />
          <Panel label="Features" title="Features the model uses">
            <FeatureList features={detail.features} averages={analytics.platform_averages} />
          </Panel>
        </Box>
        <Box sx={{ display: "grid", gap: 3, minWidth: 0 }}>
          {notice?.agentId === agentId && (
            <Alert severity="success" role="status" onClose={() => setNotice(null)}>{notice.message}</Alert>
          )}
          <ReviewSection key={detail.review?.open_decision_id ?? detail.review?.final_decision_id ?? "none"} role={user?.role} detail={detail} onDone={reviewDone} />
          <SectionCard title="Decision history" result={own} panel sx={{ p: 2.5 }}>
            {(list) => <DecisionTimeline decisions={list} />}
          </SectionCard>
          <Panel label="Identity" title="Identity (masked)">
            <Box component="dl" sx={{ m: 0, display: "grid", gridTemplateColumns: "auto 1fr", columnGap: 3, rowGap: 0.75 }}>
              <Typography component="dt" variant="body2" color="text.secondary">Name</Typography>
              <Typography component="dd" variant="body2" sx={{ m: 0 }}>{initials(identity.full_name)}</Typography>
              <Typography component="dt" variant="body2" color="text.secondary">Phone</Typography>
              <Typography component="dd" variant="body2" sx={{ ...mono, m: 0 }}>{identity.phone_number ?? "—"}</Typography>
              <Typography component="dt" variant="body2" color="text.secondary">National ID</Typography>
              <Typography component="dd" variant="body2" sx={{ ...mono, m: 0 }}>{identity.national_id_number ?? "—"}</Typography>
            </Box>
          </Panel>
        </Box>
      </Box>

      <Panel label="Evidence" title="Evidence">
        <Evidence detail={detail} />
      </Panel>
      <AgentActivity agentId={detail.agent_id} />
    </Box>
  );
}
