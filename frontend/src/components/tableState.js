export const ROWS_PER_PAGE = [10, 25, 50, 100];

/** Next sort after clicking a column: the same column flips direction, a new column starts descending. */
export function nextSort(current, key) {
  if (current.key === key) return { key, dir: current.dir === "asc" ? "desc" : "asc" };
  return { key, dir: "desc" };
}

/** Page number and page size from query-string values, clamped to valid numbers. */
export function paging(values) {
  const size = Number(values.size);
  return {
    page: Math.max(0, Number.parseInt(values.page, 10) || 0),
    rowsPerPage: ROWS_PER_PAGE.includes(size) ? size : ROWS_PER_PAGE[1],
  };
}
