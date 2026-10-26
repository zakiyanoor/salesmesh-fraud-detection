import { Link as RouterLink } from "react-router-dom";
import { Box, Link, Typography } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import { linkSx, useSurface } from "./surfaces";

const CARD_RADIUS = "8px";

/**
 * The four platform cards (issue #28): a label chip, a heading, the paragraph and one text link, in a calm two by
 * two grid. The card itself is not interactive; only its link takes focus. `href` turns a page into the
 * landing page's address for it (sign in first while signed out).
 */
export default function PlatformCards({ cards, href }) {
  const t = useSurface();
  const { palette } = useTheme();
  const border = t.dark ? alpha(palette.primary.main, 0.16) : t.ruleStrong;
  const chip = t.dark
    ? { bgcolor: palette.background.default, borderColor: alpha(palette.primary.main, 0.24), color: alpha(palette.primary.main, 0.88) }
    : { bgcolor: alpha(t.accent, 0.07), borderColor: alpha(t.accent, 0.24), color: t.accent };
  return (
    <Box component="ul" sx={{
      listStyle: "none", m: 0, p: 0, display: "grid", gap: { xs: 2, md: 3 },
      gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "repeat(2, minmax(0, 1fr))" },
    }}>
      {cards.map((card) => (
        <Box component="li" key={card.title} sx={{
          position: "relative", minWidth: 0, minHeight: { md: 240 }, boxSizing: "border-box",
          display: "flex", flexDirection: "column", alignItems: "flex-start",
          p: { xs: 3, sm: 4 }, bgcolor: "background.paper", border: `1px solid ${border}`, borderRadius: CARD_RADIUS,
          transition: "border-color 120ms linear",
          // A quiet accent edge down the left side on hover, or while the card's link has focus.
          "&::before": {
            content: '""', position: "absolute", left: -1, top: -1, bottom: -1, width: 3, // the 1px border plus 2px inside
            borderRadius: `${CARD_RADIUS} 0 0 ${CARD_RADIUS}`, bgcolor: t.accent, opacity: 0, transition: "opacity 120ms linear",
          },
          "&:hover, &:focus-within": { borderColor: t.accent, "&::before": { opacity: 1 } },
        }}>
          <Box component="span" sx={{
            border: "1px solid", ...chip, fontFamily: (th) => th.typography.fontFamilyMono, fontSize: 12, lineHeight: "18px",
            px: 1, py: 0.25, borderRadius: "4px", mb: 2,
          }}>
            {card.chip}
          </Box>
          <Typography component="h3" sx={{ fontSize: 22, fontWeight: 600, letterSpacing: "-0.01em", fontFamily: (th) => th.typography.h3.fontFamily, mb: 1, color: "text.primary" }}>
            {card.title}
          </Typography>
          <Typography sx={{ fontSize: 15, lineHeight: 1.6, color: "text.secondary", maxWidth: "55ch", mb: 2.5 }}>{card.text}</Typography>
          <Link component={RouterLink} to={href(card.path)} sx={{ ...linkSx(t), mt: "auto", fontSize: 15, fontWeight: 500 }}>
            {card.link}
          </Link>
        </Box>
      ))}
    </Box>
  );
}
