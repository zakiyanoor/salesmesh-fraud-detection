import { Box, Typography } from "@mui/material";
import { useLatestRun } from "../latestRun/latestRunContext";
import { formatDateTime } from "../format";

const STATUS = { succeeded: "succeeded", failed: "failed", running: "running" };

/** Small muted line under every signed-in page: model version and the last detection run. */
export default function AppFooter() {
  const run = useLatestRun();
  let text;
  if (run.loading || run.error?.status === 401) text = "Checking the last detection run…";
  else if (run.error) text = "Detection run status unavailable";
  else if (!run.data?.run) text = "No detection run yet";
  else {
    const r = run.data.run;
    const when = formatDateTime(r.finished_at || r.started_at);
    text = `Model ${r.model_version || "unknown"} · Last detection run ${when}${r.status === "succeeded" ? "" : ` (${STATUS[r.status] || r.status})`}`;
  }
  return (
    <Box component="footer" sx={{ mt: 6, pt: 2, borderTop: 1, borderColor: "divider" }}>
      <Typography variant="caption" color="text.secondary" aria-live="polite">{text}</Typography>
    </Box>
  );
}
