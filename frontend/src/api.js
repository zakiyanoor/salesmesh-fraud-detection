const API_BASE = "/api";

async function request(endpoint, options = {}) {
  const resp = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
}

export const api = {
  login: (username, password) =>
    request("/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  logout: () => request("/logout", { method: "POST" }),
  getFlaggedAgents: () => request("/flagged-agents"),
  getAllAgents: () => request("/all-agents"),
  getAgentDetail: (agentId) => request(`/agents/${agentId}`),
  submitReviewDecision: (flagId, decisionOutcome) =>
    request("/review-decisions", {
      method: "POST",
      body: JSON.stringify({ flag_id: flagId, decision_outcome: decisionOutcome }),
    }),
  getAnalytics: () => request("/analytics"),
  getReviewHistory: () => request("/review-decisions"),
};