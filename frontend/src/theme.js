import { createTheme } from "@mui/material/styles";

// The style guide for these tokens is docs/FRONTEND.md.
const SANS = '"IBM Plex Sans", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
const HEADING = '"Space Grotesk", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
const MONO = '"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';

export const PALETTES = {
  light: {
    background: { default: "#F5F7FA", paper: "#FFFFFF" },
    text: { primary: "#1A1D21", secondary: "#6B7280" },
    divider: "#E0E4E8",
    // primary.dark is for primary-coloured text on the page background or a tinted surface (AA there).
    primary: { main: "#1976D2", dark: "#1565C0", contrastText: "#FFFFFF" },
    // Status colours are darkened so they stay readable as text on white (AA).
    error: { main: "#D32F2F" },
    warning: { main: "#B45309" },
    success: { main: "#2E7D4F" },
    selected: "rgba(25, 118, 210, 0.08)",
    chartNeutral: "#8A9199",
    // Categorical palette for regions; avoids the red/amber/green used for status and risk.
    region: ["#1976D2", "#00897B", "#F59E0B", "#8E24AA", "#546E7A"],
  },
  dark: {
    background: { default: "#0F141A", paper: "#171D24" },
    text: { primary: "#E6E9ED", secondary: "#9AA4B1" },
    divider: "#2A333D",
    primary: { main: "#64A8F0", dark: "#8DC0F5", contrastText: "#0F141A" },
    error: { main: "#F28B82" },
    warning: { main: "#F0A848" },
    success: { main: "#5FC48B" },
    selected: "rgba(100, 168, 240, 0.16)",
    chartNeutral: "#6E7A87",
    region: ["#64A8F0", "#26A69A", "#F59E0B", "#BA68C8", "#90A4AE"],
  },
};

export const RISK_BANDS = ["high", "review", "low"];

/** Mono figures (ids, scores, counts): sx={mono}. */
export const mono = { fontFamily: (theme) => theme.typography.fontFamilyMono };

// Touch screens get 44px targets; with a mouse the compact look stays.
const TOUCH = "@media (pointer: coarse)";

export function createAppTheme(mode = "light") {
  const p = PALETTES[mode];
  return createTheme({
    palette: {
      mode,
      background: p.background,
      text: p.text,
      divider: p.divider,
      primary: p.primary,
      error: p.error,
      warning: p.warning,
      success: p.success,
      action: { selected: p.selected },
      risk: {
        high: p.error.main,
        review: p.warning.main,
        low: p.success.main,
        none: p.text.secondary,
      },
      chart: { grid: p.divider, axis: p.text.secondary, neutral: p.chartNeutral, region: p.region },
    },
    typography: {
      fontFamily: SANS,
      fontFamilyMono: MONO,
      h1: { fontFamily: HEADING, fontWeight: 600 },
      h2: { fontFamily: HEADING, fontWeight: 600 },
      h3: { fontFamily: HEADING, fontWeight: 600 },
      h4: { fontFamily: HEADING, fontWeight: 600 },
      h5: { fontFamily: HEADING, fontWeight: 600 },
      h6: { fontFamily: HEADING, fontWeight: 600 },
      button: { textTransform: "none", fontWeight: 500 },
    },
    shape: {
      borderRadius: 4,
    },
    components: {
      MuiPaper: {
        styleOverrides: {
          root: ({ theme }) => ({
            backgroundImage: "none",
            border: `1px solid ${theme.palette.divider}`,
          }),
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            boxShadow: "none",
            "&:hover": { boxShadow: "none" },
            [TOUCH]: { minHeight: 44 },
          },
          text: ({ theme, ownerState }) =>
            ownerState.color === "primary" || !ownerState.color ? { color: theme.palette.primary.dark } : {},
        },
      },
      MuiIconButton: { styleOverrides: { root: { [TOUCH]: { minWidth: 44, minHeight: 44 } } } },
      MuiListItemButton: { styleOverrides: { root: { [TOUCH]: { minHeight: 44 } } } },
      MuiMenuItem: { styleOverrides: { root: { [TOUCH]: { minHeight: 44 } } } },
    },
  });
}
