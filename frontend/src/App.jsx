import { Routes, Route } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";
import { useAuth } from "./auth/authContext";
import { PAGES } from "./auth/roles";
import RequireRole from "./auth/RequireRole";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import FlaggedAgents from "./pages/FlaggedAgents";
import AllAgents from "./pages/AllAgents";
import AgentDetail from "./pages/AgentDetail";
import Analytics from "./pages/Analytics";
import ReviewHistory from "./pages/ReviewHistory";
import ConfirmQueue from "./pages/ConfirmQueue";
import ThreatIntelligence from "./pages/ThreatIntelligence";
import AuditLog from "./pages/AuditLog";
import Reports from "./pages/Reports";
import { AccessDenied, ComingSoon, NotFound } from "./pages/StatusPages";

const PAGE_COMPONENTS = {
  overview: Dashboard,
  flagged: FlaggedAgents,
  allAgents: AllAgents,
  agentDetail: AgentDetail,
  analytics: Analytics,
  history: ReviewHistory,
  confirm: ConfirmQueue,
  threat: ThreatIntelligence,
  audit: AuditLog,
  reports: Reports,
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
        {PAGES.map(({ key, path, label, roles }) => {
          const Page = PAGE_COMPONENTS[key];
          return (
            <Route
              key={key}
              path={path}
              element={<RequireRole roles={roles}>{Page ? <Page /> : <ComingSoon title={label} />}</RequireRole>}
            />
          );
        })}
        <Route path="/403" element={<AccessDenied />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
