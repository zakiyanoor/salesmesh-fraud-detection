import { useMemo, useRef, useState } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { Alert, Box, Button, Divider, Link } from "@mui/material";
import DataTable from "../components/DataTable";
import ProposalDialog from "../components/ProposalDialog";
import PageHeader from "../components/PageHeader";
import { FlagSourceChip, NoLongerFlaggedChip, OutcomeChip, OverdueChip } from "../components/chips";
import { LoadStatus } from "../components/states";
import { nextSort } from "../components/tableState";
import { useApi } from "../hooks/useApi";
import { OUTCOME_LABELS, formatDateTime } from "../format";
import { mono } from "../theme";
import { api } from "../api";

const notesSx = { whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxWidth: 420 };

/**
 * Compliance officers agree with or overrule proposals that a fraud analyst made (#16, #28). A proposal
 * waiting more than 3 days is marked overdue; nothing here or on the server decides one automatically.
 */
export default function ConfirmQueue() {
  const result = useApi(api.getReviewDecisions);
  const navigate = useNavigate();
  const [done, setDone] = useState(() => new Set());
  const [action, setAction] = useState(null);
  const [notice, setNotice] = useState(null);
  const [sort, setSort] = useState({ key: "proposed", dir: "asc" });
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const noticeRef = useRef(null);

  const pending = useMemo(
    () => (result.data?.decisions || []).filter((d) => d.status === "pending_confirmation" && !done.has(d.decision_id)),
    [result.data, done],
  );

  const finish = (decision, message, severity) => {
    setDone((prev) => new Set(prev).add(decision.decision_id));
    setAction(null);
    setNotice({ message, severity });
    // The row is gone, so focus moves to the message instead of being lost.
    setTimeout(() => noticeRef.current?.focus(), 0);
  };

  const columns = [
    {
      key: "agent",
      label: "Agent",
      title: true,
      sortValue: (d) => d.agent_id,
      render: (d) => (d.agent_id ? (
        <Link component={RouterLink} to={`/agents/${d.agent_id}`} color="primary.dark" sx={mono}>{d.agent_id}</Link>
      ) : "—"),
    },
    {
      key: "source",
      label: "Flagged by",
      sortValue: (d) => d.flag_source || "",
      render: (d) => (
        <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
          {d.flag_source ? <FlagSourceChip source={d.flag_source} /> : "—"}
          {d.still_flagged === false && <NoLongerFlaggedChip />}
        </Box>
      ),
    },
    { key: "proposer", label: "Proposed by", sortValue: (d) => d.reviewer_id, render: (d) => d.reviewer_id },
    { key: "outcome", label: "Proposed outcome", sortValue: (d) => OUTCOME_LABELS[d.decision_outcome], render: (d) => <OutcomeChip outcome={d.decision_outcome} /> },
    { key: "notes", label: "Notes", render: (d) => <Box sx={notesSx}>{d.notes || "—"}</Box> },
    {
      key: "proposed",
      label: "Proposed on",
      sortValue: (d) => d.decision_timestamp,
      render: (d) => (
        <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
          <Box component="span" sx={{ whiteSpace: "nowrap" }}>{formatDateTime(d.decision_timestamp)}</Box>
          {d.overdue && <OverdueChip />}
        </Box>
      ),
    },
    {
      key: "action",
      label: "Actions",
      action: true,
      align: "right",
      render: (d) => (
        <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end", flexWrap: "wrap" }}>
          <Button variant="outlined" size="small" onClick={() => setAction({ kind: "agree", decision: d })} aria-label={`Agree with the proposal for ${d.agent_id}`}>
            Agree
          </Button>
          <Button variant="outlined" size="small" onClick={() => setAction({ kind: "overrule", decision: d })} aria-label={`Overrule the proposal for ${d.agent_id}`}>
            Overrule
          </Button>
        </Box>
      ),
    },
  ];

  const header = (
    <PageHeader
      title="Confirm queue"
      subtitle="Proposals from fraud analysts. A compliance officer other than the proposer agrees or overrules each one. A proposal waiting more than 3 days is marked overdue; nothing is decided automatically."
    />
  );
  if (!result.data) return <>{header}<LoadStatus result={result} /></>;

  return (
    <>
      {header}
      {notice && (
        <Alert severity={notice.severity} role="status" ref={noticeRef} tabIndex={-1} onClose={() => setNotice(null)} sx={{ mb: 3 }}>
          {notice.message}
        </Alert>
      )}
      <Divider sx={{ mb: 2 }} />
      <DataTable
        label="Decisions waiting for confirmation"
        columns={columns}
        rows={pending}
        rowKey={(d) => d.decision_id}
        sort={sort}
        onSort={(key) => setSort((current) => nextSort(current, key))}
        page={page}
        rowsPerPage={rowsPerPage}
        onPageChange={setPage}
        onRowsPerPageChange={(size) => { setRowsPerPage(size); setPage(0); }}
        onRowClick={(d) => d.agent_id && navigate(`/agents/${d.agent_id}`)}
        keyboardRows
        emptyText="No decisions are waiting for confirmation."
      />

      {action && (
        <ProposalDialog
          kind={action.kind}
          decision={action.decision}
          onClose={() => setAction(null)}
          onFinish={(message, severity) => finish(action.decision, message, severity)}
        />
      )}
    </>
  );
}
