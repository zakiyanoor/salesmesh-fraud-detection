import { Box, Paper, Skeleton, Typography } from "@mui/material";
import { mono } from "../theme";

/** Summary figure card (docs/FRONTEND.md: 20px padding, mono value, caption label). */
export default function KpiCard({ icon, value, label, detail, color, loading = false }) {
  return (
    <Paper sx={{ p: 2.5, flex: "1 1 180px", minWidth: 0, display: "flex", alignItems: "center", gap: 2 }}>
      <Box sx={{ color: color || "primary.main", display: "flex" }} aria-hidden="true">{icon}</Box>
      <Box sx={{ minWidth: 0 }}>
        {loading ? (
          <Skeleton variant="text" width={64} height={40} />
        ) : (
          <Typography variant="h4" component="p" sx={{ ...mono, lineHeight: 1, overflowWrap: "anywhere" }}>{value}</Typography>
        )}
        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>{label}</Typography>
        {detail && !loading && (
          <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>{detail}</Typography>
        )}
      </Box>
    </Paper>
  );
}
