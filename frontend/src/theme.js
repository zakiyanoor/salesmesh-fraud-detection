import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    mode: "light",
    background: {
      default: "#F5F7FA",
      paper: "#FFFFFF",
    },
    text: {
      primary: "#1A1D21",
      secondary: "#6B7280",
    },
    divider: "#E0E4E8",
    primary: {
      main: "#1976D2",
      contrastText: "#FFFFFF",
    },
    // Status colours are darkened so they stay readable as text on white (≥ 4.5:1).
    error: {
      main: "#D32F2F",
    },
    warning: {
      main: "#B45309",
    },
    success: {
      main: "#2E7D4F",
    },
    action: {
      selected: "rgba(25, 118, 210, 0.08)",
    },
  },
  typography: {
    fontFamily: '"IBM Plex Sans", sans-serif',
    h1: { fontFamily: '"Space Grotesk", sans-serif', fontWeight: 600 },
    h2: { fontFamily: '"Space Grotesk", sans-serif', fontWeight: 600 },
    h3: { fontFamily: '"Space Grotesk", sans-serif', fontWeight: 600 },
    h4: { fontFamily: '"Space Grotesk", sans-serif', fontWeight: 600 },
    h5: { fontFamily: '"Space Grotesk", sans-serif', fontWeight: 600 },
    h6: { fontFamily: '"Space Grotesk", sans-serif', fontWeight: 600 },
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
        },
      },
    },
  },
});

export default theme;