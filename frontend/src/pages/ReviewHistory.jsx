import { Typography, Table, TableHead, TableBody, TableRow, TableCell, TableContainer, Chip, Divider } from "@mui/material";
import PageHeader from "../components/PageHeader";
import { LoadStatus } from "../components/states";
import { useApi } from "../hooks/useApi";
import { mono } from "../theme";
import { api } from "../api";

export default function ReviewHistory() {
  const result = useApi(api.getReviewDecisions);
  const header = <PageHeader title="Review history" subtitle="Decisions proposed and confirmed on flagged agents" />;
  if (!result.data) return <>{header}<LoadStatus result={result} /></>;

  const decisions = result.data.decisions || [];

  return (
    <>
      {header}
      <Divider sx={{ mb: 2 }} />
      <TableContainer>
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
                <TableCell>
                  <Typography variant="body2" component="span" sx={{ whiteSpace: "nowrap" }}>
                    {new Date(d.decision_timestamp).toLocaleString()}
                  </Typography>
                </TableCell>
              </TableRow>
            ))}
            {decisions.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} align="center" sx={{ py: 4, color: "text.secondary" }}>No decisions recorded yet.</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
}
