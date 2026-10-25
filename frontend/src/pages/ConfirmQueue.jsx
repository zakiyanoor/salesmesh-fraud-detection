import { useMemo, useRef, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { Alert, Box, Button, Divider, Link } from "@mui/material";
import DataTable from "../components/DataTable";
import NoteDialog from "../components/NoteDialog";
import PageHeader from "../components/PageHeader";
import { FlagSourceChip, NoLongerFlaggedChip, OutcomeChip, OverdueChip } from "../components/chips";
import { LoadStatus } from "../components/states";
import { nextSort } from "../components/tableState";
import { useApi } from "../hooks/useApi";
import { OUTCOME_LABELS, formatDateTime } from "../format";
import { closedMessage, otherOutcome } from "../review";
import { mono } from "../theme";
import { api } from "../api";

const notesSx = { whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxWidth: 420 };

/**
 * Compliance officers agree with or overrule proposals that a fraud analyst made (#16, #28). A proposal
 * waiting more than 3 days is marked overdue; nothing here or on the server decides one automatically.
 */
export default function ConfirmQueue() {
  const result = useApi(api.getReviewDecisions);
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

  const submit = async (decision, send) => {
    try {
      const closed = await send();
      finish(decision, closedMessage(decision.agent_id, closed.status, OUTCOME_LABELS[closed.final_outcome]), "success");
    } catch (err) {
      if (err.status === 409) {
        finish(decision, `The proposal for ${decision.agent_id} was already withdrawn or decided by someone else.`, "info");
        return;
      }
      throw err.status === 403 ? new Error(`${err.message}. Another compliance officer must decide it.`) : err;
    }
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

  const selected = action?.decision;
  const summary = selected && `Agent ${selected.agent_id}: ${selected.reviewer_id} proposed ${OUTCOME_LABELS[selected.decision_outcome]} on ${formatDateTime(selected.decision_timestamp)}. Notes: ${selected.notes || "none"}.`;

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
        emptyText="No decisions are waiting for confirmation."
      />

      {action?.kind === "agree" && (
        <NoteDialog
          id="agree"
          title="Agree with this proposal?"
          description={`${summary} Once you agree, the outcome is final; only a correction can change it.`}
          submitLabel="Agree"
          onClose={() => setAction(null)}
          onSubmit={({ notes }) => submit(selected, () => api.agreeDecision({ decisionId: selected.decision_id, notes }))}
        />
      )}
      {action?.kind === "overrule" && (
        <NoteDialog
          id="overrule"
          title="Overrule this proposal?"
          description={`${summary} Choose the final outcome and explain why you disagree.`}
          outcome={otherOutcome(selected.decision_outcome)}
          noteRequired
          submitLabel="Overrule"
          onClose={() => setAction(null)}
          onSubmit={({ outcome, notes }) => submit(selected, () => api.overruleDecision({ decisionId: selected.decision_id, finalOutcome: outcome, notes }))}
        />
      )}
    </>
  );
}
