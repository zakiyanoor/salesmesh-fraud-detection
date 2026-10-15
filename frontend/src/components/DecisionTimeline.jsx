import { Box, Typography } from "@mui/material";
import { DecisionStatusChip, OutcomeChip } from "./chips";
import { formatDateTime } from "../format";

/** An agent's review decisions, newest first: outcome, status, who and when, and the notes. */
export default function DecisionTimeline({ decisions }) {
  if (decisions.length === 0) {
    return <Typography variant="body2" color="text.secondary">No decisions have been proposed for this agent yet.</Typography>;
  }
  return (
    <Box component="ol" aria-label="Decision history" sx={{ listStyle: "none", m: 0, p: 0 }}>
      {decisions.map((d) => (
        <Box
          component="li"
          key={d.decision_id}
          sx={{ position: "relative", pl: 3, pb: 2.5, borderLeft: 2, borderColor: "divider", "&:last-of-type": { pb: 0 } }}
        >
          <Box
            aria-hidden="true"
            sx={{ position: "absolute", left: -6, top: 4, width: 10, height: 10, borderRadius: "50%", bgcolor: d.status === "confirmed" ? "success.main" : "warning.main" }}
          />
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 0.75 }}>
            <OutcomeChip outcome={d.decision_outcome} />
            <DecisionStatusChip status={d.status} />
          </Box>
          <Typography variant="body2" color="text.secondary">
            Proposed by {d.reviewer_id} on {formatDateTime(d.decision_timestamp)}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {d.status === "confirmed" ? `Confirmed by ${d.confirmed_by}` : "Waiting for compliance confirmation"}
          </Typography>
          <Typography variant="body2" sx={{ mt: 0.75, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
            {d.notes || <Box component="span" sx={{ color: "text.secondary" }}>No notes (recorded before notes were required).</Box>}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}
