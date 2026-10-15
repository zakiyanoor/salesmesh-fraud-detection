import { useCallback, useMemo } from "react";
import { Link as RouterLink } from "react-router-dom";
import { Box, Button, Divider, InputAdornment, Link, MenuItem, TextField } from "@mui/material";
import SearchIcon from "@mui/icons-material/SearchOutlined";
import DataTable from "./DataTable";
import RiskBadge from "./RiskBadge";
import { DecisionStatusChip, FlagSourceChip } from "./chips";
import { filterWidth } from "./filters";
import { nextSort, paging } from "./tableState";
import { useQueryParams } from "../hooks/useQueryParams";
import { FLAG_SOURCE_LABELS, REVIEW_STATUS_LABELS, formatNumber, latestDecisionByAgent } from "../format";
import { RISK_BANDS, mono } from "../theme";

const AGENT_FILTER_DEFAULTS = { q: "", risk: "all", source: "all", review: "all", sort: "score", dir: "desc", page: "0", size: "25" };
const RISK_RANK = { high: 3, review: 2, low: 1 };
const RISK_OPTIONS = { high: "High risk", review: "Review", low: "Low risk" };

function reviewStatusOf(agent, latest) {
  return latest[agent.agent_id]?.status || "none";
}

/**
 * The agent table used by Flagged agents and All agents: filters in the URL, sortable columns,
 * paging and cards on narrow screens. agents come from /api/all-agents, decisions from /api/review-decisions.
 */
export default function AgentList({ label, agents, decisions, sources, emptyText }) {
  const [query, setQuery] = useQueryParams(AGENT_FILTER_DEFAULTS);
  const { page, rowsPerPage } = paging(query);
  const latest = useMemo(() => latestDecisionByAgent(decisions), [decisions]);

  const filtered = useMemo(() => {
    const term = query.q.trim().toLowerCase();
    return agents.filter(
      (a) =>
        (!term || a.agent_id.toLowerCase().includes(term)) &&
        (query.risk === "all" || a.risk_band === query.risk) &&
        (query.source === "all" || a.flag_source === query.source) &&
        (query.review === "all" || reviewStatusOf(a, latest) === query.review),
    );
  }, [agents, latest, query.q, query.risk, query.source, query.review]);

  const setFilter = useCallback((changes) => setQuery({ ...changes, page: 0 }), [setQuery]);
  const filtersActive = ["q", "risk", "source", "review"].some((k) => query[k] !== AGENT_FILTER_DEFAULTS[k]);

  const columns = useMemo(
    () => [
      {
        key: "agent",
        label: "Agent ID",
        title: true,
        sortValue: (a) => a.agent_id,
        render: (a) => (
          <Link component={RouterLink} to={`/agents/${a.agent_id}`} color="primary.dark" sx={mono}>{a.agent_id}</Link>
        ),
      },
      { key: "region", label: "Region", sortValue: (a) => a.region, render: (a) => a.region ?? "—" },
      {
        key: "score",
        label: "Score",
        sortValue: (a) => a.suspicion_score,
        render: (a) => <Box component="span" sx={mono}>{formatNumber(a.suspicion_score, 3)}</Box>,
      },
      { key: "risk", label: "Risk", sortValue: (a) => RISK_RANK[a.risk_band], render: (a) => <RiskBadge band={a.risk_band} /> },
      { key: "source", label: "Flagged by", sortValue: (a) => FLAG_SOURCE_LABELS[a.flag_source], render: (a) => <FlagSourceChip source={a.flag_source} /> },
      {
        key: "review",
        label: "Review",
        sortValue: (a) => REVIEW_STATUS_LABELS[reviewStatusOf(a, latest)],
        render: (a) => <DecisionStatusChip status={reviewStatusOf(a, latest)} />,
      },
    ],
    [latest],
  );

  return (
    <>
      <Box component="form" role="search" aria-label="Filter agents" onSubmit={(e) => e.preventDefault()} sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap", alignItems: "center" }}>
        <TextField
          size="small"
          placeholder="Search by agent ID"
          value={query.q}
          onChange={(e) => setFilter({ q: e.target.value })}
          slotProps={{
            input: { startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> },
            htmlInput: { "aria-label": "Search by agent ID" },
          }}
          sx={filterWidth(220)}
        />
        <TextField select size="small" label="Risk" value={query.risk} onChange={(e) => setFilter({ risk: e.target.value })} sx={filterWidth(150)}>
          <MenuItem value="all">All risk bands</MenuItem>
          {RISK_BANDS.map((band) => <MenuItem key={band} value={band}>{RISK_OPTIONS[band]}</MenuItem>)}
        </TextField>
        <TextField select size="small" label="Flagged by" value={query.source} onChange={(e) => setFilter({ source: e.target.value })} sx={filterWidth(170)}>
          <MenuItem value="all">All sources</MenuItem>
          {sources.map((source) => <MenuItem key={source} value={source}>{FLAG_SOURCE_LABELS[source]}</MenuItem>)}
        </TextField>
        <TextField select size="small" label="Review" value={query.review} onChange={(e) => setFilter({ review: e.target.value })} sx={filterWidth(160)}>
          <MenuItem value="all">All review states</MenuItem>
          {Object.entries(REVIEW_STATUS_LABELS).map(([value, text]) => <MenuItem key={value} value={value}>{text}</MenuItem>)}
        </TextField>
        {filtersActive && (
          <Button onClick={() => setFilter({ q: "", risk: "all", source: "all", review: "all" })}>Clear filters</Button>
        )}
      </Box>

      <Divider sx={{ mb: 2 }} />

      <DataTable
        label={label}
        columns={columns}
        rows={filtered}
        rowKey={(a) => a.agent_id}
        sort={{ key: query.sort, dir: query.dir === "asc" ? "asc" : "desc" }}
        onSort={(key) => {
          const next = nextSort({ key: query.sort, dir: query.dir }, key);
          setQuery({ sort: next.key, dir: next.dir, page: 0 });
        }}
        page={page}
        rowsPerPage={rowsPerPage}
        onPageChange={(next) => setQuery({ page: next })}
        onRowsPerPageChange={(size) => setQuery({ size, page: 0 })}
        emptyText={agents.length === 0 ? emptyText : "No agents match your filters."}
      />
    </>
  );
}
