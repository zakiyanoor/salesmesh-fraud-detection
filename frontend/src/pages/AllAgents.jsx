import { useEffect, useMemo, useState } from "react";
import {
  Box, Typography, Table, TableHead, TableBody, TableRow, TableCell, TableSortLabel,
  Divider, Chip, CircularProgress, TextField, MenuItem, Paper, InputAdornment,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/SearchOutlined";
import WarningAmberOutlined from "@mui/icons-material/WarningAmberOutlined";
import GroupsOutlined from "@mui/icons-material/GroupsOutlined";
import CheckCircleOutlined from "@mui/icons-material/CheckCircleOutlined";
import Sidebar, { DRAWER_WIDTH } from "../components/Sidebar";
import { api } from "../api";

const MONO = { fontFamily: '"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace' };

function fmt(value, digits) {
  return value == null ? "—" : value.toFixed(digits);
}

function KpiCard({ icon, value, label, color }) {
  return (
    <Paper sx={{ p: 2.5, flex: 1, display: "flex", alignItems: "center", gap: 2 }}>
      <Box sx={{ color: color || "primary.main" }}>{icon}</Box>
      <Box>
        <Typography variant="h4" sx={{ ...MONO, lineHeight: 1 }}>{value}</Typography>
        <Typography variant="caption" color="text.secondary">{label}</Typography>
      </Box>
    </Paper>
  );
}

export default function AllAgents({ username, onLogout }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [regionFilter, setRegionFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [scoreDir, setScoreDir] = useState("desc");

  useEffect(() => {
    api.getAllAgents().then(setData).catch(onLogout).finally(() => setLoading(false));
  }, [onLogout]);

  const agents = useMemo(() => data?.agents || [], [data]);
  const regions = useMemo(() => [...new Set(agents.map((a) => a.region))].sort(), [agents]);

  const filtered = useMemo(() => {
    let result = agents.filter((a) => a.agent_id.toLowerCase().includes(search.toLowerCase()));
    if (regionFilter !== "all") result = result.filter((a) => a.region === regionFilter);
    if (statusFilter !== "all") result = result.filter((a) => a.status === statusFilter);
    const dir = scoreDir === "asc" ? 1 : -1;
    // Agents without a score always sort last, whichever direction is active.
    return [...result].sort((a, b) => {
      if (a.suspicion_score == null && b.suspicion_score == null) return 0;
      if (a.suspicion_score == null) return 1;
      if (b.suspicion_score == null) return -1;
      return dir * (a.suspicion_score - b.suspicion_score);
    });
  }, [agents, search, regionFilter, statusFilter, scoreDir]);

  if (loading) {
    return <Box sx={{ display: "flex", justifyContent: "center", mt: 10 }}><CircularProgress /></Box>;
  }

  const flaggedCount = agents.filter((a) => a.status === "flagged").length;

  return (
    <Box sx={{ display: "flex" }}>
      <Sidebar username={username} onLogout={onLogout} />

      <Box sx={{ flexGrow: 1, p: 5, ml: `${DRAWER_WIDTH}px` }}>
        <Typography variant="h4" gutterBottom>All Agents</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Every registered agent with their latest detection result
        </Typography>

        <Box sx={{ display: "flex", gap: 3, mb: 4 }}>
          <KpiCard icon={<GroupsOutlined fontSize="large" />} value={data?.count ?? 0} label="Total agents" />
          <KpiCard icon={<WarningAmberOutlined fontSize="large" />} value={flaggedCount} label="Flagged" color="error.main" />
          <KpiCard icon={<CheckCircleOutlined fontSize="large" />} value={agents.length - flaggedCount} label="Clear" color="success.main" />
        </Box>

        <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
          <TextField
            size="small"
            placeholder="Search by agent ID"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> }}
            sx={{ width: 240 }}
          />
          <TextField select size="small" label="Region" value={regionFilter} onChange={(e) => setRegionFilter(e.target.value)} sx={{ width: 180 }}>
            <MenuItem value="all">All regions</MenuItem>
            {regions.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
          </TextField>
          <TextField select size="small" label="Status" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} sx={{ width: 160 }}>
            <MenuItem value="all">All statuses</MenuItem>
            <MenuItem value="flagged">Flagged</MenuItem>
            <MenuItem value="clear">Clear</MenuItem>
          </TextField>
        </Box>

        <Divider sx={{ mb: 2 }} />

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
              <TableCell>Submission frequency</TableCell>
              <TableCell>Time-of-day dist.</TableCell>
              <TableCell>Customer similarity</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.map((agent) => (
              <TableRow key={agent.agent_id} hover>
                <TableCell sx={MONO}>{agent.agent_id}</TableCell>
                <TableCell>{agent.region}</TableCell>
                <TableCell sx={MONO}>{fmt(agent.suspicion_score, 3)}</TableCell>
                <TableCell sx={MONO}>{agent.submission_frequency ?? "—"}</TableCell>
                <TableCell sx={MONO}>{fmt(agent.time_of_day_dist, 3)}</TableCell>
                <TableCell sx={MONO}>{fmt(agent.customer_similarity, 3)}</TableCell>
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
              <TableRow><TableCell colSpan={7} align="center" sx={{ py: 4, color: "text.secondary" }}>No agents match your filters.</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </Box>
    </Box>
  );
}
