import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box, Button, Divider, InputAdornment, MenuItem, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, TextField,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/SearchOutlined";
import PageHeader from "../components/PageHeader";
import RiskBadge from "../components/RiskBadge";
import { LoadStatus } from "../components/states";
import { filterWidth, visuallyHidden } from "../components/filters";
import { useApi } from "../hooks/useApi";
import { mono } from "../theme";
import { api } from "../api";

const SORTERS = {
  score_desc: (a, b) => b.suspicion_score - a.suspicion_score,
  score_asc: (a, b) => a.suspicion_score - b.suspicion_score,
  agent_id: (a, b) => a.agent_id.localeCompare(b.agent_id),
};

export default function FlaggedAgents() {
  const result = useApi(api.getFlaggedAgents);
  const [search, setSearch] = useState("");
  const [regionFilter, setRegionFilter] = useState("all");
  const [sortBy, setSortBy] = useState("score_desc");
  const navigate = useNavigate();

  const agents = useMemo(() => result.data?.flagged_agents || [], [result.data]);
  const regions = useMemo(() => [...new Set(agents.map((a) => a.region))].sort(), [agents]);
  const filtered = useMemo(() => {
    let rows = agents.filter((a) => a.agent_id.toLowerCase().includes(search.toLowerCase()));
    if (regionFilter !== "all") rows = rows.filter((a) => a.region === regionFilter);
    return [...rows].sort(SORTERS[sortBy]);
  }, [agents, search, regionFilter, sortBy]);

  const analysisPeriod = agents[0]?.analysis_period;
  const header = (
    <PageHeader
      title="Flagged agents"
      subtitle={`Agents the model flagged in the most recent detection cycle${analysisPeriod ? ` · Analysis period ${analysisPeriod}` : ""}`}
    />
  );
  if (!result.data) return <>{header}<LoadStatus result={result} /></>;

  return (
    <>
      {header}
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
        <TextField select size="small" label="Sort by" value={sortBy} onChange={(e) => setSortBy(e.target.value)} sx={filterWidth(200)}>
          <MenuItem value="score_desc">Highest score first</MenuItem>
          <MenuItem value="score_asc">Lowest score first</MenuItem>
          <MenuItem value="agent_id">Agent ID</MenuItem>
        </TextField>
      </Box>

      <Divider sx={{ mb: 2 }} />

      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Agent ID</TableCell>
              <TableCell>Region</TableCell>
              <TableCell>Suspicion score</TableCell>
              <TableCell>Risk</TableCell>
              <TableCell align="right"><Box component="span" sx={visuallyHidden}>Actions</Box></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.map((agent) => (
              <TableRow key={agent.agent_id} hover>
                <TableCell sx={mono}>{agent.agent_id}</TableCell>
                <TableCell>{agent.region}</TableCell>
                <TableCell sx={mono}>{agent.suspicion_score?.toFixed(3) ?? "—"}</TableCell>
                <TableCell><RiskBadge band={agent.risk_band} /></TableCell>
                <TableCell align="right">
                  <Button size="small" onClick={() => navigate(`/agents/${agent.agent_id}`)} aria-label={`Review ${agent.agent_id}`}>
                    Review
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  {agents.length === 0 ? "No agents are flagged in the latest run." : "No agents match your filters."}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
}
