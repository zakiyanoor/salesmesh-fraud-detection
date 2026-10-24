import { useState } from "react";
import {
  Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, FormControl,
  FormControlLabel, FormLabel, Radio, RadioGroup, TextField,
} from "@mui/material";
import { NOTES_HINT, NOTES_MAX, notesError } from "../review";
import { OUTCOME_LABELS } from "../format";

/**
 * A review action that takes a note (issue #28): withdraw, agree, overrule or correct. With `outcome`, the
 * officer picks an outcome first (preset to `outcome`). onSubmit({ outcome, notes }) returns a promise; its
 * error message is shown in the dialog. The note is checked like the server does: required, or optional
 * but still at most 1000 characters.
 */
export default function NoteDialog({ id, title, description, outcome, noteRequired, submitLabel, onClose, onSubmit }) {
  const [chosen, setChosen] = useState(outcome ?? null);
  const [notes, setNotes] = useState("");
  const [touched, setTouched] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const trimmed = notes.trim();
  const noteError = touched && (noteRequired || trimmed) ? notesError(notes) : null;

  const close = () => {
    if (!busy) onClose();
  };

  const submit = async () => {
    setTouched(true);
    if ((noteRequired || trimmed) && notesError(notes)) return;
    setBusy(true);
    setError(null);
    try {
      await onSubmit({ outcome: chosen, notes: trimmed || null });
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <Dialog open onClose={close} aria-labelledby={`${id}-title`} aria-describedby={`${id}-description`} fullWidth maxWidth="sm">
      <DialogTitle id={`${id}-title`}>{title}</DialogTitle>
      <DialogContent>
        {error && <Alert severity="error" role="alert" sx={{ mb: 2 }}>{error}</Alert>}
        <DialogContentText id={`${id}-description`} sx={{ mb: 2 }}>{description}</DialogContentText>
        {outcome !== undefined && (
          <FormControl sx={{ mb: 2 }}>
            <FormLabel id={`${id}-outcome-label`}>Final outcome</FormLabel>
            <RadioGroup aria-labelledby={`${id}-outcome-label`} value={chosen} onChange={(e) => setChosen(e.target.value)}>
              {Object.entries(OUTCOME_LABELS).map(([value, label]) => (
                <FormControlLabel key={value} value={value} control={<Radio />} label={label} />
              ))}
            </RadioGroup>
          </FormControl>
        )}
        <TextField
          label={noteRequired ? "Note" : "Note (optional)"}
          required={noteRequired}
          multiline
          minRows={3}
          fullWidth
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          error={Boolean(noteError)}
          helperText={
            <Box component="span" sx={{ display: "flex", justifyContent: "space-between", gap: 2 }}>
              <span>{noteError || NOTES_HINT}</span>
              <Box component="span" aria-live="polite" sx={{ whiteSpace: "nowrap" }}>{trimmed.length} / {NOTES_MAX}</Box>
            </Box>
          }
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={close} disabled={busy}>Cancel</Button>
        <Button variant="contained" onClick={submit} disabled={busy}>{submitLabel}</Button>
      </DialogActions>
    </Dialog>
  );
}
