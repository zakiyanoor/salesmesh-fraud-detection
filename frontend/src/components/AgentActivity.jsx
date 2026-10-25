import { useCallback } from "react";
import { Box, Chip, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import ContentCopyOutlined from "@mui/icons-material/ContentCopyOutlined";
import SectionCard from "./SectionCard";
import { SimpleBarChart } from "./charts";
import { hourTable } from "../chartTables";
import { useApi } from "../hooks/useApi";
import { mono } from "../theme";
import { api } from "../api";

export const RECORDED_NOTE = "Days and hours are as recorded in the data.";

/**
 * An agent's activity (issue #28): one row per day of the data window, and activations by hour of day.
 * A day can hold duplicate evidence; the flag itself belongs to the agent for the whole run, so no day is
 * called flagged.
 */
export default function AgentActivity({ agentId }) {
  const load = useCallback(() => api.getAgentActivity(agentId), [agentId]);
  const result = useApi(load);

  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 3, mt: 3, alignItems: "start" }}>
      <SectionCard
        title="Daily activity"
        subtitle={`${RECORDED_NOTE} The flag applies to the agent for the whole detection run, not to single days.`}
        result={result}
      >
        {(data) => (
          <TableContainer sx={{ maxHeight: 420 }}>
            <Table size="small" stickyHeader aria-label="Activations per day">
              <TableHead>
                <TableRow>
                  <TableCell>Day</TableCell>
                  <TableCell align="right">Activations</TableCell>
                  <TableCell align="right">Completed</TableCell>
                  <TableCell>Duplicate evidence</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.days.map((d) => (
                  <TableRow key={d.date}>
                    <TableCell sx={{ ...mono, whiteSpace: "nowrap" }}>{d.date}</TableCell>
                    <TableCell align="right" sx={mono}>{d.activations}</TableCell>
                    <TableCell align="right" sx={mono}>{d.completed}</TableCell>
                    <TableCell>
                      {d.duplicate_evidence && (
                        <Chip size="small" variant="outlined" icon={<ContentCopyOutlined fontSize="small" />} label="Duplicate evidence on this day" />
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </SectionCard>
      <SectionCard
        title="Activations by hour of day"
        subtitle={`${RECORDED_NOTE} Hours 0 to 23.`}
        result={result}
        table={hourTable}
      >
        {(data) => (
          <>
            <SimpleBarChart data={data.hours.map((h) => ({ name: String(h.hour), value: h.activations }))} name="Activations" />
            <Typography variant="caption" color="text.secondary">
              {`${data.totals.activations} activations, ${data.totals.completed} completed.`}
            </Typography>
          </>
        )}
      </SectionCard>
    </Box>
  );
}
