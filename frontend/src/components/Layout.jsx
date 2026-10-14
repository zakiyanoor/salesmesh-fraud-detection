import { Suspense, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { AppBar, Box, IconButton, Toolbar, Typography, useMediaQuery } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import MenuIcon from "@mui/icons-material/MenuOutlined";
import Sidebar from "./Sidebar";
import ErrorBoundary from "./ErrorBoundary";
import AppFooter from "./AppFooter";
import { PageSkeleton } from "./states";

/** First stop for keyboard users: jumps past the menu to the page content. Hidden until focused. */
function SkipLink() {
  return (
    <Box
      component="a"
      href="#main-content"
      sx={{
        position: "absolute",
        left: 8,
        top: -48,
        zIndex: (t) => t.zIndex.tooltip + 1,
        px: 2,
        py: 1,
        bgcolor: "background.paper",
        color: "primary.dark",
        border: 1,
        borderColor: "primary.main",
        borderRadius: 1,
        typography: "body2",
        fontWeight: 500,
        "&:focus": { top: 8 },
      }}
    >
      Skip to content
    </Box>
  );
}

export default function Layout() {
  const theme = useTheme();
  const desktop = useMediaQuery(theme.breakpoints.up("md"), { noSsr: true });
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <SkipLink />
      {!desktop && (
        <AppBar
          position="fixed"
          color="inherit"
          elevation={0}
          sx={{ bgcolor: "background.paper", border: 0, borderBottom: 1, borderColor: "divider" }}
        >
          <Toolbar>
            <IconButton edge="start" aria-label="Open menu" onClick={() => setMenuOpen(true)} sx={{ mr: 1 }}>
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" component="div">SalesMesh</Typography>
          </Toolbar>
        </AppBar>
      )}

      <Sidebar
        variant={desktop ? "permanent" : "temporary"}
        open={desktop || menuOpen}
        onClose={() => setMenuOpen(false)}
        onNavigate={() => setMenuOpen(false)}
      />

      {/* The permanent drawer already takes its 240px in this row, so the content needs no margin. */}
      <Box sx={{ flexGrow: 1, minWidth: 0, p: { xs: 2, md: 5 }, display: "flex", flexDirection: "column" }}>
        {!desktop && <Toolbar />}
        <Box component="main" id="main-content" tabIndex={-1} sx={{ flexGrow: 1, minWidth: 0, "&:focus": { outline: "none" } }}>
          <ErrorBoundary key={location.pathname}>
            <Suspense fallback={<PageSkeleton cards={2} rows={6} />}>
              <Outlet />
            </Suspense>
          </ErrorBoundary>
        </Box>
        <AppFooter />
      </Box>
    </Box>
  );
}
