import { useCallback } from "react";
import { Box, Chip, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import ContentCopyOutlined from "@mui/icons-material/ContentCopyOutlined";
import SectionCard from "./SectionCard";
import { hourRange, hourTable } from "../chartTables";
import { useApi } from "../hooks/useApi";
import { mono } from "../theme";
import { api } from "../api";

export const RECORDED_NOTE = "Days and hours are as recorded in the data.";
const ACTIVATION_NOTE = "An activation is one customer signed up by the agent. Completed means the activation reached its completed status.";
const TABLE_HEIGHT = 360;
const clock = (hour) => `${String(hour).padStart(2, "0")}:00`;
const head = { fontSize: 13, fontWeight: 500, color: "text.secondary", whiteSpace: "nowrap", py: 1, px: 1 };

function DailyTable({ days }) {
  // The duplicate evidence column only when at least one day holds evidence.
  const withEvidence = days.some((d) => d.duplicate_evidence);
  return (
    <>
      <TableContainer sx={{ maxHeight: TABLE_HEIGHT }}>
        <Table size="small" stickyHeader aria-label="Activations per day" sx={{ "& td": { borderColor: "divider", fontVariantNumeric: "tabular-nums", px: 1, py: 0.75, fontSize: 13 }, "& th:first-of-type, & td:first-of-type": { pl: 1.5 } }}>
          <TableHead>
            <TableRow>
              <TableCell sx={head}>Day</TableCell>
              <TableCell align="right" sx={head}>Activations</TableCell>
              <TableCell align="right" sx={head}>Completed</TableCell>
              {withEvidence && <TableCell sx={head}>Duplicate evidence</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {days.map((d) => (
              <TableRow key={d.date} hover>
                <TableCell sx={{ ...mono, whiteSpace: "nowrap" }}>{d.date}</TableCell>
                <TableCell align="right" sx={mono}>{d.activations}</TableCell>
                <TableCell align="right" sx={mono}>{d.completed}</TableCell>
                {withEvidence && (
                  <TableCell>
                    {d.duplicate_evidence && (
                      <Chip
                        size="small"
                        variant="outlined"
                        icon={<ContentCopyOutlined fontSize="small" />}
                        label="Duplicate evidence on this day"
                        // In the half width card the label wraps instead of being cut off.
                        sx={{ height: "auto", py: 0.25, maxWidth: 150, fontSize: 12, "& .MuiChip-label": { whiteSpace: "normal", lineHeight: 1.3 } }}
                      />
                    )}
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      {!withEvidence && (
        <Typography sx={{ fontSize: 13, color: "text.secondary", mt: 1.5 }}>No duplicate evidence in this period.</Typography>
      )}
    </>
  );
}

/** The bar tooltip: "08:00 to 08:59: 3 activations". */
export function HourTooltip({ active, payload }) {
  const theme = useTheme();
  if (!active || !payload?.length) return null;
  const { hour, activations } = payload[0].payload;
  return (
    <Box sx={{ bgcolor: "background.paper", border: `1px solid ${theme.palette.divider}`, borderRadius: "6px", px: 1.25, py: 0.75, fontSize: 13 }}>
      {`${hourRange(hour)}: ${activations} ${activations === 1 ? "activation" : "activations"}`}
    </Box>
  );
}

/** One bar per hour of the 24 hour clock, labelled every six hours. */
function HourChart({ hours }) {
  const theme = useTheme();
  const axis = { fill: theme.palette.text.secondary, fontSize: 12 };
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={hours} margin={{ top: 8, right: 8, bottom: 24, left: 0 }}>
        <CartesianGrid vertical={false} stroke={theme.palette.divider} />
        <XAxis
          dataKey="hour"
          interval={0}
          tickLine={false}
          axisLine={{ stroke: theme.palette.divider }}
          tick={axis}
          tickFormatter={(h) => (h % 6 === 0 ? clock(h) : "")}
          label={{ value: "Hour of day, 24 hour clock", position: "insideBottom", offset: -16, fill: theme.palette.text.secondary, fontSize: 12 }}
        />
        <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={axis} width={36} />
        <Tooltip cursor={{ fill: theme.palette.action.selected }} content={<HourTooltip />} />
        <Bar dataKey="activations" name="Activations" fill={theme.palette.primary.main} radius={[2, 2, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/**
 * An agent's activity (issue #28): one row per day of the data window, and activations by hour of day, side
 * by side at equal height. A day can hold duplicate evidence; the flag itself belongs to the agent for the
 * whole run, so no day is called flagged.
 */
export default function AgentActivity({ agentId }) {
  const load = useCallback(() => api.getAgentActivity(agentId), [agentId]);
  const result = useApi(load);
  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "repeat(2, minmax(0, 1fr))" }, gap: 3, mt: 3, alignItems: "stretch" }}>
      <SectionCard
        panel
        title="Daily activity"
        subtitle={(
          <>
            <Box component="span" sx={{ display: "block" }}>
              {`${RECORDED_NOTE} The flag applies to the agent for the whole detection run, not to single days.`}
            </Box>
            <Box component="span" sx={{ display: "block", mt: 0.5 }}>{ACTIVATION_NOTE}</Box>
          </>
        )}
        result={result}
        sx={{ p: 2.5, height: "100%", boxSizing: "border-box" }}
      >
        {(data) => <DailyTable days={data.days} />}
      </SectionCard>
      <SectionCard
        panel
        title="Activations by hour of day"
        subtitle={`${RECORDED_NOTE} Hours 0 to 23.`}
        result={result}
        table={hourTable}
        sx={{ p: 2.5, height: "100%", boxSizing: "border-box" }}
      >
        {(data) => (
          <>
            <HourChart hours={data.hours} />
            <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
              {`${data.totals.activations} activations, ${data.totals.completed} completed.`}
            </Typography>
          </>
        )}
      </SectionCard>
    </Box>
  );
}
