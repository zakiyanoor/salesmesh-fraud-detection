import { useMemo, useRef, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Divider, Link, Typography,
} from "@mui/material";
import DataTable from "../components/DataTable";
import PageHeader from "../components/PageHeader";
import { OutcomeChip } from "../components/chips";
import { LoadStatus } from "../components/states";
import { nextSort } from "../components/tableState";
import { useApi } from "../hooks/useApi";
import { OUTCOME_LABELS, formatDateTime } from "../format";
import { confirmedMessage } from "../review";
import { mono } from "../theme";
import { api } from "../api";

const notesSx = { whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxWidth: 420 };

/** Compliance officers confirm decisions that a fraud analyst proposed (#16). */
export default function ConfirmQueue() {
  const result = useApi(api.getReviewDecisions);
  const [done, setDone] = useState(() => new Set());
  const [selected, setSelected] = useState(null);
  const [dialogError, setDialogError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const [sort, setSort] = useState({ key: "proposed", dir: "asc" });
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const noticeRef = useRef(null);

  const pending = useMemo(
    () => (result.data?.decisions || []).filter((d) => d.status === "pending_confirmation" && !done.has(d.decision_id)),
    [result.data, done],
  );

  const close = () => {
    if (busy) return;
    setSelected(null);
    setDialogError(null);
  };

  const finish = (decision, message, severity) => {
    setDone((prev) => new Set(prev).add(decision.decision_id));
    setSelected(null);
    setDialogError(null);
    setNotice({ message, severity });
    // The row is gone, so focus moves to the message instead of being lost.
    setTimeout(() => noticeRef.current?.focus(), 0);
  };

  const confirm = async () => {
    setBusy(true);
    setDialogError(null);
    try {
      await api.confirmDecision(selected.decision_id);
      finish(selected, confirmedMessage(selected.agent_id), "success");
    } catch (err) {
      if (err.status === 409) {
        finish(selected, `The decision for ${selected.agent_id} was already confirmed by someone else.`, "info");
      } else {
        setDialogError(err.status === 403 ? `${err.message}. Another compliance officer must confirm it.` : err.message);
      }
    } finally {
      setBusy(false);
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
    { key: "proposer", label: "Proposed by", sortValue: (d) => d.reviewer_id, render: (d) => d.reviewer_id },
    { key: "outcome", label: "Outcome", sortValue: (d) => OUTCOME_LABELS[d.decision_outcome], render: (d) => <OutcomeChip outcome={d.decision_outcome} /> },
    { key: "notes", label: "Notes", render: (d) => <Box sx={notesSx}>{d.notes || "—"}</Box> },
    {
      key: "proposed",
      label: "Proposed",
      sortValue: (d) => d.decision_timestamp,
      render: (d) => <Box component="span" sx={{ whiteSpace: "nowrap" }}>{formatDateTime(d.decision_timestamp)}</Box>,
    },
    {
      key: "action",
      label: "Actions",
      action: true,
      align: "right",
      render: (d) => (
        <Button variant="outlined" size="small" onClick={() => setSelected(d)} aria-label={`Confirm the decision for ${d.agent_id}`}>
          Confirm
        </Button>
      ),
    },
  ];

  const header = (
    <PageHeader
      title="Confirm queue"
      subtitle="Decisions fraud analysts proposed. Each takes effect only once a compliance officer other than the proposer confirms it."
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
        emptyText="No decisions are waiting for confirmation."
      />

      <Dialog open={Boolean(selected)} onClose={close} aria-labelledby="confirm-title" aria-describedby="confirm-description" fullWidth maxWidth="sm">
        {selected && (
          <>
            <DialogTitle id="confirm-title">Confirm this decision?</DialogTitle>
            <DialogContent>
              {dialogError && <Alert severity="error" role="alert" sx={{ mb: 2 }}>{dialogError}</Alert>}
              <DialogContentText id="confirm-description" sx={{ mb: 2 }}>
                Once confirmed, the decision on agent {selected.agent_id} is final.
              </DialogContentText>
              <Box component="dl" sx={{ m: 0, display: "grid", gridTemplateColumns: "auto 1fr", columnGap: 2, rowGap: 1 }}>
                <Typography component="dt" variant="body2" color="text.secondary">Outcome</Typography>
                <Box component="dd" sx={{ m: 0 }}><OutcomeChip outcome={selected.decision_outcome} /></Box>
                <Typography component="dt" variant="body2" color="text.secondary">Proposed by</Typography>
                <Typography component="dd" variant="body2" sx={{ m: 0 }}>{selected.reviewer_id} on {formatDateTime(selected.decision_timestamp)}</Typography>
                <Typography component="dt" variant="body2" color="text.secondary">Notes</Typography>
                <Typography component="dd" variant="body2" sx={{ m: 0, ...notesSx }}>{selected.notes || "—"}</Typography>
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={close} disabled={busy}>Cancel</Button>
              <Button variant="contained" onClick={confirm} disabled={busy}>Confirm decision</Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </>
  );
}
