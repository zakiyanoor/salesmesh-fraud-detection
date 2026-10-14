import { lazy } from "react";
import { Routes, Route } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";
import { useAuth } from "./auth/authContext";
import { PAGES } from "./auth/roles";
import RequireRole from "./auth/RequireRole";
import Layout from "./components/Layout";
import Login from "./pages/Login";
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
};

export default function App() {
  const { status } = useAuth();

  if (status === "loading") {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <CircularProgress aria-label="Checking your session" />
      </Box>
    );
  }
  // Signed out on any address: after signing in, the same address opens (if the role allows it).
  if (status !== "authenticated") return <Login />;

  return (
    <Routes>
      <Route element={<Layout />}>
        {PAGES.map(({ key, path, roles }) => {
          const Page = PAGE_COMPONENTS[key];
          return <Route key={key} path={path} element={<RequireRole roles={roles}><Page /></RequireRole>} />;
        })}
        <Route path="/403" element={<AccessDenied />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
