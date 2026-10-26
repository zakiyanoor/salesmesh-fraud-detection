// Surfaces for the signed-out pages, the landing page and sign in (issue #28). Light is designed on its own
// terms: a cool off-white page, crisp visible rules, a tinted hero band, white cards on a faintly tinted
// section and the deeper accent blue. Flat: no shadows on cards, no gradients. Dark keeps the lighter accent on dark surfaces.
import { alpha, darken, useTheme } from "@mui/material/styles";

export const RADIUS = "6px";
export const TEXTURE_STEP = 18;
export const GRID_STEP = 32;

/** Page tokens for the active scheme. */
export function useSurface() {
  const { palette } = useTheme();
  const dark = palette.mode === "dark";
  // Light: primary.dark (#1565C0, 5.75:1 with white, 5.35:1 on the page). Dark: primary.main (7.4:1 with its dark text).
  const accent = dark ? palette.primary.main : palette.primary.dark;
  return {
    dark,
    accent,
    accentHover: dark ? palette.primary.dark : darken(accent, 0.16),
    accentPressed: dark ? darken(palette.primary.main, 0.12) : darken(accent, 0.3),
    accentText: palette.primary.contrastText,
    accentSoft: alpha(accent, dark ? 0.45 : 0.4),
    link: palette.primary.dark,
    surface: palette.background.paper,
    rule: alpha(palette.text.primary, dark ? 0.13 : 0.15),
    ruleStrong: alpha(palette.text.primary, dark ? 0.22 : 0.26),
    band: alpha(accent, dark ? 0.06 : 0.055),
    section: dark ? alpha("#000000", 0.18) : alpha(palette.text.primary, 0.028),
    footer: dark ? palette.background.default : palette.background.paper,
    // A fine dot texture at very low contrast.
    grid: `linear-gradient(${alpha(palette.text.primary, dark ? 0.035 : 0.04)} 1px, transparent 1px), `
      + `linear-gradient(90deg, ${alpha(palette.text.primary, dark ? 0.035 : 0.04)} 1px, transparent 1px)`,
    texture: `radial-gradient(${alpha(palette.text.primary, dark ? 0.09 : 0.1)} 1px, transparent 1.2px)`,
  };
}

/** A contained accent button with clear hover, pressed, focus and disabled states in both schemes. */
export function accentButtonSx(t) {
  return {
    borderRadius: RADIUS,
    bgcolor: t.accent,
    color: t.accentText,
    "&:hover": { bgcolor: t.accentHover },
    "&:active": { bgcolor: t.accentPressed },
    "&.Mui-focusVisible, &:focus-visible": { outline: `2px solid ${t.accent}`, outlineOffset: 2 },
    "&.Mui-disabled": { bgcolor: t.rule, color: "text.secondary" },
  };
}

/** A text link in the accent with an underline on hover, a darker pressed state and an accent focus ring. */
export function linkSx(t, { color = t.link, underline = false } = {}) {
  return {
    color,
    borderRadius: "3px",
    textDecoration: underline ? "underline" : "none",
    textDecorationColor: alpha(t.accent, 0.4),
    textUnderlineOffset: "4px",
    "&:hover": { color: t.accentHover, textDecoration: "underline", textDecorationColor: "currentColor" },
    "&:active": { color: t.accentPressed },
    "&:focus-visible": { outline: `2px solid ${t.accent}`, outlineOffset: 2 },
  };
}
