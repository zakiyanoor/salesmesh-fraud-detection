import { useMemo, useState } from "react";
import {
  Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Divider, MenuItem,
  TextField, Typography,
} from "@mui/material";
import CheckCircleOutlined from "@mui/icons-material/CheckCircleOutlined";
import BlockOutlined from "@mui/icons-material/BlockOutlined";
import WarningAmberOutlined from "@mui/icons-material/WarningAmberOutlined";
import DataTable from "../components/DataTable";
import PageHeader from "../components/PageHeader";
import { LoadStatus } from "../components/states";
import { nextSort } from "../components/tableState";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../auth/authContext";
import { ROLE_LABELS } from "../auth/roles";
import { mono } from "../theme";
import { api } from "../api";

const chip = { size: "small", variant: "outlined" };

function RoleChip({ role }) {
  if (ROLE_LABELS[role]) return <Chip {...chip} label={ROLE_LABELS[role]} />;
  return <Chip {...chip} color="warning" icon={<WarningAmberOutlined fontSize="small" />} label={`${role} (not a valid role)`} />;
}

function ActiveChip({ active }) {
  return active
    ? <Chip {...chip} color="success" icon={<CheckCircleOutlined fontSize="small" />} label="Active" />
    : <Chip {...chip} icon={<BlockOutlined fontSize="small" />} label="Deactivated" />;
}

/** Confirms one account change; shows the server's refusal (own account, last admin) in place. */
function ChangeDialog({ change, onClose, onDone }) {
  const [role, setRole] = useState(change?.account.role in ROLE_LABELS ? change.account.role : "fraud_analyst");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  if (!change) return null;
  const { account, kind } = change;

  const titles = { role: "Change role", deactivate: "Deactivate account", reactivate: "Reactivate account" };
  const apply = async () => {
    setBusy(true);
    setError(null);
    try {
      const response =
        kind === "role" ? await api.changeAccountRole(account.admin_id, role)
          : kind === "deactivate" ? await api.deactivateAccount(account.admin_id)
            : await api.reactivateAccount(account.admin_id);
      onDone(response, kind);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <Dialog open onClose={busy ? undefined : onClose} aria-labelledby="account-dialog-title" fullWidth maxWidth="xs">
      <DialogTitle id="account-dialog-title">{titles[kind]}</DialogTitle>
      <DialogContent>
        {error && <Alert severity="error" role="alert" sx={{ mb: 2 }}>{error}</Alert>}
        <DialogContentText sx={{ mb: kind === "role" ? 2 : 0 }}>
          {kind === "role" && `Choose the new role for ${account.username}. It applies on their next request.`}
          {kind === "deactivate" && `${account.username} will be signed out on their next request and cannot sign in until reactivated.`}
          {kind === "reactivate" && `${account.username} will be able to sign in again with their existing password.`}
        </DialogContentText>
        {kind === "role" && (
          <TextField select fullWidth size="small" label="Role" value={role} onChange={(e) => setRole(e.target.value)}>
            {Object.entries(ROLE_LABELS).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
          </TextField>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>Cancel</Button>
        <Button variant="contained" color={kind === "deactivate" ? "error" : "primary"} onClick={apply} disabled={busy}>
          {titles[kind]}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

/** Admin accounts: list, change role, deactivate or reactivate, through /api/admin/accounts. */
export default function Accounts() {
  const result = useApi(api.listAccounts);
  const { user } = useAuth();
  const [updated, setUpdated] = useState({});
  const [change, setChange] = useState(null);
  const [notice, setNotice] = useState(null);
  const [sort, setSort] = useState({ key: "username", dir: "asc" });
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  const accounts = useMemo(
    () => (result.data?.accounts || []).map((a) => updated[a.admin_id] || a),
    [result.data, updated],
  );

  const done = (response, kind) => {
    const account = response.account;
    setUpdated((prev) => ({ ...prev, [account.admin_id]: account }));
    setChange(null);
    const what = { role: `now ${ROLE_LABELS[account.role] || account.role}`, deactivate: "deactivated", reactivate: "reactivated" }[kind];
    setNotice(response.changed === false ? `No change: ${account.username} was already ${what.replace("now ", "")}.` : `${account.username} is ${what}.`);
  };

  const columns = [
    {
      key: "username",
      label: "Username",
      title: true,
      sortValue: (a) => a.username,
      render: (a) => (
        <Box component="span" sx={{ fontWeight: 500 }}>
          {a.username}
          {a.username === user?.username && <Typography component="span" variant="caption" color="text.secondary"> (you)</Typography>}
        </Box>
      ),
    },
    { key: "id", label: "Account ID", sortValue: (a) => a.admin_id, render: (a) => <Box component="span" sx={mono}>{a.admin_id}</Box> },
    { key: "role", label: "Role", sortValue: (a) => ROLE_LABELS[a.role] || a.role, render: (a) => <RoleChip role={a.role} /> },
    { key: "status", label: "Status", sortValue: (a) => (a.is_active ? 0 : 1), render: (a) => <ActiveChip active={a.is_active} /> },
    {
      key: "actions",
      label: "Actions",
      action: true,
      align: "right",
      render: (a) => (a.username === user?.username ? (
        <Typography variant="caption" color="text.secondary">You cannot change your own account</Typography>
      ) : (
        <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end", flexWrap: "wrap" }}>
          <Button size="small" onClick={() => setChange({ account: a, kind: "role" })} aria-label={`Change role of ${a.username}`}>
            Change role
          </Button>
          <Button
            size="small"
            color={a.is_active ? "error" : "primary"}
            onClick={() => setChange({ account: a, kind: a.is_active ? "deactivate" : "reactivate" })}
            aria-label={`${a.is_active ? "Deactivate" : "Reactivate"} ${a.username}`}
          >
            {a.is_active ? "Deactivate" : "Reactivate"}
          </Button>
        </Box>
      )),
    },
  ];

  const header = (
    <PageHeader
      title="Accounts"
      subtitle="Who can sign in, and with which role. Password hashes are never shown."
    />
  );
  if (!result.data) return <>{header}<LoadStatus result={result} /></>;

  return (
    <>
      {header}
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        New accounts and password resets are not available here: there is no API for them, so they are done on the server (password resets with <Box component="code" sx={mono}>python -m src.manage_accounts reset-password</Box>).
      </Typography>
      {notice && <Alert severity="success" role="status" onClose={() => setNotice(null)} sx={{ mb: 3 }}>{notice}</Alert>}
      <Divider sx={{ mb: 2 }} />
      <DataTable
        label="Accounts"
        columns={columns}
        rows={accounts}
        rowKey={(a) => a.admin_id}
        sort={sort}
        onSort={(key) => setSort((current) => nextSort(current, key))}
        page={page}
        rowsPerPage={rowsPerPage}
        onPageChange={setPage}
        onRowsPerPageChange={(size) => { setRowsPerPage(size); setPage(0); }}
        emptyText="No accounts exist yet."
      />
      <ChangeDialog key={change ? `${change.account.admin_id}-${change.kind}` : "none"} change={change} onClose={() => setChange(null)} onDone={done} />
    </>
  );
}
