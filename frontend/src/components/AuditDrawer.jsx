import { Box, Divider, Drawer, IconButton, Typography } from "@mui/material";
import CloseIcon from "@mui/icons-material/CloseOutlined";
import AgentId from "./AgentId";
import { AuditResultChip } from "./chips";
import { AUDIT_ACTIONS, AUDIT_CATEGORIES, safeDetails } from "../audit";
import { formatDateTime } from "../format";
import { mono } from "../theme";

function Value({ value }) {
  if (value === null || value === undefined || value === "") return <Box component="span" sx={{ color: "text.secondary" }}>—</Box>;
  if (Array.isArray(value)) return value.length ? value.map((v) => (typeof v === "object" ? JSON.stringify(v) : String(v))).join(", ") : "—";
  if (typeof value === "object") {
    return <Box component="pre" sx={{ ...mono, m: 0, whiteSpace: "pre-wrap", fontSize: 12 }}>{JSON.stringify(value, null, 2)}</Box>;
  }
  return String(value);
}

function Field({ label, children, monospace = false }) {
  return (
    <>
      <Typography component="dt" variant="caption" color="text.secondary" sx={{ pt: 0.25 }}>{label}</Typography>
      <Box component="dd" sx={{ m: 0, minWidth: 0, overflowWrap: "anywhere", typography: "body2", ...(monospace && mono) }}>{children}</Box>
    </>
  );
}

/**
 * One audit event in full. MUI's temporary Drawer is a modal: it traps focus, closes with Esc,
 * and returns focus to the element that opened it (the row or its Details button).
 */
export default function AuditDrawer({ entry, onClose }) {
  const details = safeDetails(entry?.details);
  return (
    <Drawer
      anchor="right"
      open={Boolean(entry)}
      onClose={onClose}
      slotProps={{ paper: { role: "dialog", "aria-modal": true, "aria-labelledby": "audit-drawer-title", sx: { width: { xs: "100%", sm: 440 }, p: 3 } } }}
    >
      {entry && (
        <>
          <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 2 }}>
            <Typography id="audit-drawer-title" variant="h6" component="h2">{AUDIT_ACTIONS[entry.action] || entry.action}</Typography>
            <IconButton aria-label="Close details" onClick={onClose} edge="end"><CloseIcon /></IconButton>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{formatDateTime(entry.timestamp)}</Typography>
          <Divider sx={{ mb: 2 }} />
          <Box component="dl" sx={{ m: 0, display: "grid", gridTemplateColumns: "auto 1fr", columnGap: 2, rowGap: 1 }}>
            <Field label="Result"><AuditResultChip entry={entry} /></Field>
            <Field label="Actor" monospace>{entry.actor}</Field>
            <Field label="Actor type">{entry.actor_type}</Field>
            <Field label="Category">{AUDIT_CATEGORIES[entry.category] || entry.category}</Field>
            <Field label="Action" monospace>{entry.action}</Field>
            <Field label="Agent"><AgentId id={entry.target_agent_id} /></Field>
            <Field label="Request IP (masked)" monospace>{entry.request_ip || "—"}</Field>
          </Box>
          <Typography variant="overline" color="text.secondary" component="h3" sx={{ display: "block", mt: 3 }}>Details</Typography>
          {details.length === 0 ? (
            <Typography variant="body2" color="text.secondary">No further details.</Typography>
          ) : (
            <Box component="dl" sx={{ m: 0, display: "grid", gridTemplateColumns: "auto 1fr", columnGap: 2, rowGap: 1 }}>
              {details.map(([key, value]) => (
                <Field key={key} label={key} monospace={typeof value !== "string" || key.endsWith("_id")}>
                  {key === "notes" ? <Box component="span" sx={{ whiteSpace: "pre-wrap" }}>{value}</Box> : <Value value={value} />}
                </Field>
              ))}
            </Box>
          )}
        </>
      )}
    </Drawer>
  );
}
