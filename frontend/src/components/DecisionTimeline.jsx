import { Box, Typography } from "@mui/material";
import { CorrectedChip, DecisionStatusChip, OutcomeChip } from "./chips";
import { OUTCOME_LABELS, formatDateTime } from "../format";

const noteSx = { mt: 0.5, whiteSpace: "pre-wrap", overflowWrap: "anywhere" };
const when = (at) => (at ? ` on ${formatDateTime(at)}` : "");

function Step({ children, note }) {
  return (
    <Box sx={{ mt: 1 }}>
      <Typography variant="body2" color="text.secondary">{children}</Typography>
      {note && <Typography variant="body2" sx={noteSx}>{note}</Typography>}
    </Box>
  );
}

function closing(d) {
  if (d.status === "withdrawn") return <Step note={d.close_note}>{`Withdrawn by ${d.closed_by}${when(d.closed_at)}`}</Step>;
  if (d.status === "agreed") return <Step note={d.close_note}>{`Agreed by ${d.closed_by}${when(d.closed_at)}`}</Step>;
  if (d.status === "overruled") {
    return (
      <Step note={d.close_note}>
        {`Overruled by ${d.closed_by}${when(d.closed_at)}: final outcome ${OUTCOME_LABELS[d.final_outcome]}`}
      </Step>
    );
  }
  return <Step>{d.overdue ? "Waiting for a compliance officer (overdue)" : "Waiting for a compliance officer"}</Step>;
}

/**
 * An agent's review decisions, newest first (issue #28). Each shows every step in order: the proposal, its
 * withdrawal, agreement or overrule, then each correction, with who, when, the outcomes and the notes.
 */
export default function DecisionTimeline({ decisions }) {
  if (decisions.length === 0) {
    return <Typography variant="body2" color="text.secondary">No decisions have been proposed for this agent yet.</Typography>;
  }
  return (
    <Box component="ol" aria-label="Decision history" sx={{ listStyle: "none", m: 0, p: 0 }}>
      {decisions.map((d) => {
        const corrections = d.corrections || [];
        const final = d.status === "agreed" || d.status === "overruled";
        return (
          <Box
            component="li"
            key={d.decision_id}
            sx={{ position: "relative", pl: 3, pb: 2.5, borderLeft: 2, borderColor: "divider", "&:last-of-type": { pb: 0 } }}
          >
            <Box
              aria-hidden="true"
              sx={{ position: "absolute", left: -6, top: 4, width: 10, height: 10, borderRadius: "50%", bgcolor: final ? "success.main" : "warning.main" }}
            />
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 0.75 }}>
              <OutcomeChip outcome={d.decision_outcome} />
              <DecisionStatusChip status={d.status} />
              {corrections.length > 0 && <CorrectedChip />}
            </Box>
            <Step note={d.notes || "No notes (recorded before notes were required)."}>
              {`Proposed by ${d.reviewer_id}${when(d.decision_timestamp)}`}
            </Step>
            {closing(d)}
            {corrections.map((c) => (
              <Step key={c.correction_id} note={c.note}>
                {`Corrected by ${c.corrected_by}${when(c.corrected_at)}: ${OUTCOME_LABELS[c.previous_outcome]} to ${OUTCOME_LABELS[c.new_outcome]}`}
              </Step>
            ))}
            {corrections.length > 0 && (
              <Typography variant="body2" sx={{ mt: 1, fontWeight: 500 }}>
                {`Outcome in force: ${OUTCOME_LABELS[d.effective_outcome]}`}
              </Typography>
            )}
          </Box>
        );
      })}
    </Box>
  );
}
