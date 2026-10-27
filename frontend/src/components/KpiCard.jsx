import { Box, Paper, Skeleton, Typography } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import { mono } from "../theme";

/** "risk.high" -> theme.palette.risk.high; a colour value passes through. */
function paletteColour(theme, path) {
  return path.split(".").reduce((node, key) => node?.[key], theme.palette) ?? path;
}

/**
 * Summary figure card (docs/FRONTEND.md: 20px padding, mono value, caption label).
 * compact: a word or date rather than a number, in a smaller type so it fits beside the figures.
 * refined: the finished look (Overview): the icon in a 36px square tinted with its colour, the figure in the
 * display font with tabular numerals, a 13px label, a 12px note, an 8px radius and no shadow.
 */
export default function KpiCard({ icon, value, label, detail, color, loading = false, compact = false, refined = false }) {
  const theme = useTheme();
  if (refined) {
    const tone = paletteColour(theme, color || "primary.main");
    return (
      <Paper sx={{
        p: 2.5, flex: "1 1 160px", minWidth: 0, display: "flex", alignItems: "center", gap: 2,
        borderRadius: "8px", boxShadow: "none",
      }}>
        <Box aria-hidden="true" sx={{
          width: 36, height: 36, borderRadius: "8px", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center",
          bgcolor: alpha(tone, theme.palette.mode === "dark" ? 0.16 : 0.1), color: tone, "& svg": { fontSize: 20 },
        }}>
          {icon}
        </Box>
        <Box sx={{ minWidth: 0 }}>
          {loading ? (
            <Skeleton variant="text" width={64} height={compact ? 28 : 40} />
          ) : (
            <Typography component="p" sx={{
              fontFamily: (th) => th.typography.h1.fontFamily, fontVariantNumeric: "tabular-nums", fontWeight: 500,
              color: "text.primary",
              ...(compact
                ? { fontSize: 16, fontWeight: 600, lineHeight: 1.3, overflowWrap: "normal" }
                : { fontSize: 32, lineHeight: 1.1, letterSpacing: "-0.01em", overflowWrap: "anywhere" }),
            }}>
              {value}
            </Typography>
          )}
          <Typography sx={{ fontSize: 13, lineHeight: 1.4, color: "text.secondary", mt: 0.5 }}>{label}</Typography>
          {detail && !loading && (
            <Typography sx={{ fontSize: 12, lineHeight: 1.4, color: "text.secondary", fontVariantNumeric: "tabular-nums" }}>{detail}</Typography>
          )}
        </Box>
      </Paper>
    );
  }
  return (
    <Paper sx={{ p: 2.5, flex: "1 1 160px", minWidth: 0, display: "flex", alignItems: "center", gap: 2 }}>
      <Box sx={{ color: color || "primary.main", display: "flex" }} aria-hidden="true">{icon}</Box>
      <Box sx={{ minWidth: 0 }}>
        {loading ? (
          <Skeleton variant="text" width={64} height={40} />
        ) : (
          <Typography
            variant={compact ? "subtitle1" : "h4"}
            component="p"
            sx={compact ? { fontWeight: 600, lineHeight: 1.3 } : { ...mono, lineHeight: 1, overflowWrap: "anywhere" }}
          >
            {value}
          </Typography>
        )}
        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>{label}</Typography>
        {detail && !loading && (
          <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>{detail}</Typography>
        )}
      </Box>
    </Paper>
  );
}
