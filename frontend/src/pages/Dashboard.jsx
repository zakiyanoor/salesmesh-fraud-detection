import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Drawer,
  Typography,
  Button,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Divider,
  Chip,
  CircularProgress,
} from "@mui/material";
import { api } from "../api";

const DRAWER_WIDTH = 220;

function riskColor(score) {
  if (score >= 0.8) return "error";
  if (score >= 0.5) return "warning";
  return "success";
}

function Sidebar({ username, onLogout }) {
  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: DRAWER_WIDTH,
          bgcolor: "background.paper",
          borderRight: "1px solid",
          borderColor: "divider",
          p: 3,
        },
      }}
    >
      <Typography variant="h6" sx={{ mb: 0.5 }}>
        SalesMesh
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 4 }}>
        Fraud Detection
      </Typography>

      <Typography variant="body2" sx={{ mb: 1 }}>
        Dashboard
      </Typography>

      <Box sx={{ mt: "auto", position: "absolute", bottom: 24, left: 24, right: 24 }}>
        <Divider sx={{ mb: 2 }} />
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
          Signed in as {username}
        </Typography>
        <Button size="small" onClick={onLogout} sx={{ px: 0 }}>
          Sign out
        </Button>
      </Box>
    </Drawer>
  );
}

export default function Dashboard({ username, onLogout }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api
      .getFlaggedAgents()
      .then(setData)
      .catch(() => onLogout())
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", mt: 10 }}>
        <CircularProgress />
      </Box>
    );
  }

  const agents = data?.flagged_agents || [];
  const highRisk = agents.filter((a) => a.suspicion_score >= 0.8).length;

  return (
    <Box sx={{ display: "flex" }}>
      <Sidebar username={username} onLogout={onLogout} />

      <Box sx={{ flexGrow: 1, p: 5, ml: `${DRAWER_WIDTH}px` }}>
        <Typography variant="h4" gutterBottom>
          Flagged Agents
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Agents surfaced by the most recent detection cycle
        </Typography>

        <Box sx={{ display: "flex", gap: 6, mb: 4 }}>
          <Box>
            <Typography variant="h3" sx={{ fontFamily: '"IBM Plex Mono"' }}>
              {data.count}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Agents flagged
            </Typography>
          </Box>
          <Box>
            <Typography variant="h3" sx={{ fontFamily: '"IBM Plex Mono"', color: "error.main" }}>
              {highRisk}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              High risk (score ≥ 0.8)
            </Typography>
          </Box>
          <Box>
            <Typography variant="h3" sx={{ fontFamily: '"IBM Plex Mono"' }}>
              {agents[0]?.analysis_period || "—"}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Analysis period
            </Typography>
          </Box>
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
            {agents.map((agent) => (
              <TableRow key={agent.agent_id} hover>
                <TableCell sx={{ fontFamily: '"IBM Plex Mono"' }}>{agent.agent_id}</TableCell>
                <TableCell>{agent.region}</TableCell>
                <TableCell sx={{ fontFamily: '"IBM Plex Mono"' }}>
                  {agent.suspicion_score.toFixed(3)}
                </TableCell>
                <TableCell>
                  <Chip
                    label={agent.flag_status}
                    color={riskColor(agent.suspicion_score)}
                    size="small"
                    variant="outlined"
                  />
                </TableCell>
                <TableCell align="right">
                  <Button size="small" onClick={() => navigate(`/agents/${agent.agent_id}`)}>
                    Review
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Box>
  );
}