// Every backend call goes through request() or download(); endpoints are documented in docs/API.md.
const API_BASE = (import.meta.env.VITE_API_BASE || "/api").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(status, message, body = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

const DEFAULT_MESSAGES = {
  0: "Could not reach the server. Check your connection and try again.",
  401: "Your session has ended. Please sign in again.",
  403: "You do not have access to this.",
  404: "Not found.",
  409: "This was already changed by someone else. Reload and try again.",
  429: "Too many attempts. Wait a minute and try again.",
};

function defaultMessage(status) {
  return DEFAULT_MESSAGES[status] || (status >= 500 ? "The server had a problem. Try again." : `Request failed (${status}).`);
}

// Only a 401 ends the session; the auth provider registers what that does.
let unauthorizedHandler = null;

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
  return () => {
    if (unauthorizedHandler === handler) unauthorizedHandler = null;
  };
}

function queryString(params) {
  const entries = Object.entries(params || {}).filter(([, v]) => v !== undefined && v !== null && v !== "");
  const text = new URLSearchParams(entries).toString();
  return text ? `?${text}` : "";
}

async function send(path, { method = "GET", body, params, handleUnauthorized = true } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}${queryString(params)}`, {
      method,
      credentials: "include",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, defaultMessage(0));
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const error = new ApiError(response.status, data?.error || defaultMessage(response.status), data);
    if (response.status === 401 && handleUnauthorized && unauthorizedHandler) unauthorizedHandler(error);
    throw error;
  }
  return response;
}

export async function request(path, options) {
  const response = await send(path, options);
  return response.json().catch(() => ({}));
}

/** A file endpoint: { blob, filename } with the server's file name. */
export async function download(path, params) {
  const response = await send(path, { params });
  const match = /filename="?([^";]+)"?/.exec(response.headers.get("Content-Disposition") || "");
  return { blob: await response.blob(), filename: match ? match[1] : path.split("/").pop() };
}

const id = encodeURIComponent;

export const api = {
  // Session. A 401 here means "not signed in" or "wrong password", not "session ended".
  login: (username, password) =>
    request("/login", { method: "POST", body: { username, password }, handleUnauthorized: false }),
  logout: () => request("/logout", { method: "POST", handleUnauthorized: false }),
  me: () => request("/me", { handleUnauthorized: false }),
  health: () => request("/health"),

  // Agents and scores
  getFlaggedAgents: () => request("/flagged-agents"),
  getAllAgents: () => request("/all-agents"),
  // Customer view (issue #28): by reference, so the customer ID is never in a URL; every open is audited.
  getCustomer: ({ customerRef, fromAgent }) => request(`/customers/${id(customerRef)}`, { params: { from_agent: fromAgent } }),
  getAgentDetail: (agentId) => request(`/agents/${id(agentId)}`),
  getAgentActivity: (agentId) => request(`/agents/${id(agentId)}/activity`),
  getAgentScores: ({ flagSource, limit, offset } = {}) =>
    request("/agent-scores", { params: { flag_source: flagSource, limit, offset } }),
  getAnalytics: () => request("/analytics"),
  getClients: () => request("/clients"),
  getLatestDetectionRun: () => request("/detection-runs/latest"),

  // Threat intelligence
  getThreatSummary: () => request("/threat-intelligence/summary"),
  getThreatByRegion: () => request("/threat-intelligence/by-region"),
  getThreatByClient: () => request("/threat-intelligence/by-client"),
  getThreatByCategory: () => request("/threat-intelligence/by-category"),
  getThreatTimeline: () => request("/threat-intelligence/timeline"),
  getCustomerSharing: () => request("/threat-intelligence/customer-sharing"),
  getRingCandidates: () => request("/threat-intelligence/ring-candidates"),

  // Review decisions (issue #28). Analyst: propose, withdraw. Compliance officer: agree, overrule, correct.
  proposeDecision: ({ flagId, decisionOutcome, notes }) =>
    request("/review-decisions", {
      method: "POST",
      body: { flag_id: flagId, decision_outcome: decisionOutcome, notes },
    }),
  withdrawDecision: ({ decisionId, notes }) =>
    request(`/review-decisions/${id(decisionId)}/withdraw`, { method: "POST", body: { notes } }),
  agreeDecision: ({ decisionId, notes }) =>
    request(`/review-decisions/${id(decisionId)}/agree`, { method: "POST", body: notes ? { notes } : {} }),
  overruleDecision: ({ decisionId, finalOutcome, notes }) =>
    request(`/review-decisions/${id(decisionId)}/overrule`, { method: "POST", body: { final_outcome: finalOutcome, notes } }),
  correctDecision: ({ decisionId, newOutcome, expectedCurrentOutcome, notes }) =>
    request(`/review-decisions/${id(decisionId)}/corrections`, {
      method: "POST",
      body: { new_outcome: newOutcome, expected_current_outcome: expectedCurrentOutcome, notes },
    }),
  getReviewDecisions: () => request("/review-decisions"),

  // Audit log: filters category, actor, agent_id, date_from, date_to; paging limit, offset
  getAuditLog: (filters) => request("/audit-log", { params: filters }),

  // Reports (admin)
  downloadFlaggedAgentsCsv: () => download("/reports/flagged-agents.csv"),
  downloadAuditLogCsv: (filters) => download("/reports/audit-log.csv", filters),
  downloadDetectionSummaryPdf: () => download("/reports/detection-summary.pdf"),

  // Accounts (admin)
  listAccounts: () => request("/admin/accounts"),
  changeAccountRole: (adminId, role) => request(`/admin/accounts/${id(adminId)}/role`, { method: "PATCH", body: { role } }),
  deactivateAccount: (adminId) => request(`/admin/accounts/${id(adminId)}/deactivate`, { method: "POST" }),
  reactivateAccount: (adminId) => request(`/admin/accounts/${id(adminId)}/reactivate`, { method: "POST" }),
};
