import { vi } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ColorModeProvider from "../colorMode/ColorModeProvider";
import AuthProvider from "../auth/AuthProvider";
import App from "../App";

export const ACCOUNTS = {
  fraud_analyst: { username: "analyst_01", role: "fraud_analyst" },
  compliance_officer: { username: "compliance_01", role: "compliance_officer" },
  admin: { username: "admin_01", role: "admin" },
};

const AGENT = {
  agent_id: "A10001", region: "Nairobi", status: "flagged", flag_source: "ML", risk_band: "high",
  suspicion_score: 3.2, submission_frequency: 20, time_of_day_dist: 0.8, customer_similarity: 0.1, collusion_score: 0.3,
};

export const FIXTURES = {
  "GET /api/flagged-agents": {
    count: 1,
    flagged_agents: [{ ...AGENT, flag_id: "FL1", flag_status: "flagged", analysis_period: "2026-08", model_version: "lof_v3_4f" }],
  },
  "GET /api/all-agents": { count: 1, agents: [AGENT] },
  "GET /api/analytics": {
    score_distribution: [{ bucket: "1.0-1.5", count: 1 }],
    region_breakdown: [{ region: "Nairobi", flagged: 1, total: 1 }],
    platform_averages: { submission_frequency: 14, time_of_day_dist: 0.78, customer_similarity: 0.102 },
  },
  "GET /api/review-decisions": { count: 0, decisions: [] },
  "GET /api/agents/A10001": {
    ...AGENT, registration_timestamp: "2026-06-11T20:56:24",
    features: { submission_frequency: 20, time_of_day_dist: 0.8, customer_similarity: 0.1, collusion_score: 0.3 },
    flag: { flag_id: "FL1", flag_status: "flagged", model_version: "lof_v3_4f", suspicion_score: 3.2 },
  },
  "POST /api/logout": { message: "Logged out successfully" },
  "GET /api/threat-intelligence/summary": {
    agents_scored: 1000, flagged: 145, flagged_rate: 0.145, rule_flagged: 102,
    flag_sources: { ML: 72, Rule: 29, Both: 73, None: 826 },
    risk_bands: { high: 145, review: 89, low: 766 },
  },
  "GET /api/detection-runs/latest": {
    run: {
      run_id: "RUN1", trigger: "manual", status: "succeeded", started_at: "2026-10-13T15:07:08",
      finished_at: "2026-10-13T15:07:16", agents_scored: 1000, flagged_count: 145, error: null,
    },
  },
  "GET /api/agent-scores": {
    total: 3, count: 3, offset: 0, threshold: 1.444799,
    scores: [
      { agent_id: "A35485", anomaly_score: 5.563827, flag_source: "Both", risk_band: "high" },
      { agent_id: "A10001", anomaly_score: 3.2, flag_source: "ML", risk_band: "high" },
      { agent_id: "A20002", anomaly_score: 1.35, flag_source: "Rule", risk_band: "review" },
    ],
  },
};

export function reply(status, body) {
  return { status, body };
}

/**
 * Stubs fetch. routes maps "METHOD /path" (no query) to a body (200), a reply(status, body),
 * a function (request) => either, or an Error to simulate a network failure. Unknown routes are 404.
 */
export function mockApi(routes = {}) {
  const calls = [];
  const fetchMock = vi.fn(async (url, init = {}) => {
    const method = init.method || "GET";
    const path = String(url).split("?")[0];
    const request = { method, path, url: String(url), init, body: init.body ? JSON.parse(init.body) : undefined };
    calls.push(request);
    let route = routes[`${method} ${path}`] ?? FIXTURES[`${method} ${path}`];
    if (typeof route === "function") route = route(request);
    if (route instanceof Error) throw route;
    const { status, body } = route && "status" in route && "body" in route ? route : { status: route ? 200 : 404, body: route ?? { error: "Not found" } };
    return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { fetchMock, calls };
}

/** A signed-in session for role (or none when role is null). */
export function sessionRoutes(role) {
  return { "GET /api/me": role ? ACCOUNTS[role] : reply(401, { error: "Authentication required" }) };
}

export function renderApp(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ColorModeProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ColorModeProvider>
    </MemoryRouter>,
  );
}
