import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Box, Typography, Button, Divider, Paper, RadioGroup, FormControlLabel, Radio, TextField, Alert, CircularProgress } from "@mui/material";
import Sidebar, { DRAWER_WIDTH } from "../components/Sidebar";
import RiskBadge from "../components/RiskBadge";
import { mono } from "../theme";
import { api } from "../api";

export default function AgentDetail({ username, onLogout }) {
  const { agentId } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [averages, setAverages] = useState(null);
  const [loading, setLoading] = useState(true);
  const [decision, setDecision] = useState("legitimate");
  const [notes, setNotes] = useState("");
  const [submitStatus, setSubmitStatus] = useState(null);

  useEffect(() => {
    Promise.all([api.getAgentDetail(agentId), api.getAnalytics()])
      .then(([detail, analytics]) => {
        setData(detail);
        setAverages(analytics.platform_averages);
      })
      .catch(onLogout)
      .finally(() => setLoading(false));
  }, [agentId, onLogout]);

  const handleSubmit = async () => {
    setSubmitStatus(null);
    try {
      await api.submitReviewDecision(data.flag.flag_id, decision);
      setSubmitStatus({ type: "success", message: "Review decision recorded." });
    } catch (err) {
      setSubmitStatus({ type: "error", message: err.message });
    }
  };

  if (loading) {
    return <Box sx={{ display: "flex", justifyContent: "center", mt: 10 }}><CircularProgress /></Box>;
  }

  const { features, flag } = data;
  const comparisonRows = [
    { metric: "Submission frequency", agent: features?.submission_frequency, platform: averages?.submission_frequency },
    { metric: "Time-of-day distribution", agent: features?.time_of_day_dist, platform: averages?.time_of_day_dist },
    { metric: "Customer similarity", agent: features?.customer_similarity, platform: averages?.customer_similarity },
  ];

  return (
    <Box sx={{ display: "flex" }}>
      <Sidebar username={username} onLogout={onLogout} />

      <Box sx={{ flexGrow: 1, p: 5, ml: `${DRAWER_WIDTH}px`, maxWidth: 1000 }}>
        <Button onClick={() => navigate("/")} sx={{ mb: 3, px: 0 }}>← Back to flagged agents</Button>

        <Typography variant="h4" sx={mono}>{data.agent_id}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          {data.region} · Registered {new Date(data.registration_timestamp).toLocaleDateString()}
        </Typography>

        <Box sx={{ display: "flex", gap: 5, mb: 4 }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="overline" color="text.secondary">Feature evidence</Typography>
            <Divider sx={{ mb: 2 }} />
            {[
              ["Submission frequency", features?.submission_frequency],
              ["Time-of-day distribution", features?.time_of_day_dist],
              ["Customer similarity", features?.customer_similarity],
              ["Collusion score", features?.collusion_score],
            ].map(([label, value]) => (
              <Box key={label} sx={{ display: "flex", justifyContent: "space-between", py: 1.2 }}>
                <Typography variant="body2" color="text.secondary">{label}</Typography>
                <Typography variant="body2" sx={mono}>{value ?? "—"}</Typography>
              </Box>
            ))}

            <Box sx={{ mt: 4 }}>
              <Typography variant="overline" color="text.secondary">Suspicion score</Typography>
              <Typography variant="h2" sx={{ ...mono, color: "primary.main" }}>
                {flag?.suspicion_score?.toFixed(3) ?? "—"}
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flexWrap: "wrap" }}>
                <RiskBadge band={data.risk_band} />
                <Typography variant="caption" color="text.secondary">Model: {flag?.model_version}</Typography>
              </Box>
            </Box>
          </Box>

          <Paper sx={{ flex: 1, p: 3, alignSelf: "flex-start" }}>
            <Typography variant="overline" color="text.secondary">Record review decision</Typography>
            <Divider sx={{ mb: 2, mt: 1 }} />
            {submitStatus && <Alert severity={submitStatus.type} sx={{ mb: 2 }}>{submitStatus.message}</Alert>}
            <RadioGroup value={decision} onChange={(e) => setDecision(e.target.value)}>
              <FormControlLabel value="legitimate" control={<Radio />} label="Legitimate" />
              <FormControlLabel value="confirmed_fraud" control={<Radio />} label="Confirmed fraud" />
            </RadioGroup>
            <TextField label="Notes (optional)" multiline rows={3} fullWidth sx={{ mt: 2 }} value={notes} onChange={(e) => setNotes(e.target.value)} />
            <Button variant="contained" fullWidth sx={{ mt: 3, py: 1.2 }} onClick={handleSubmit}>Submit decision</Button>
          </Paper>
        </Box>

        <Paper sx={{ p: 3 }}>
          <Typography variant="overline" color="text.secondary">Agent vs platform average</Typography>
          <Box sx={{ mt: 2 }}>
            {comparisonRows.map(({ metric, agent, platform }) => {
              const ratio = platform ? (agent / platform) * 100 : 0;
              const isHigh = ratio > 150;
              return (
                <Box key={metric} sx={{ mb: 2.5 }}>
                  <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                    <Typography variant="body2">{metric}</Typography>
                    <Typography variant="body2" sx={{ ...mono, color: isHigh ? "error.main" : "text.secondary" }}>
                      {ratio.toFixed(0)}% of average
                    </Typography>
                  </Box>
                  <Box sx={{ height: 8, bgcolor: "divider", borderRadius: 4, overflow: "hidden" }}>
                    <Box sx={{ height: "100%", width: `${Math.min(ratio, 200) / 2}%`, bgcolor: isHigh ? "error.main" : "primary.main" }} />
                  </Box>
                </Box>
              );
            })}
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}