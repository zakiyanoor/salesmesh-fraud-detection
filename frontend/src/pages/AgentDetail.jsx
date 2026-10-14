import { useCallback, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Box, Typography, Button, Divider, Paper, RadioGroup, FormControlLabel, Radio, TextField, Alert } from "@mui/material";
import PageHeader from "../components/PageHeader";
import RiskBadge from "../components/RiskBadge";
import { LoadStatus } from "../components/states";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../auth/authContext";
import { FRAUD_ANALYST } from "../auth/roles";
import { mono } from "../theme";
import { api } from "../api";

function ReviewForm({ flagId }) {
  const [decision, setDecision] = useState("legitimate");
  const [notes, setNotes] = useState("");
  const [submitStatus, setSubmitStatus] = useState(null);

  const handleSubmit = async () => {
    setSubmitStatus(null);
    try {
      await api.proposeDecision({ flagId, decisionOutcome: decision, notes });
      setSubmitStatus({ type: "success", message: "Review decision recorded." });
    } catch (err) {
      setSubmitStatus({ type: "error", message: err.message });
    }
  };

  return (
    <Paper sx={{ flex: 1, p: 3, alignSelf: "flex-start", width: { xs: "100%", md: "auto" }, boxSizing: "border-box" }}>
      <Typography variant="overline" color="text.secondary">Record review decision</Typography>
      <Divider sx={{ mb: 2, mt: 1 }} />
      {submitStatus && <Alert severity={submitStatus.type} sx={{ mb: 2 }}>{submitStatus.message}</Alert>}
      {flagId ? (
        <>
          <RadioGroup value={decision} onChange={(e) => setDecision(e.target.value)}>
            <FormControlLabel value="legitimate" control={<Radio />} label="Legitimate" />
            <FormControlLabel value="confirmed_fraud" control={<Radio />} label="Confirmed fraud" />
          </RadioGroup>
          <TextField label="Notes" multiline rows={3} fullWidth sx={{ mt: 2 }} value={notes} onChange={(e) => setNotes(e.target.value)} />
          <Button variant="contained" fullWidth sx={{ mt: 3, py: 1.2 }} onClick={handleSubmit}>Submit decision</Button>
        </>
      ) : (
        <Typography variant="body2" color="text.secondary">This agent has no model flag to review.</Typography>
      )}
    </Paper>
  );
}

export default function AgentDetail() {
  const { agentId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const load = useCallback(() => Promise.all([api.getAgentDetail(agentId), api.getAnalytics()]), [agentId]);
  const result = useApi(load);

  const back = (
    <Button onClick={() => navigate("/flagged")} sx={{ mb: 3, px: 0 }}>← Back to flagged agents</Button>
  );
  if (!result.data) {
    return (
      <Box sx={{ maxWidth: 1000 }}>
        {back}
        <PageHeader title={agentId} />
        <LoadStatus result={result} />
      </Box>
    );
  }

  const [data, analytics] = result.data;
  const averages = analytics.platform_averages;
  const { features, flag } = data;
  const comparisonRows = [
    { metric: "Submission frequency", agent: features?.submission_frequency, platform: averages?.submission_frequency },
    { metric: "Time-of-day distribution", agent: features?.time_of_day_dist, platform: averages?.time_of_day_dist },
    { metric: "Customer similarity", agent: features?.customer_similarity, platform: averages?.customer_similarity },
  ];

  return (
    <Box sx={{ maxWidth: 1000 }}>
      {back}
      <PageHeader title={data.agent_id} subtitle={`${data.region} · Registered ${new Date(data.registration_timestamp).toLocaleDateString()}`} />

      <Box sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 5, mb: 4 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="overline" color="text.secondary">Feature evidence</Typography>
          <Divider sx={{ mb: 2 }} />
          {[
            ["Submission frequency", features?.submission_frequency],
            ["Time-of-day distribution", features?.time_of_day_dist],
            ["Customer similarity", features?.customer_similarity],
            ["Collusion score", features?.collusion_score],
          ].map(([label, value]) => (
            <Box key={label} sx={{ display: "flex", justifyContent: "space-between", gap: 2, py: 1.2 }}>
              <Typography variant="body2" color="text.secondary">{label}</Typography>
              <Typography variant="body2" sx={mono}>{value ?? "—"}</Typography>
            </Box>
          ))}

          <Box sx={{ mt: 4 }}>
            <Typography variant="overline" color="text.secondary">Suspicion score</Typography>
            <Typography variant="h2" component="p" sx={{ ...mono, color: "primary.main" }}>
              {flag?.suspicion_score?.toFixed(3) ?? "—"}
            </Typography>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flexWrap: "wrap" }}>
              <RiskBadge band={data.risk_band} />
              <Typography variant="caption" color="text.secondary">Model: {flag?.model_version}</Typography>
            </Box>
          </Box>
        </Box>

        {user?.role === FRAUD_ANALYST ? (
          <ReviewForm flagId={flag?.flag_id} />
        ) : (
          <Paper sx={{ flex: 1, p: 3, alignSelf: "flex-start", width: { xs: "100%", md: "auto" }, boxSizing: "border-box" }}>
            <Typography variant="overline" color="text.secondary">Review decision</Typography>
            <Divider sx={{ mb: 2, mt: 1 }} />
            <Typography variant="body2" color="text.secondary">
              Fraud analysts propose decisions; compliance officers confirm them from the confirm queue.
            </Typography>
          </Paper>
        )}
      </Box>

      <Paper sx={{ p: 3 }}>
        <Typography variant="overline" color="text.secondary">Agent vs platform average</Typography>
        <Box sx={{ mt: 2 }}>
          {comparisonRows.map(({ metric, agent, platform }) => {
            const ratio = platform && agent != null ? (agent / platform) * 100 : null;
            const isHigh = ratio != null && ratio > 150;
            return (
              <Box key={metric} sx={{ mb: 2.5 }}>
                <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, mb: 0.5 }}>
                  <Typography variant="body2">{metric}</Typography>
                  <Typography variant="body2" sx={{ ...mono, color: isHigh ? "error.main" : "text.secondary" }}>
                    {ratio == null ? "—" : `${ratio.toFixed(0)}% of average`}
                  </Typography>
                </Box>
                <Box sx={{ height: 8, bgcolor: "divider", borderRadius: 4, overflow: "hidden" }}>
                  <Box sx={{ height: "100%", width: `${Math.min(ratio ?? 0, 200) / 2}%`, bgcolor: isHigh ? "error.main" : "primary.main" }} />
                </Box>
              </Box>
            );
          })}
        </Box>
      </Paper>
    </Box>
  );
}
