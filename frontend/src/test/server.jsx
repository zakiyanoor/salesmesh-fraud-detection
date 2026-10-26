import { vi } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import LocationProbe from "./LocationProbe";
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
    review: { proposals: 6, open: 2, overdue: 1, withdrawn: 1, agreed: 2, overruled: 1, corrections: 1, overrule_rate: 0.3333, overdue_hours: 72 },
  },
  "GET /api/review-decisions": { count: 0, decisions: [] },
  "GET /api/agents/A10001": {
    ...AGENT, registration_timestamp: "2026-06-11T20:56:24",
    features: { submission_frequency: 20, time_of_day_dist: 0.8, customer_similarity: 0.1, collusion_score: 0.3 },
    flag: { flag_id: "FL1", flag_status: "flagged", model_version: "lof_v3_4f", suspicion_score: 3.2 },
    duplicate_evidence: [
      { customer_id: "CUST10000001", customer_ref: "c_00112233445566778899aabb", client_id: "CL01", other_agent_id: "A20002", reason: "shared customer", record_ids: ["R1"] },
    ],
    review: {
      reviewable: true, reason: null, flag_id: "FL1", flag_source: "ML", open_decision_id: null, open_proposed_by: null,
      open_is_mine: false, final_decision_id: null, effective_outcome: null,
    },
  },
  "POST /api/logout": { message: "Logged out successfully" },
  "GET /api/model-info": {
    model_version: "lof_v3_4f", features: ["submission_frequency", "time_of_day_entropy", "customer_similarity", "collusion_score"],
    cutoff: 1.4447993633890617, cutoff_rule: "min expected cost 5:1", cutoff_chosen_on: "validation", test_agents: 150, test_fraud_agents: 19,
    results: {
      model: { method: "lof_v3_4f (cutoff 1.445)", precision: 0.6, recall: 0.7894736842105263, pr_auc: 0.84536680072518, roc_auc: 0.9533949377259944, precision_ci: [0.39, 0.79], recall_ci: [0.58, 0.96], pr_auc_ci: [0.6842170081902225, 0.9603234989648033], roc_auc_ci: [0.8972917468150516, 0.9915910062160062], flagged: 25, tp: 15, fp: 10, fn: 4, tn: 121 },
      rule: { method: "duplicate_activation_rule (pairs > 0)", precision: 1, recall: 0.8421052631578947, pr_auc: 0.8621052631578945, roc_auc: 0.9210526315789473, precision_ci: [1, 1], recall_ci: [0.65, 1], pr_auc_ci: [0.6962962962962964, 1], roc_auc_ci: [0.8234768907563025, 1], flagged: 16, tp: 16, fp: 0, fn: 3, tn: 131 },
      model_or_rule: { method: "SECONDARY: union of model flag and duplicate rule flag", precision: 0.6551724137931034, recall: 1, pr_auc: 0.6551724137931034, roc_auc: 0.9618320610687022, precision_ci: [0.46, 0.83], recall_ci: [1, 1], pr_auc_ci: [0.46, 0.83], roc_auc_ci: [0.94, 0.98], flagged: 29, tp: 19, fp: 10, fn: 0, tn: 121 },
    },
    measured_on: "the 150 held-out test agents, scored once with the frozen model; not a promise for other data",
    detection_interval_minutes: 1440,
    sources: ["ml/runs/20261013-093050_selection_s42/operating_point.json"],
  },
  "GET /api/agents/A10001/activity": {
    agent_id: "A10001", run_id: "RUN1", first_day: "2026-08-01", last_day: "2026-08-03",
    days: [
      { date: "2026-08-01", activations: 5, completed: 4, duplicate_evidence: true },
      { date: "2026-08-02", activations: 0, completed: 0, duplicate_evidence: false },
      { date: "2026-08-03", activations: 2, completed: 2, duplicate_evidence: false },
    ],
    hours: Array.from({ length: 24 }, (_, hour) => ({ hour, activations: hour === 9 ? 4 : hour === 14 ? 3 : 0 })),
    totals: { activations: 7, completed: 6 }, note: "Days and hours are as recorded in the data.",
  },
  "GET /api/customers/c_00112233445566778899aabb": {
    customer: { customer_ref: "c_00112233445566778899aabb", customer_id: "CUST10000001" }, run_id: "RUN1",
    agent_count: 2, client_count: 1, client_ids: ["CL01"], first_seen: "2026-08-02T10:00:00", last_seen: "2026-08-05T11:00:00",
    agents: [
      { agent_id: "A10001", flag_source: "ML", risk_band: "high", activations: 1, client_ids: ["CL01"], first_seen: "2026-08-02T10:00:00", last_seen: "2026-08-02T10:00:00" },
      { agent_id: "A20002", flag_source: "Rule", risk_band: "review", activations: 1, client_ids: ["CL01"], first_seen: "2026-08-05T11:00:00", last_seen: "2026-08-05T11:00:00" },
    ],
    activations_total: 2, activations_limit: 200,
    activations: [
      { timestamp: "2026-08-05T11:00:00", agent_id: "A20002", client_id: "CL01", status: "completed" },
      { timestamp: "2026-08-02T10:00:00", agent_id: "A10001", client_id: "CL01", status: "completed" },
    ],
  },
  "GET /api/threat-intelligence/summary": {
    agents_scored: 1000, flagged: 145, flagged_rate: 0.145, rule_flagged: 102,
    flag_sources: { ML: 72, Rule: 29, Both: 73, None: 826 },
    risk_bands: { high: 145, review: 89, low: 766 },
  },
  "GET /api/detection-runs/latest": {
    run: {
      run_id: "RUN1", trigger: "manual", status: "succeeded", model_version: "lof_v3_4f", started_at: "2026-10-13T15:07:08",
      finished_at: "2026-10-13T15:07:16", agents_scored: 1000, flagged_count: 145, error: null,
    },
  },
  "GET /api/admin/accounts": {
    count: 1, accounts: [{ admin_id: "ADM_ADMIN_01", username: "admin_01", role: "admin", is_active: true }],
  },
  "GET /api/agent-scores": {
    total: 3, count: 3, offset: 0, threshold: 1.444799,
    scores: [
      { agent_id: "A35485", anomaly_score: 5.563827, score_percentile: 98.9, flag_source: "Both", risk_band: "high" },
      { agent_id: "A10001", anomaly_score: 3.2, score_percentile: 97.4, flag_source: "ML", risk_band: "high" },
      { agent_id: "A20002", anomaly_score: 1.35, score_percentile: 80.6, flag_source: "Rule", risk_band: "review" },
    ],
  },
};

export function reply(status, body) {
  return { status, body };
}

/**
 * Stubs fetch. routes maps "METHOD /path" (no query) to a body (200), a reply(status, body),
 * a function (request) => either, a Response (for files), or an Error to simulate a network failure.
 * Unknown routes are 404.
 */
export function mockApi(routes = {}) {
  const calls = [];
  const fetchMock = vi.fn(async (url, init = {}) => {
    const method = init.method || "GET";
    const path = String(url).split("?")[0];
    const request = { method, path, url: String(url), init, body: init.body ? JSON.parse(init.body) : undefined };
    calls.push(request);
    let route = routes[`${method} ${path}`] ?? FIXTURES[`${method} ${path}`];
    if (typeof route === "function") route = await route(request);
    if (route instanceof Error) throw route;
    if (route instanceof Response) return route;
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

/** The current router address, for checking that filters land in the query string. */
export function currentLocation() {
  return document.querySelector('[data-testid="location"]').textContent;
}

export function renderApp(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ColorModeProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ColorModeProvider>
      <LocationProbe />
    </MemoryRouter>,
  );
}
