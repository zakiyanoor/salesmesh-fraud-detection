import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box, Typography, Button, Table, TableHead, TableBody, TableRow, TableCell,
  Divider, Chip, CircularProgress, TextField, MenuItem, Paper, InputAdornment,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/SearchOutlined";
import WarningAmberOutlined from "@mui/icons-material/WarningAmberOutlined";
import GroupsOutlined from "@mui/icons-material/GroupsOutlined";
import ScheduleOutlined from "@mui/icons-material/ScheduleOutlined";
import Sidebar, { DRAWER_WIDTH } from "../components/Sidebar";
import { api } from "../api";

function riskColor(score) {
  if (score >= 0.8) return "error";
  if (score >= 0.5) return "warning";
  return "success";
}

function KpiCard({ icon, value, label, color }) {
  return (
    <Paper sx={{ p: 2.5, flex: 1, display: "flex", alignItems: "center", gap: 2 }}>
      <Box sx={{ color: color || "primary.main" }}>{icon}</Box>
      <Box>
        <Typography variant="h4" sx={{ fontFamily: '"IBM Plex Mono"', lineHeight: 1 }}>
          {value}
        </Typography>
        <Typography variant="caption" color="text.secondary">{label}</Typography>
      </Box>
    </Paper>
  );
}

export default function Dashboard({ username, onLogout }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [regionFilter, setRegionFilter] = useState("all");
  const [sortBy, setSortBy] = useState("score_desc");
  const navigate = useNavigate();

  useEffect(() => {
    api.getFlaggedAgents().then(setData).catch(onLogout).finally(() => setLoading(false));
  }, []);

  const agents = data?.flagged_agents || [];
  const regions = useMemo(() => [...new Set(agents.map((a) => a.region))], [agents]);

  const filtered = useMemo(() => {
    let result = agents.filter((a) => a.agent_id.toLowerCase().includes(search.toLowerCase()));
    if (regionFilter !== "all") result = result.filter((a) => a.region === regionFilter);
    const sorters = {
      score_desc: (a, b) => b.suspicion_score - a.suspicion_score,
      score_asc: (a, b) => a.suspicion_score - b.suspicion_score,
      agent_id: (a, b) => a.agent_id.localeCompare(b.agent_id),
    };
    return [...result].sort(sorters[sortBy]);
  }, [agents, search, regionFilter, sortBy]);

  if (loading) {
    return <Box sx={{ display: "flex", justifyContent: "center", mt: 10 }}><CircularProgress /></Box>;
  }

  const highRisk = agents.filter((a) => a.suspicion_score >= 0.8).length;

  return (
    <Box sx={{ display: "flex" }}>
      <Sidebar username={username} onLogout={onLogout} />

      <Box sx={{ flexGrow: 1, p: 5, ml: `${DRAWER_WIDTH}px` }}>
        <Typography variant="h4" gutterBottom>Flagged Agents</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Agents surfaced by the most recent detection cycle
        </Typography>

        <Box sx={{ display: "flex", gap: 3, mb: 4 }}>
          <KpiCard icon={<GroupsOutlined fontSize="large" />} value={data.count} label="Agents flagged" />
          <KpiCard icon={<WarningAmberOutlined fontSize="large" />} value={highRisk} label="High risk (≥ 0.8)" color="error.main" />
          <KpiCard icon={<ScheduleOutlined fontSize="large" />} value={agents[0]?.analysis_period || "—"} label="Analysis period" />
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
          <TextField select size="small" label="Sort by" value={sortBy} onChange={(e) => setSortBy(e.target.value)} sx={{ width: 200 }}>
            <MenuItem value="score_desc">Highest risk first</MenuItem>
            <MenuItem value="score_asc">Lowest risk first</MenuItem>
            <MenuItem value="agent_id">Agent ID</MenuItem>
          </TextField>
        </Box>

        <Divider sx={{ mb: 2 }} />

        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Agent ID</TableCell>
              <TableCell>Region</TableCell>
              <TableCell>Suspicion score</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right"></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.map((agent) => (
              <TableRow key={agent.agent_id} hover>
                <TableCell sx={{ fontFamily: '"IBM Plex Mono"' }}>{agent.agent_id}</TableCell>
                <TableCell>{agent.region}</TableCell>
                <TableCell sx={{ fontFamily: '"IBM Plex Mono"' }}>{agent.suspicion_score.toFixed(3)}</TableCell>
                <TableCell>
                  <Chip label={agent.flag_status} color={riskColor(agent.suspicion_score)} size="small" variant="outlined" />
                </TableCell>
                <TableCell align="right">
                  <Button size="small" onClick={() => navigate(`/agents/${agent.agent_id}`)}>Review</Button>
                </TableCell>
              </TableRow>
            ))}
            {filtered.length === 0 && (
              <TableRow><TableCell colSpan={5} align="center" sx={{ py: 4, color: "text.secondary" }}>No agents match your filters.</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </Box>
    </Box>
  );
}