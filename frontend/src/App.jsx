import { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import AgentDetail from "./pages/AgentDetail";

export default function App() {
  const [username, setUsername] = useState(null);

  if (!username) {
    return <Login onLogin={setUsername} />;
  }

  return (
    <Routes>
      <Route path="/" element={<Dashboard username={username} onLogout={() => setUsername(null)} />} />
      <Route path="/agents/:agentId" element={<AgentDetail username={username} onLogout={() => setUsername(null)} />} />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}