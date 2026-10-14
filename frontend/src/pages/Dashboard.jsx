import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box, Typography, Button, Table, TableHead, TableBody, TableRow, TableCell,
  Divider, CircularProgress, TextField, MenuItem, Paper, InputAdornment,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { PieChart, Pie, Tooltip } from "recharts";
import SearchIcon from "@mui/icons-material/SearchOutlined";
import Sidebar, { DRAWER_WIDTH } from "../components/Sidebar";
import RiskBadge from "../components/RiskBadge";
import { mono } from "../theme";
import { api } from "../api";

const CHART_SIZE = 140;

function DonutCard({ title, subtitle, slices }) {
  const theme = useTheme();
  const total = slices.reduce((sum, s) => sum + s.value, 0);
  const visible = slices.filter((s) => s.value > 0);
  // With nothing to plot, draw a single muted ring so the card keeps its shape.
  const pieData = total > 0 ? visible : [{ name: "No data", value: 1, fill: theme.palette.divider }];

  return (
    <Paper sx={{ p: 3, flex: "1 1 320px", minWidth: 0 }}>
      <Typography variant="overline" color="text.secondary">{title}</Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>{subtitle}</Typography>

      <Box sx={{ display: "flex", alignItems: "center", gap: 3, mt: 2 }}>
        <Box sx={{ position: "relative", width: CHART_SIZE, height: CHART_SIZE, flexShrink: 0 }}>
          <PieChart width={CHART_SIZE} height={CHART_SIZE}>
            <Pie
              data={pieData}
              dataKey="value"
              nameKey="name"
              innerRadius={44}
              outerRadius={64}
              paddingAngle={visible.length > 1 ? 2 : 0}
              stroke="none"
            />
            {total > 0 && (
              <Tooltip
                contentStyle={{
                  background: theme.palette.background.paper,
                  border: `1px solid ${theme.palette.divider}`,
                  color: theme.palette.text.primary,
                }}
              />
            )}
          </PieChart>
          <Box sx={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", pointerEvents: "none" }}>
            <Typography variant="h5" sx={mono}>{total}</Typography>
          </Box>
        </Box>

        <Box sx={{ flex: 1, minWidth: 0 }}>
          {slices.map((s) => (
            <Box key={s.name} sx={{ display: "flex", alignItems: "center", gap: 1, py: 0.5 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: s.fill, flexShrink: 0 }} />
              <Typography variant="body2" noWrap title={s.name} sx={{ flex: 1, minWidth: 0 }}>{s.name}</Typography>
              <Typography variant="body2" sx={mono}>{s.value}</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ ...mono, width: 40, textAlign: "right" }}>
                {total > 0 ? `${Math.round((s.value / total) * 100)}%` : "—"}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>
    </Paper>
  );
}

export default function Dashboard({ username, onLogout }) {
  const [data, setData] = useState(null);
  const [allAgents, setAllAgents] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [regionFilter, setRegionFilter] = useState("all");
  const [sortBy, setSortBy] = useState("score_desc");
  const navigate = useNavigate();
  const theme = useTheme();

  useEffect(() => {
    Promise.all([api.getFlaggedAgents(), api.getAllAgents()])
      .then(([flagged, everyone]) => {
        setData(flagged);
        setAllAgents(everyone);
      })
      .catch(onLogout)
      .finally(() => setLoading(false));
  }, [onLogout]);

  const agents = useMemo(() => data?.flagged_agents || [], [data]);
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

  // The donuts count agents, so they read /all-agents (one row per agent, latest
  // period). /analytics and /flagged-agents aggregate per feature vector, which
  // double-counts any agent analysed in more than one period.
  const roster = allAgents?.agents || [];
  const flaggedTotal = roster.filter((a) => a.status === "flagged").length;

  const regionCounts = {};
  roster.forEach((a) => {
    const region = a.region ?? "Unknown";
    regionCounts[region] = (regionCounts[region] || 0) + 1;
  });
  const regionEntries = Object.entries(regionCounts).sort((a, b) => b[1] - a[1]);

  const statusSlices = [
    { name: "Flagged", value: flaggedTotal, fill: theme.palette.error.main },
    { name: "Clear", value: roster.length - flaggedTotal, fill: theme.palette.success.main },
  ];
  const regionSlices = regionEntries.slice(0, 5).map(([region, count], i) => ({
    name: region,
    value: count,
    fill: theme.palette.chart.region[i],
  }));
  const riskSlices = [
    { name: "High risk", band: "high" },
    { name: "Review", band: "review" },
    { name: "Low risk", band: "low" },
  ].map(({ name, band }) => ({
    name,
    value: roster.filter((a) => a.risk_band === band).length,
    fill: theme.palette.risk[band],
  }));

  const analysisPeriod = agents[0]?.analysis_period;

  return (
    <Box sx={{ display: "flex" }}>
      <Sidebar username={username} onLogout={onLogout} />

      <Box sx={{ flexGrow: 1, p: 5, ml: `${DRAWER_WIDTH}px` }}>
        <Typography variant="h4" gutterBottom>Flagged Agents</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Agents surfaced by the most recent detection cycle{analysisPeriod ? ` · Analysis period ${analysisPeriod}` : ""}
        </Typography>

        <Box sx={{ display: "flex", gap: 3, mb: 4, flexWrap: "wrap" }}>
          <DonutCard title="Agents by Status" subtitle="All registered agents" slices={statusSlices} />
          <DonutCard
            title="Top 5 Regions"
            subtitle={regionEntries.length > 5 ? `By agent count, 5 of ${regionEntries.length} regions` : "By agent count"}
            slices={regionSlices}
          />
          <DonutCard
            title="Risk Level Breakdown"
            subtitle="High: model flagged · Review: rule only or score 1.3 and above · Low: the rest"
            slices={riskSlices}
          />
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
              <TableCell>Risk</TableCell>
              <TableCell align="right"></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.map((agent) => (
              <TableRow key={agent.agent_id} hover>
                <TableCell sx={mono}>{agent.agent_id}</TableCell>
                <TableCell>{agent.region}</TableCell>
                <TableCell sx={mono}>{agent.suspicion_score.toFixed(3)}</TableCell>
                <TableCell>
                  <RiskBadge band={agent.risk_band} />
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