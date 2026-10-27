import { useCallback, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Box, Button, Divider, MenuItem, TextField } from "@mui/material";
import AgentId from "../components/AgentId";
import AuditDrawer from "../components/AuditDrawer";
import DataTable from "../components/DataTable";
import PageHeader from "../components/PageHeader";
import { AuditResultChip } from "../components/chips";
import { LoadStatus } from "../components/states";
import { filterWidth } from "../components/filters";
import { paging } from "../components/tableState";
import { useApi } from "../hooks/useApi";
import { useQueryParams } from "../hooks/useQueryParams";
import { AUDIT_ACTIONS, AUDIT_CATEGORIES, categoryHasAgents } from "../audit";
import DayField from "../components/DayField";
import { checkDayRange, fromIsoDay } from "../components/dayDates";
import { formatDateTime } from "../format";
import { mono } from "../theme";
import { api } from "../api";

const DEFAULTS = { category: "", actor: "", agent_id: "", date_from: "", date_to: "", page: "0", size: "25" };
const FILTER_KEYS = ["category", "actor", "agent_id", "date_from", "date_to"];

/**
 * Filters edited locally and applied together, so typing does not send a request per key. Dates are typed as
 * dd/mm/yyyy and kept in the address as YYYY-MM-DD; an invalid date or a From date after the To date is shown
 * under the field and nothing is applied.
 */
function AuditFilters({ values, onApply }) {
  const [draft, setDraft] = useState(() => ({
    ...Object.fromEntries(FILTER_KEYS.map((k) => [k, values[k]])),
    date_from: fromIsoDay(values.date_from),
    date_to: fromIsoDay(values.date_to),
  }));
  const [errors, setErrors] = useState({});
  const set = (key) => (e) => setDraft((d) => ({ ...d, [key]: e.target.value }));
  const setDay = (key) => (value) => setDraft((d) => ({ ...d, [key]: value }));
  const active = FILTER_KEYS.some((k) => values[k]);
  return (
    <Box
      component="form"
      role="search"
      aria-label="Filter audit events"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        const range = checkDayRange(draft.date_from, draft.date_to);
        setErrors(range);
        if (range.fromError || range.toError) return;
        onApply({ category: draft.category, actor: draft.actor.trim(), agent_id: draft.agent_id.trim(), date_from: range.from, date_to: range.to });
      }}
      sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap", alignItems: "flex-start" }}
    >
      <TextField
        select
        size="small"
        label="Category"
        slotProps={{ select: { displayEmpty: true }, inputLabel: { shrink: true } }}
        value={draft.category}
        onChange={(e) => {
          setDraft((d) => ({ ...d, category: e.target.value }));
          onApply({ category: e.target.value });
        }}
        sx={filterWidth(170)}
      >
        <MenuItem value="">All categories</MenuItem>
        {Object.entries(AUDIT_CATEGORIES).map(([value, text]) => <MenuItem key={value} value={value}>{text}</MenuItem>)}
      </TextField>
      <TextField size="small" label="Actor" placeholder="Username or account ID" value={draft.actor} onChange={set("actor")} slotProps={{ inputLabel: { shrink: true } }} sx={filterWidth(200)} />
      <TextField size="small" label="Agent ID" value={draft.agent_id} onChange={set("agent_id")} sx={filterWidth(140)} />
      <DayField label="From date" value={draft.date_from} onChange={setDay("date_from")} error={errors.fromError} />
      <DayField label="To date" value={draft.date_to} onChange={setDay("date_to")} error={errors.toError} />
      <Button type="submit" variant="outlined">Apply filters</Button>
      {active && <Button onClick={() => onApply(Object.fromEntries(FILTER_KEYS.map((k) => [k, ""])))}>Clear filters</Button>}
    </Box>
  );
}

/** The audit trail, newest first, admin only. Filters and paging run on the server and live in the URL. */
export default function AuditLog() {
  const [query, setQuery] = useQueryParams(DEFAULTS);
  const [searchParams] = useSearchParams();
  const { page, rowsPerPage } = paging(query);
  const [selected, setSelected] = useState(null);
  const { category, actor, agent_id: agentId, date_from: dateFrom, date_to: dateTo } = query;

  const load = useCallback(
    () => api.getAuditLog({ category, actor, agent_id: agentId, date_from: dateFrom, date_to: dateTo, limit: rowsPerPage, offset: page * rowsPerPage }),
    [category, actor, agentId, dateFrom, dateTo, rowsPerPage, page],
  );
  const result = useApi(load);

  const columns = [
    {
      key: "time",
      label: "Time",
      title: true,
      render: (e) => <Box component="span" sx={{ whiteSpace: "nowrap" }}>{formatDateTime(e.timestamp)}</Box>,
    },
    { key: "actor", label: "Actor", render: (e) => <Box component="span" sx={mono}>{e.actor}</Box> },
    { key: "category", label: "Category", render: (e) => AUDIT_CATEGORIES[e.category] || e.category },
    { key: "action", label: "Action", render: (e) => AUDIT_ACTIONS[e.action] || e.action },
    // Agents appear only in Review and Detection entries, so the column is left out for other categories.
    ...(categoryHasAgents(category) ? [{ key: "agent", label: "Agent", render: (e) => <AgentId id={e.target_agent_id} /> }] : []),
    { key: "result", label: "Result", render: (e) => <AuditResultChip entry={e} /> },
    {
      key: "details",
      label: "Details",
      action: true,
      align: "right",
      render: (e) => (
        <Button
          size="small"
          aria-haspopup="dialog"
          aria-label={`Details of ${AUDIT_ACTIONS[e.action] || e.action} at ${formatDateTime(e.timestamp)}`}
          onClick={(event) => {
            event.stopPropagation();
            setSelected(e);
          }}
        >
          Details
        </Button>
      ),
    },
  ];

  return (
    <>
      <PageHeader title="Audit log" subtitle="A permanent record of who did what, and when. Entries cannot be changed or deleted." />
      {/* Remounting on a new query string keeps the form in step with Back and Forward. */}
      <AuditFilters key={searchParams.toString()} values={query} onApply={(filters) => setQuery({ ...filters, page: 0 })} />
      <Divider sx={{ mb: 2 }} />
      {result.data ? (
        <DataTable
          label="Audit events"
          columns={columns}
          rows={result.data.entries}
          rowKey={(e) => e.log_id}
          totalCount={result.data.total}
          page={page}
          rowsPerPage={rowsPerPage}
          onPageChange={(next) => setQuery({ page: next })}
          onRowsPerPageChange={(size) => setQuery({ size, page: 0 })}
          onRowClick={(e) => setSelected(e)}
          emptyText={FILTER_KEYS.some((k) => query[k]) ? "No audit events match your filters." : "No audit events yet."}
        />
      ) : (
        <LoadStatus result={result} />
      )}
      <AuditDrawer entry={selected} onClose={() => setSelected(null)} />
    </>
  );
}
