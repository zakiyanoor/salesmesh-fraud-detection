import { Suspense, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { AppBar, Box, IconButton, Toolbar, Typography, useMediaQuery } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import MenuIcon from "@mui/icons-material/MenuOutlined";
import Sidebar from "./Sidebar";
import ErrorBoundary from "./ErrorBoundary";
import AppFooter from "./AppFooter";
import { PageSkeleton } from "./states";

export default function Layout() {
  const theme = useTheme();
  const desktop = useMediaQuery(theme.breakpoints.up("md"), { noSsr: true });
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
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
        <Box component="main" sx={{ flexGrow: 1, minWidth: 0 }}>
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
