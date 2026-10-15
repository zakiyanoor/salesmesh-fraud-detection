import { useState } from "react";
import { Box, Button, Paper, Skeleton, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { mono } from "../theme";

const visuallyHidden = {
  position: "absolute", width: "1px", height: "1px", p: 0, m: "-1px", overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap", border: 0,
};

/**
 * A card with its own loading, error and empty state, so one failing request does not blank a page.
 * children is a function of the loaded data. isEmpty(data) decides the empty state.
 * table(data) -> { columns: [{ key, label }], rows } marks children as a chart: the chart gets a text
 * label, and a "Show as table" toggle replaces it with the same numbers as a table.
 */
export default function SectionCard({ title, subtitle, result, isEmpty, emptyText = "Nothing to show yet.", table, sx, children }) {
  const [asTable, setAsTable] = useState(false);
  const ready = !result.loading && !result.error && !isEmpty?.(result.data);

  let body;
  if (result.loading || result.error?.status === 401) {
    body = (
      <Box role="status" aria-live="polite" aria-busy="true">
        <Box component="span" sx={visuallyHidden}>Loading {title}…</Box>
        <Skeleton variant="rounded" height={160} />
      </Box>
    );
  } else if (result.error) {
    body = (
      <Box role="alert">
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          {result.error.status === 403 ? "Your role does not have access to this." : result.error.message}
        </Typography>
        {result.error.status !== 403 && (
          <Button size="small" variant="outlined" onClick={result.retry}>Try again</Button>
        )}
      </Box>
    );
  } else if (isEmpty?.(result.data)) {
    body = <Typography variant="body2" color="text.secondary">{emptyText}</Typography>;
  } else if (table && asTable) {
    const { columns, rows } = table(result.data);
    body = (
      <TableContainer>
        <Table size="small" aria-label={`${title} data`}>
          <TableHead>
            <TableRow>{columns.map((c) => <TableCell key={c.key}>{c.label}</TableCell>)}</TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row, i) => (
              <TableRow key={i}>
                {columns.map((c, j) => (
                  <TableCell key={c.key} sx={j > 0 ? mono : undefined}>{row[c.key]}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  } else if (table) {
    body = (
      <Box role="img" aria-label={`${title} chart. Choose "Show as table" to read the values.`}>
        {children(result.data)}
      </Box>
    );
  } else {
    body = children(result.data);
  }

  return (
    <Paper component="section" aria-label={title} sx={{ p: 3, minWidth: 0, ...sx }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 1 }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="overline" color="text.secondary" component="h2">{title}</Typography>
          {subtitle && (
            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>{subtitle}</Typography>
          )}
        </Box>
        {table && ready && (
          <Button size="small" onClick={() => setAsTable((v) => !v)} aria-pressed={asTable} sx={{ flexShrink: 0 }}>
            {asTable ? "Show as chart" : "Show as table"}
          </Button>
        )}
      </Box>
      <Box sx={{ mt: 2 }}>{body}</Box>
    </Paper>
  );
}
