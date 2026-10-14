// Client-side visibility only: the server checks every request again.
export const FRAUD_ANALYST = "fraud_analyst";
export const COMPLIANCE_OFFICER = "compliance_officer";
export const ADMIN = "admin";

export const ROLE_LABELS = {
  [FRAUD_ANALYST]: "Fraud analyst",
  [COMPLIANCE_OFFICER]: "Compliance officer",
  [ADMIN]: "Admin",
};

const REVIEWERS = [FRAUD_ANALYST, COMPLIANCE_OFFICER];
const EVERYONE = [FRAUD_ANALYST, COMPLIANCE_OFFICER, ADMIN];

// In menu order. menu: false pages are reached from another page.
export const PAGES = [
  { key: "overview", path: "/", label: "Overview", roles: EVERYONE, menu: true },
  { key: "flagged", path: "/flagged", label: "Flagged agents", roles: REVIEWERS, menu: true },
  { key: "allAgents", path: "/all-agents", label: "All agents", roles: REVIEWERS, menu: true },
  { key: "agentDetail", path: "/agents/:agentId", label: "Agent detail", roles: REVIEWERS, menu: false },
  { key: "threat", path: "/threat-intelligence", label: "Threat intelligence", roles: EVERYONE, menu: true },
  { key: "analytics", path: "/analytics", label: "Analytics", roles: EVERYONE, menu: true },
  { key: "history", path: "/history", label: "Review history", roles: REVIEWERS, menu: true },
  { key: "confirm", path: "/review/confirm", label: "Confirm queue", roles: [COMPLIANCE_OFFICER], menu: true },
  { key: "audit", path: "/audit-log", label: "Audit log", roles: [COMPLIANCE_OFFICER, ADMIN], menu: true },
  { key: "reports", path: "/reports", label: "Reports", roles: [ADMIN], menu: true },
  { key: "accounts", path: "/accounts", label: "Accounts", roles: [ADMIN], menu: true },
];

export function menuFor(role) {
  return PAGES.filter((page) => page.menu && page.roles.includes(role));
}

export function canAccess(role, key) {
  return Boolean(PAGES.find((page) => page.key === key)?.roles.includes(role));
}
