import { useMemo, useState } from "react";
import {
  Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Divider, Typography,
} from "@mui/material";
import DataTable from "../components/DataTable";
import PageHeader from "../components/PageHeader";
import { DeactivationChip, OutcomeChip } from "../components/chips";
import { LoadStatus } from "../components/states";
import { nextSort } from "../components/tableState";
import { useApi } from "../hooks/useApi";
import { DEACTIVATION_LABELS, OUTCOME_LABELS, formatDateTime } from "../format";
import { mono } from "../theme";
import { api } from "../api";

const PENDING = "pending_deactivation";
const STATUS_ORDER = { pending_deactivation: 0, deactivated: 1, cancelled: 2 };

/** Confirms one deactivation; shows the server's refusal (already deactivated or cancelled) in place. */
function ConfirmDialog({ request, onClose, onDone }) {
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  if (!request) return null;

  const apply = async () => {
    setBusy(true);
    setError(null);
    try {
      onDone(await api.confirmAgentDeactivation(request.deactivation_id));
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <Dialog open onClose={busy ? undefined : onClose} aria-labelledby="deactivation-dialog-title" fullWidth maxWidth="xs">
      <DialogTitle id="deactivation-dialog-title">Deactivate Agent</DialogTitle>
      <DialogContent>
        {error && <Alert severity="error" role="alert" sx={{ mb: 2 }}>{error}</Alert>}
        <DialogContentText>
          {`Agent ${request.agent_id} will be marked deactivated. Nothing will be deleted: the agent, its records and its review decision stay as they are. This is recorded in the audit log.`}
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>Cancel</Button>
        <Button variant="contained" color="error" onClick={apply} disabled={busy}>Deactivate Agent</Button>
      </DialogActions>
    </Dialog>
  );
}

/** Agents a compliance officer confirmed as fraud, waiting for an administrator, through /api/admin/agent-deactivations. */
export default function AgentDeactivations() {
  const result = useApi(api.listAgentDeactivations);
  const [updated, setUpdated] = useState({});
  const [selected, setSelected] = useState(null);
  const [notice, setNotice] = useState(null);
  const [sort, setSort] = useState({ key: "status", dir: "asc" });
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  const requests = useMemo(
    () => (result.data?.deactivations || []).map((r) => updated[r.deactivation_id] || r),
    [result.data, updated],
  );

  const done = (response) => {
    const request = response.deactivation;
    setUpdated((prev) => ({ ...prev, [request.deactivation_id]: { ...prev[request.deactivation_id], ...request } }));
    setSelected(null);
    setNotice(`Agent ${request.agent_id} is deactivated.`);
  };

  const columns = [
    {
      key: "agent",
      label: "Agent",
      title: true,
      sortValue: (r) => r.agent_id,
      render: (r) => <Box component="span" sx={{ ...mono, fontWeight: 500 }}>{r.agent_id}</Box>,
    },
    {
      key: "decision",
      label: "Decision",
      sortValue: (r) => OUTCOME_LABELS[r.effective_outcome] ?? "",
      render: (r) => (r.effective_outcome ? <OutcomeChip outcome={r.effective_outcome} /> : "—"),
    },
    {
      key: "status",
      label: "Status",
      sortValue: (r) => `${STATUS_ORDER[r.status] ?? 9}-${r.requested_at}`,
      render: (r) => <DeactivationChip state={r.status} />,
    },
    {
      key: "action",
      label: "Action",
      action: true,
      align: "right",
      render: (r) => (r.status === PENDING ? (
        <Button size="small" color="error" onClick={() => setSelected(r)} aria-label={`Deactivate Agent ${r.agent_id}`}>
          Deactivate Agent
        </Button>
      ) : (
        <Typography variant="caption" color="text.secondary">
          {r.actioned_at
            ? `${DEACTIVATION_LABELS[r.status]} by ${r.actioned_by}, ${formatDateTime(r.actioned_at)}`
            : DEACTIVATION_LABELS[r.status]}
        </Typography>
      )),
    },
  ];

  const header = (
    <PageHeader
      title="Agent deactivations"
      subtitle="Agents a compliance officer confirmed as fraud. Deactivating marks the agent deactivated here; nothing is deleted."
    />
  );
  if (!result.data) return <>{header}<LoadStatus result={result} /></>;

  return (
    <>
      {header}
      {notice && <Alert severity="success" role="status" onClose={() => setNotice(null)} sx={{ mb: 3 }}>{notice}</Alert>}
      <Divider sx={{ mb: 2 }} />
      <DataTable
        hidePagingWhenOnePage
        label="Agent deactivations"
        columns={columns}
        rows={requests}
        rowKey={(r) => r.deactivation_id}
        sort={sort}
        onSort={(key) => setSort((current) => nextSort(current, key))}
        page={page}
        rowsPerPage={rowsPerPage}
        onPageChange={setPage}
        onRowsPerPageChange={(size) => { setRowsPerPage(size); setPage(0); }}
        emptyText="No agent is waiting to be deactivated."
      />
      <ConfirmDialog key={selected?.deactivation_id ?? "none"} request={selected} onClose={() => setSelected(null)} onDone={done} />
    </>
  );
}
