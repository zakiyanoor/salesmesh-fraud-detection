import { TextField } from "@mui/material";
import { filterWidth } from "./filters";

/** A date typed as day/month/year, with its error under the field. */
export default function DayField({ label, value, onChange, error, width = 160 }) {
  return (
    <TextField
      size="small"
      label={label}
      placeholder="dd/mm/yyyy"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      error={Boolean(error)}
      helperText={error || undefined}
      slotProps={{ inputLabel: { shrink: true }, htmlInput: { inputMode: "numeric", autoComplete: "off", maxLength: 10 } }}
      sx={filterWidth(width)}
    />
  );
}
