import { useEffect, useState } from "react";
import { Box, Typography, Table, TableHead, TableBody, TableRow, TableCell, Chip, CircularProgress, Divider } from "@mui/material";
import Sidebar, { DRAWER_WIDTH } from "../components/Sidebar";
import { mono } from "../theme";
import { api } from "../api";

export default function ReviewHistory({ username, onLogout }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getReviewHistory().then(setData).catch(onLogout).finally(() => setLoading(false));
  }, [onLogout]);

  if (loading) {
    return <Box sx={{ display: "flex", justifyContent: "center", mt: 10 }}><CircularProgress /></Box>;
  }

  const decisions = data?.decisions || [];

  return (
    <Box sx={{ display: "flex" }}>
      <Sidebar username={username} onLogout={onLogout} />
      <Box sx={{ flexGrow: 1, p: 5, ml: `${DRAWER_WIDTH}px` }}>
        <Typography variant="h4" gutterBottom>Review History</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Past administrator decisions on flagged agents
        </Typography>
        <Divider sx={{ mb: 2 }} />

        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Agent ID</TableCell>
              <TableCell>Decision</TableCell>
              <TableCell>Reviewer</TableCell>
              <TableCell>Timestamp</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {decisions.map((d) => (
              <TableRow key={d.decision_id} hover>
                <TableCell sx={mono}>{d.agent_id}</TableCell>
                <TableCell>
                  <Chip label={d.decision_outcome} color={d.decision_outcome === "confirmed_fraud" ? "error" : "success"} size="small" variant="outlined" />
                </TableCell>
                <TableCell>{d.reviewer_id}</TableCell>
                <TableCell>{new Date(d.decision_timestamp).toLocaleString()}</TableCell>
              </TableRow>
            ))}
            {decisions.length === 0 && (
              <TableRow><TableCell colSpan={4} align="center" sx={{ py: 4, color: "text.secondary" }}>No decisions recorded yet.</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </Box>
    </Box>
  );
}