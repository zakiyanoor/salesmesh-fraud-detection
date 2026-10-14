import { useMemo, useState } from "react";
import {
  Box, Typography, Table, TableHead, TableBody, TableRow, TableCell, TableContainer, TableSortLabel,
  Divider, Chip, TextField, MenuItem, Paper, InputAdornment,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/SearchOutlined";
import WarningAmberOutlined from "@mui/icons-material/WarningAmberOutlined";
import GroupsOutlined from "@mui/icons-material/GroupsOutlined";
import CheckCircleOutlined from "@mui/icons-material/CheckCircleOutlined";
import PageHeader from "../components/PageHeader";
import RiskBadge from "../components/RiskBadge";
import { LoadStatus } from "../components/states";
import { filterWidth } from "../components/filters";
import { useApi } from "../hooks/useApi";
import { mono } from "../theme";
import { api } from "../api";

function fmt(value, digits) {
  return value == null ? "—" : value.toFixed(digits);
}

function KpiCard({ icon, value, label, color }) {
  return (
    <Paper sx={{ p: 2.5, flex: "1 1 180px", display: "flex", alignItems: "center", gap: 2 }}>
      <Box sx={{ color: color || "primary.main" }}>{icon}</Box>
      <Box>
        <Typography variant="h4" component="p" sx={{ ...mono, lineHeight: 1 }}>{value}</Typography>
        <Typography variant="caption" color="text.secondary">{label}</Typography>
      </Box>
    </Paper>
  );
}

export default function AllAgents() {
  const result = useApi(api.getAllAgents);
  const [search, setSearch] = useState("");
  const [regionFilter, setRegionFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [scoreDir, setScoreDir] = useState("desc");

  const agents = useMemo(() => result.data?.agents || [], [result.data]);
  const regions = useMemo(() => [...new Set(agents.map((a) => a.region))].sort(), [agents]);

  const filtered = useMemo(() => {
    let rows = agents.filter((a) => a.agent_id.toLowerCase().includes(search.toLowerCase()));
    if (regionFilter !== "all") rows = rows.filter((a) => a.region === regionFilter);
    if (statusFilter !== "all") rows = rows.filter((a) => a.status === statusFilter);
    const dir = scoreDir === "asc" ? 1 : -1;
    // Agents without a score always sort last, whichever direction is active.
    return [...rows].sort((a, b) => {
      if (a.suspicion_score == null && b.suspicion_score == null) return 0;
      if (a.suspicion_score == null) return 1;
      if (b.suspicion_score == null) return -1;
      return dir * (a.suspicion_score - b.suspicion_score);
    });
  }, [agents, search, regionFilter, statusFilter, scoreDir]);

  const header = <PageHeader title="All agents" subtitle="Every registered agent with their latest detection result" />;
  if (!result.data) return <>{header}<LoadStatus result={result} /></>;

  const flaggedCount = agents.filter((a) => a.status === "flagged").length;

  return (
    <>
      {header}
      <Box sx={{ display: "flex", gap: 3, mb: 4, flexWrap: "wrap" }}>
        <KpiCard icon={<GroupsOutlined fontSize="large" />} value={result.data.count ?? agents.length} label="Total agents" />
        <KpiCard icon={<WarningAmberOutlined fontSize="large" />} value={flaggedCount} label="Flagged" color="error.main" />
        <KpiCard icon={<CheckCircleOutlined fontSize="large" />} value={agents.length - flaggedCount} label="Clear" color="success.main" />
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
        <TextField
          size="small"
          placeholder="Search by agent ID"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          slotProps={{
            input: { startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> },
            htmlInput: { "aria-label": "Search by agent ID" },
          }}
          sx={filterWidth(240)}
        />
        <TextField select size="small" label="Region" value={regionFilter} onChange={(e) => setRegionFilter(e.target.value)} sx={filterWidth(180)}>
          <MenuItem value="all">All regions</MenuItem>
          {regions.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
        </TextField>
        <TextField select size="small" label="Status" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} sx={filterWidth(160)}>
          <MenuItem value="all">All statuses</MenuItem>
          <MenuItem value="flagged">Flagged</MenuItem>
          <MenuItem value="clear">Clear</MenuItem>
        </TextField>
      </Box>

      <Divider sx={{ mb: 2 }} />

      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Agent ID</TableCell>
              <TableCell>Region</TableCell>
              <TableCell sortDirection={scoreDir}>
                <TableSortLabel active direction={scoreDir} onClick={() => setScoreDir(scoreDir === "desc" ? "asc" : "desc")}>
                  Suspicion score
                </TableSortLabel>
              </TableCell>
              <TableCell>Risk</TableCell>
              <TableCell>Submission frequency</TableCell>
              <TableCell>Time-of-day dist.</TableCell>
              <TableCell>Customer similarity</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.map((agent) => (
              <TableRow key={agent.agent_id} hover>
                <TableCell sx={mono}>{agent.agent_id}</TableCell>
                <TableCell>{agent.region}</TableCell>
                <TableCell sx={mono}>{fmt(agent.suspicion_score, 3)}</TableCell>
                <TableCell><RiskBadge band={agent.risk_band} /></TableCell>
                <TableCell sx={mono}>{agent.submission_frequency ?? "—"}</TableCell>
                <TableCell sx={mono}>{fmt(agent.time_of_day_dist, 3)}</TableCell>
                <TableCell sx={mono}>{fmt(agent.customer_similarity, 3)}</TableCell>
                <TableCell>
                  <Chip
                    label={agent.status}
                    color={agent.status === "flagged" ? "error" : "success"}
                    size="small"
                    variant="outlined"
                  />
                </TableCell>
              </TableRow>
            ))}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  {agents.length === 0 ? "No agents are loaded yet." : "No agents match your filters."}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
}
