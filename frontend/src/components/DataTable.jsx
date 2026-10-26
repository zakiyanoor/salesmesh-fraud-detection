import { useMemo } from "react";
import {
  Box, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TablePagination, TableRow, TableSortLabel,
  Typography, useMediaQuery,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { ROWS_PER_PAGE } from "./tableState";

const visuallyHidden = {
  // Pixel strings: in sx a bare 1 means 100% and m: -1 means -8px.
  position: "absolute", width: "1px", height: "1px", p: 0, m: "-1px", overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap", border: 0,
};

/**
 * Sortable, paged table that turns into cards below md (docs/FRONTEND.md, Tables).
 * columns: { key, label, render(row), sortValue?(row), align?, title? (the card heading), action? (buttons) }.
 * An action column's label is read by screen readers only; on cards its content sits at the bottom.
 * sort is { key, dir }; page and rowsPerPage are numbers. Sorting and paging happen here, unless
 * totalCount is given: then rows are already the current page from the server.
 * onRowClick(row, element) makes rows clickable; the row takes focus so a drawer can return focus to it.
 * refined: the finished look (Flagged agents): 13px secondary headings, hairline rows with a hover and a
 * keyboard focus highlight, tabular numerals, and flat 8px cards on narrow screens.
 */
// The refined table: quiet headings, hairline rows, a highlight on hover and while a row holds keyboard focus.
const REFINED_TABLE = {
  "& th": { fontSize: 13, fontWeight: 500, color: "text.secondary", py: 1, borderColor: "divider" },
  "& td": { fontSize: 14, py: 1.25, borderColor: "divider", fontVariantNumeric: "tabular-nums" },
  "& tbody tr:last-of-type td": { borderBottom: 0 },
  "& tbody tr:focus-within": { bgcolor: "action.hover" },
};

export default function DataTable({
  label, columns, rows, rowKey, sort, onSort, page, rowsPerPage, onPageChange, onRowsPerPageChange, emptyText,
  totalCount, onRowClick, refined = false,
}) {
  const theme = useTheme();
  const cards = useMediaQuery(theme.breakpoints.down("md"), { noSsr: true });

  const sorted = useMemo(() => {
    const column = columns.find((c) => c.key === sort?.key && c.sortValue);
    if (!column) return rows;
    const dir = sort.dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const x = column.sortValue(a);
      const y = column.sortValue(b);
      // Missing values always sort last.
      if (x == null && y == null) return 0;
      if (x == null) return 1;
      if (y == null) return -1;
      return dir * (typeof x === "string" ? x.localeCompare(y) : x - y);
    });
  }, [rows, columns, sort]);

  const serverPaged = totalCount != null;
  const count = serverPaged ? totalCount : sorted.length;
  const lastPage = Math.max(0, Math.ceil(count / rowsPerPage) - 1);
  const safePage = serverPaged ? page : Math.min(page, lastPage);
  const visible = serverPaged ? sorted : sorted.slice(safePage * rowsPerPage, safePage * rowsPerPage + rowsPerPage);
  const titleColumn = columns.find((c) => c.title) || columns[0];

  const pagination = count > 0 && (
    <TablePagination
      component="div"
      count={count}
      page={safePage}
      rowsPerPage={rowsPerPage}
      rowsPerPageOptions={ROWS_PER_PAGE}
      onPageChange={(_, next) => onPageChange(next)}
      onRowsPerPageChange={(e) => onRowsPerPageChange(Number(e.target.value))}
      labelRowsPerPage={cards ? "Rows" : "Rows per page"}
    />
  );

  if (cards) {
    return (
      <Box component="section" aria-label={label}>
        {visible.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: "center" }}>{emptyText}</Typography>
        )}
        <Box component="ul" sx={{ listStyle: "none", p: 0, m: 0, display: "grid", gap: 1.5 }}>
          {visible.map((row) => (
            <Paper component="li" key={rowKey(row)} sx={{ p: 2, ...(refined ? { borderRadius: "8px", boxShadow: "none" } : {}) }}>
              <Box sx={{ mb: 1 }}>{titleColumn.render(row)}</Box>
              <Box component="dl" sx={{ m: 0, display: "grid", gridTemplateColumns: "auto 1fr", columnGap: 2, rowGap: 0.75 }}>
                {columns.filter((c) => c !== titleColumn && !c.action).map((c) => (
                  <Box key={c.key} sx={{ display: "contents" }}>
                    <Typography component="dt" variant="caption" color="text.secondary" sx={{ alignSelf: "center" }}>{c.label}</Typography>
                    <Box component="dd" sx={{ m: 0, minWidth: 0, overflowWrap: "anywhere", typography: "body2" }}>{c.render(row)}</Box>
                  </Box>
                ))}
              </Box>
              {columns.filter((c) => c.action).map((c) => (
                <Box key={c.key} sx={{ mt: 1.5, display: "flex", justifyContent: "flex-end" }}>{c.render(row)}</Box>
              ))}
            </Paper>
          ))}
        </Box>
        {pagination}
      </Box>
    );
  }

  return (
    <Box component="section" aria-label={label}>
      <TableContainer>
        <Table size="small" aria-label={label} sx={refined ? REFINED_TABLE : undefined}>
          <TableHead>
            <TableRow>
              {columns.map((c) => (
                <TableCell key={c.key} align={c.align} sortDirection={sort?.key === c.key ? sort.dir : false}>
                  {c.action ? (
                    <Box component="span" sx={visuallyHidden}>{c.label}</Box>
                  ) : c.sortValue ? (
                    <TableSortLabel
                      active={sort?.key === c.key}
                      direction={sort?.key === c.key ? sort.dir : "asc"}
                      onClick={() => onSort(c.key)}
                    >
                      {c.label}
                    </TableSortLabel>
                  ) : (
                    c.label
                  )}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {visible.map((row) => (
              <TableRow
                key={rowKey(row)}
                hover
                {...(onRowClick && {
                  tabIndex: -1,
                  onClick: (e) => onRowClick(row, e.currentTarget),
                  sx: { cursor: "pointer", "&:focus-visible": { outline: 2, outlineColor: "primary.main", outlineOffset: -2 } },
                })}
              >
                {columns.map((c) => (
                  <TableCell key={c.key} align={c.align} sx={c.cellSx}>{c.render(row)}</TableCell>
                ))}
              </TableRow>
            ))}
            {visible.length === 0 && (
              <TableRow>
                <TableCell colSpan={columns.length} align="center" sx={{ py: 4, color: "text.secondary" }}>{emptyText}</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      {pagination}
    </Box>
  );
}
