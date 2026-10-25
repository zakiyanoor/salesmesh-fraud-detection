import { lazy } from "react";
import { Navigate, Routes, Route, useLocation } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";
import { useAuth } from "./auth/authContext";
import { PAGES } from "./auth/roles";
import RequireRole from "./auth/RequireRole";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Landing, { SIGN_IN_PATH } from "./pages/Landing";
import { AccessDenied, NotFound } from "./pages/StatusPages";

// Every page is its own chunk, loaded on first visit; Login and the layout shell stay in the main bundle.
const PAGE_COMPONENTS = {
  overview: lazy(() => import("./pages/Dashboard")),
  flagged: lazy(() => import("./pages/FlaggedAgents")),
  allAgents: lazy(() => import("./pages/AllAgents")),
  agentDetail: lazy(() => import("./pages/AgentDetail")),
  analytics: lazy(() => import("./pages/Analytics")),
  history: lazy(() => import("./pages/ReviewHistory")),
  confirm: lazy(() => import("./pages/ConfirmQueue")),
  threat: lazy(() => import("./pages/ThreatIntelligence")),
  audit: lazy(() => import("./pages/AuditLog")),
  reports: lazy(() => import("./pages/Reports")),
  accounts: lazy(() => import("./pages/Accounts")),
  howItWorks: lazy(() => import("./pages/HowItWorks")),
};

export default function App() {
  const { status, notice } = useAuth();
  const { pathname } = useLocation();

  if (status === "loading") {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <CircularProgress aria-label="Checking your session" />
      </Box>
    );
  }
  // Signed out at the site root: the landing page (issue #28), unless the sign-in page has a message to show
  // (for example a deactivated account). Signed out on any other address: after signing in, the same
  // address opens (if the role allows it); /sign-in opens the usual home page.
  if (status !== "authenticated") return pathname === "/" && !notice ? <Landing /> : <Login />;

  return (
    <Routes>
      <Route element={<Layout />}>
        {PAGES.map(({ key, path, roles }) => {
          const Page = PAGE_COMPONENTS[key];
          return <Route key={key} path={path} element={<RequireRole roles={roles}><Page /></RequireRole>} />;
        })}
        <Route path={SIGN_IN_PATH} element={<Navigate to="/" replace />} />
        <Route path="/403" element={<AccessDenied />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
