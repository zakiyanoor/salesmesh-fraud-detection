import { useState } from "react";
import { Alert, Box, Button, Chip, CircularProgress, MenuItem, Paper, TextField, Typography } from "@mui/material";
import DayField from "../components/DayField";
import { checkDayRange } from "../components/dayDates";
import DownloadIcon from "@mui/icons-material/FileDownloadOutlined";
import PageHeader from "../components/PageHeader";
import { filterWidth } from "../components/filters";
import { AUDIT_CATEGORIES } from "../audit";
import { saveFile } from "../download";
import { api } from "../api";

/** One report card: a download button with its own loading, error and done state. */
function ReportCard({ title, format, description, download, children }) {
  const [state, setState] = useState({ status: "idle" });

  const handleDownload = async () => {
    setState({ status: "loading" });
    try {
      const file = await download();
      saveFile(file);
      setState({ status: "done", filename: file.filename, limited: file.limited });
    } catch (err) {
      setState({ status: "error", message: err.message });
    }
  };

  const busy = state.status === "loading";
  return (
    <Paper component="section" aria-label={title} sx={{ p: 3, flex: "1 1 300px", minWidth: 0, display: "flex", flexDirection: "column" }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2, mb: 1 }}>
        <Typography variant="h6" component="h2">{title}</Typography>
        <Chip size="small" variant="outlined" label={format} />
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, flexGrow: 1 }}>{description}</Typography>
      {children}
      <Box aria-live="polite">
        {state.status === "error" && <Alert severity="error" role="alert" sx={{ mb: 2 }}>Download failed: {state.message}</Alert>}
        {state.status === "done" && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Downloaded {state.filename}</Typography>
        )}
        {state.status === "done" && state.limited && (
          <Alert severity="info" variant="outlined" sx={{ mb: 2 }}>
            This export was limited to the newest 50,000 events. Narrow the category or dates to see older ones.
          </Alert>
        )}
      </Box>
      <Button
        variant="contained"
        onClick={handleDownload}
        disabled={busy}
        aria-busy={busy}
        startIcon={busy ? <CircularProgress size={16} color="inherit" aria-hidden="true" /> : <DownloadIcon />}
        sx={{ alignSelf: "flex-start" }}
      >
        {busy ? "Preparing…" : `Download ${format}`}
      </Button>
    </Paper>
  );
}

function AuditReportFilters({ filters, onChange, errors }) {
  const set = (key) => (e) => onChange({ ...filters, [key]: e.target.value });
  const setText = (key) => (value) => onChange({ ...filters, [key]: value });
  return (
    <Box sx={{ display: "flex", gap: 2, mb: 2, flexWrap: "wrap" }}>
      <TextField
        select
        size="small"
        label="Category"
        value={filters.category}
        onChange={set("category")}
        slotProps={{ select: { displayEmpty: true }, inputLabel: { shrink: true } }}
        sx={filterWidth(170)}
      >
        <MenuItem value="">All categories</MenuItem>
        {Object.entries(AUDIT_CATEGORIES).map(([value, text]) => <MenuItem key={value} value={value}>{text}</MenuItem>)}
      </TextField>
      <DayField label="From date" value={filters.date_from} onChange={setText("date_from")} error={errors.fromError} />
      <DayField label="To date" value={filters.date_to} onChange={setText("date_to")} error={errors.toError} />
    </Box>
  );
}

/** The three reports the backend offers (admin only). Every download is audited on the server. */
export default function Reports() {
  const [auditFilters, setAuditFilters] = useState({ category: "", date_from: "", date_to: "" });
  // Dates are typed as dd/mm/yyyy and sent as YYYY-MM-DD; an invalid one stops the download with a message.
  const range = checkDayRange(auditFilters.date_from, auditFilters.date_to);
  const downloadAuditLog = () => {
    if (range.fromError || range.toError) return Promise.reject(new Error("check the dates"));
    return api.downloadAuditLogCsv({ category: auditFilters.category, date_from: range.from, date_to: range.to });
  };

  return (
    <>
      <PageHeader
        title="Reports"
        subtitle="Download results to share outside the dashboard. Names, phone numbers and national IDs are masked, and every download is recorded in the audit log."
      />
      <Box sx={{ display: "flex", gap: 3, flexWrap: "wrap" }}>
        <ReportCard
          title="Flagged agents"
          format="CSV"
          description="Agents flagged by the model or the duplicate rule in the latest run, highest score first, with risk band, reasons and masked identity."
          download={api.downloadFlaggedAgentsCsv}
        />
        <ReportCard
          title="Audit log"
          format="CSV"
          description="Audit events, newest first. Narrow them by category and date."
          download={downloadAuditLog}
        >
          <AuditReportFilters filters={auditFilters} onChange={setAuditFilters} errors={range} />
        </ReportCard>
        <ReportCard
          title="Detection summary"
          format="PDF"
          description="One page: run status, model version and cutoff, counts by flag source and risk band, and the top 10 counties by flagged rate."
          download={api.downloadDetectionSummaryPdf}
        />
      </Box>
    </>
  );
}
