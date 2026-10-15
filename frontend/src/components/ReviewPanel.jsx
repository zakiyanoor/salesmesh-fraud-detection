import { useState } from "react";
import {
  Alert, Box, Button, Divider, FormControl, FormControlLabel, FormHelperText, FormLabel, Paper, Radio, RadioGroup,
  TextField, Typography,
} from "@mui/material";
import { NOTES_HINT, NOTES_MAX, PROPOSED_MESSAGE, notesError } from "../review";
import { OUTCOME_LABELS } from "../format";
import { api } from "../api";

/** Fraud analysts propose a decision on a model flag; a compliance officer confirms it later. */
export default function ReviewPanel({ flagId, onProposed }) {
  const [outcome, setOutcome] = useState("");
  const [notes, setNotes] = useState("");
  const [touched, setTouched] = useState(false);
  const [status, setStatus] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const outcomeError = touched && !outcome ? "Choose an outcome." : null;
  const noteError = touched ? notesError(notes) : null;
  const length = notes.trim().length;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setTouched(true);
    setStatus(null);
    if (!outcome || notesError(notes)) return;
    setSubmitting(true);
    try {
      await api.proposeDecision({ flagId, decisionOutcome: outcome, notes: notes.trim() });
      setStatus({ type: "success", message: PROPOSED_MESSAGE });
      setOutcome("");
      setNotes("");
      setTouched(false);
      onProposed?.();
    } catch (err) {
      setStatus({ type: "error", message: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Paper component="section" aria-label="Propose a decision" sx={{ p: 3 }}>
      <Typography variant="overline" color="text.secondary" component="h2">Propose a decision</Typography>
      <Divider sx={{ mb: 2, mt: 1 }} />
      {status && <Alert severity={status.type} sx={{ mb: 2 }} role={status.type === "error" ? "alert" : "status"}>{status.message}</Alert>}

      <Box component="form" noValidate onSubmit={handleSubmit}>
        <FormControl error={Boolean(outcomeError)} required>
          <FormLabel id="decision-outcome-label">Outcome</FormLabel>
          <RadioGroup aria-labelledby="decision-outcome-label" value={outcome} onChange={(e) => setOutcome(e.target.value)}>
            {Object.entries(OUTCOME_LABELS).map(([value, label]) => (
              <FormControlLabel key={value} value={value} control={<Radio />} label={label} />
            ))}
          </RadioGroup>
          {outcomeError && <FormHelperText>{outcomeError}</FormHelperText>}
        </FormControl>

        <TextField
          label="Notes"
          required
          multiline
          minRows={3}
          fullWidth
          sx={{ mt: 2 }}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          error={Boolean(noteError) || length > NOTES_MAX}
          helperText={
            <Box component="span" sx={{ display: "flex", justifyContent: "space-between", gap: 2 }}>
              <span>{noteError || NOTES_HINT}</span>
              <Box component="span" aria-live="polite" sx={{ whiteSpace: "nowrap" }}>{length} / {NOTES_MAX}</Box>
            </Box>
          }
        />

        <Button type="submit" variant="contained" fullWidth disabled={submitting} sx={{ mt: 3, py: 1.2 }}>
          Propose decision
        </Button>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
          A compliance officer must confirm the decision before it takes effect.
        </Typography>
      </Box>
    </Paper>
  );
}
