// Audit log labels and display rules (docs/API.md, "Audit log").

export const AUDIT_CATEGORIES = {
  authentication: "Sign-in",
  authorization: "Access",
  review: "Review",
  admin: "Accounts",
  report: "Reports",
  ai_decision: "Detection",
};

export const AUDIT_ACTIONS = {
  login: "Signed in",
  login_failure: "Sign-in failed",
  logout: "Signed out",
  access_denied: "Access denied",
  propose_decision: "Decision proposed",
  withdraw_decision: "Proposal withdrawn",
  agree_decision: "Proposal agreed",
  overrule_decision: "Proposal overruled",
  correct_decision: "Decision corrected",
  review_refused: "Review action refused",
  customer_viewed: "Customer viewed",
  // Before issue #28 an agreement was called a confirmation; older entries keep that action.
  confirm_decision: "Decision confirmed (agreed)",
  role_change: "Role changed",
  account_deactivated: "Account deactivated",
  account_reactivated: "Account reactivated",
  password_reset: "Password reset (local recovery)",
  account_created: "First admin created",
  report_download: "Report downloaded",
  ai_detection_run: "Detection run",
  ai_flag: "Flag changed",
};

// Categories whose entries can name an agent: everything under Review and Detection. Sign-in, Reports and
// Accounts entries never do, so the Agent column and field are left out for them.
const AGENT_CATEGORIES = ["review", "ai_decision"];

/** Whether entries of this category (or of all categories, "") can name an agent. */
export function categoryHasAgents(category) {
  return !category || AGENT_CATEGORIES.includes(category);
}

/** Whether the event was a refusal or failure. Derived for display only; the API has no outcome field. */
export function auditResult(entry) {
  if (entry.action === "access_denied" || entry.action === "review_refused") return "refused";
  if (entry.action === "login_failure") return "failed";
  if (entry.action === "ai_detection_run" && entry.details?.status === "failed") return "failed";
  return "ok";
}

// Defence in depth: the server never stores these, and the client never shows a key that looks like one.
const SECRET_KEY = /pass(word)?|hash|secret|token|cookie|session/i;

/** Detail entries safe to show: [key, value] pairs, with anything that looks like a secret left out. */
export function safeDetails(details) {
  if (!details || typeof details !== "object") return [];
  return Object.entries(details).filter(([key]) => !SECRET_KEY.test(key));
}
