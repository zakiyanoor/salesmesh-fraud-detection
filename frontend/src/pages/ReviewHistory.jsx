import { useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Link, MenuItem, TextField,
} from "@mui/material";
import DataTable from "../components/DataTable";
import DecisionTimeline from "../components/DecisionTimeline";
import PageHeader from "../components/PageHeader";
import { CorrectedChip, DecisionStatusChip, OutcomeChip } from "../components/chips";
import { LoadStatus } from "../components/states";
import { filterWidth } from "../components/filters";
import { nextSort, paging } from "../components/tableState";
import { useApi } from "../hooks/useApi";
import { useQueryParams } from "../hooks/useQueryParams";
import { OUTCOME_LABELS, STATUS_LABELS, formatDateTime } from "../format";
import { mono } from "../theme";
import { api } from "../api";

const DEFAULTS = { status: "all", outcome: "all", sort: "proposed", dir: "desc", page: "0", size: "25" };

const muted = (text) => <Box component="span" sx={{ color: "text.secondary" }}>{text}</Box>;

const COLUMNS = [
  {
    key: "agent",
    label: "Agent",
    title: true,
    sortValue: (d) => d.agent_id,
    render: (d) => (d.agent_id ? (
      <Link component={RouterLink} to={`/agents/${d.agent_id}`} color="primary.dark" sx={mono}>{d.agent_id}</Link>
    ) : "—"),
  },
  { key: "outcome", label: "Proposed outcome", sortValue: (d) => OUTCOME_LABELS[d.decision_outcome], render: (d) => <OutcomeChip outcome={d.decision_outcome} /> },
  {
    key: "status",
    label: "Status",
    sortValue: (d) => STATUS_LABELS[d.status],
    render: (d) => (
      <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
        <DecisionStatusChip status={d.status} />
        {d.corrections?.length > 0 && <CorrectedChip />}
      </Box>
    ),
  },
  {
    key: "final",
    label: "Outcome in force",
    sortValue: (d) => OUTCOME_LABELS[d.effective_outcome] || "",
    render: (d) => (d.effective_outcome ? <OutcomeChip outcome={d.effective_outcome} /> : muted("—")),
  },
  { key: "proposer", label: "Proposed by", sortValue: (d) => d.reviewer_id, render: (d) => d.reviewer_id },
  {
    key: "closer",
    label: "Closed by",
    sortValue: (d) => d.closed_by || "",
    render: (d) => d.closed_by || muted("Waiting"),
  },
  {
    key: "notes",
    label: "Notes",
    render: (d) => (
      <Box sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxWidth: 360 }}>
        {d.notes || <Box component="span" sx={{ color: "text.secondary" }}>None (before notes were required)</Box>}
      </Box>
    ),
  },
  {
    key: "proposed",
    label: "Proposed on",
    sortValue: (d) => d.decision_timestamp,
    render: (d) => <Box component="span" sx={{ whiteSpace: "nowrap" }}>{formatDateTime(d.decision_timestamp)}</Box>,
  },
];

/** Every review decision and what happened to it (#15, #28); each row opens its full history. */
export default function ReviewHistory() {
  const result = useApi(api.getReviewDecisions);
  const [open, setOpen] = useState(null);
  const columns = [
    ...COLUMNS,
    {
      key: "history",
      label: "History",
      action: true,
      align: "right",
      render: (d) => (
        <Button size="small" onClick={() => setOpen(d)} aria-label={`Show the history of the decision for ${d.agent_id}`}>History</Button>
      ),
    },
  ];
  const [query, setQuery] = useQueryParams(DEFAULTS);
  const { page, rowsPerPage } = paging(query);

  const decisions = useMemo(() => result.data?.decisions || [], [result.data]);
  const filtered = useMemo(
    () => decisions.filter(
      (d) => (query.status === "all" || d.status === query.status) && (query.outcome === "all" || d.decision_outcome === query.outcome),
    ),
    [decisions, query.status, query.outcome],
  );

  const header = (
    <PageHeader
      title="Review history"
      subtitle="Every proposal on a flagged agent and what happened to it. A proposal has no effect until a compliance officer agrees or overrules it; a correction never changes the decision, it is added to its history. Dates are when the proposal was made."
    />
  );
  if (!result.data) return <>{header}<LoadStatus result={result} /></>;

  const filtersActive = query.status !== "all" || query.outcome !== "all";

  return (
    <>
      {header}
      <Box component="form" role="search" aria-label="Filter decisions" onSubmit={(e) => e.preventDefault()} sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap", alignItems: "center" }}>
        <TextField select size="small" label="Status" value={query.status} onChange={(e) => setQuery({ status: e.target.value, page: 0 })} sx={filterWidth(180)}>
          <MenuItem value="all">All statuses</MenuItem>
          {Object.entries(STATUS_LABELS).map(([value, text]) => <MenuItem key={value} value={value}>{text}</MenuItem>)}
        </TextField>
        <TextField select size="small" label="Proposed outcome" value={query.outcome} onChange={(e) => setQuery({ outcome: e.target.value, page: 0 })} sx={filterWidth(180)}>
          <MenuItem value="all">All outcomes</MenuItem>
          {Object.entries(OUTCOME_LABELS).map(([value, text]) => <MenuItem key={value} value={value}>{text}</MenuItem>)}
        </TextField>
        {filtersActive && <Button onClick={() => setQuery({ status: "all", outcome: "all", page: 0 })}>Clear filters</Button>}
      </Box>
      <Divider sx={{ mb: 2 }} />
      <DataTable
        label="Review decisions"
        columns={columns}
        rows={filtered}
        rowKey={(d) => d.decision_id}
        sort={{ key: query.sort, dir: query.dir === "asc" ? "asc" : "desc" }}
        onSort={(key) => {
          const next = nextSort({ key: query.sort, dir: query.dir }, key);
          setQuery({ sort: next.key, dir: next.dir, page: 0 });
        }}
        page={page}
        rowsPerPage={rowsPerPage}
        onPageChange={(next) => setQuery({ page: next })}
        onRowsPerPageChange={(size) => setQuery({ size, page: 0 })}
        emptyText={decisions.length === 0 ? "No decisions recorded yet." : "No decisions match your filters."}
      />
      <Dialog open={Boolean(open)} onClose={() => setOpen(null)} aria-labelledby="history-title" fullWidth maxWidth="sm">
        {open && (
          <>
            <DialogTitle id="history-title">{`Decision history for ${open.agent_id}`}</DialogTitle>
            <DialogContent><DecisionTimeline decisions={[open]} /></DialogContent>
            <DialogActions><Button onClick={() => setOpen(null)}>Close</Button></DialogActions>
          </>
        )}
      </Dialog>
    </>
  );
}
