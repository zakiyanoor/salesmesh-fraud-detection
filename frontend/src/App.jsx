import { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import AgentDetail from "./pages/AgentDetail";
import Analytics from "./pages/Analytics";
import ReviewHistory from "./pages/ReviewHistory";

export default function App() {
  const [username, setUsername] = useState(null);

  if (!username) {
    return <Login onLogin={setUsername} />;
  }

  const shared = { username, onLogout: () => setUsername(null) };

  return (
    <Routes>
      <Route path="/" element={<Dashboard {...shared} />} />
      <Route path="/agents/:agentId" element={<AgentDetail {...shared} />} />
      <Route path="/analytics" element={<Analytics {...shared} />} />
      <Route path="/history" element={<ReviewHistory {...shared} />} />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}