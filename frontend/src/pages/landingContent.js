// Landing page copy (issue #28), kept apart from the component so tests can check it.

export const SIGN_IN_PATH = "/sign-in";

// Checked against ml/feature_engineering.py and ml/baselines.py (duplicate_activation_counts).
export const SIGNALS = [
  ["Busiest 24 hours", "The most activations an agent submitted in any 24 hours in a row. A sudden burst far above what agents usually manage stands out."],
  ["Time of day", "Whether an agent's activations are spread across the day or packed into a few hours."],
  ["Customer ID patterns", "How alike the customer IDs an agent enters are, character by character. Near-identical or sequential IDs, such as numbers counting up, stand out."],
  ["Shared customers", "The share of an agent's customers that at least one other agent also activated. Honest agents rarely share many."],
];
export const DUPLICATE_RULE = [
  "Duplicate activations",
  "The same customer activated for the same client by more than one agent, or by the same agent again after an earlier activation for that client had already completed. A retry after a failed activation does not count.",
];

export const STEPS = [
  ["A detection run", "Detection runs on a schedule, not live. Each run scores every agent and applies the rule."],
  ["A flag with its evidence", "An agent flagged by the model, the rule or both appears for review with the signals and the duplicate records behind it."],
  ["A fraud analyst proposes", "The analyst proposes an outcome, fraud or legitimate, with a note. They can withdraw it until it is decided."],
  ["A different person decides", "A compliance officer, never the person who proposed, agrees or overrules the proposed outcome."],
  ["Corrected, never edited", "A decision is never edited. If it was wrong, a compliance officer records a correction beside the original, with a note."],
];

// From the role matrix in docs/API.md, checked against the role checks in backend/src/api.py.
export const ROLES = ["Fraud analyst", "Compliance officer", "Administrator"];
export const PERMISSIONS = [
  ["See agents, scores, evidence and run status", [true, true, true]],
  ["Open the threat intelligence views", [true, true, true]],
  ["Propose an outcome for a flagged agent", [true, false, false]],
  ["Withdraw their own open proposal", [true, false, false]],
  ["Agree with or overrule someone else's proposal", [false, true, false]],
  ["Correct a final decision", [false, true, false]],
  ["Open a customer from the duplicate evidence", [true, true, false]],
  ["Read the audit log", [false, true, true]],
  ["Download reports and manage accounts", [false, false, true]],
];

// Each point is true in the code; docs/FRONTEND.md names the file that proves it.
export const SECURITY = [
  ["role-based-access", "Role based access", "The server checks the account's role on every request and refuses anything outside it, whatever the screen shows."],
  ["two-person-review", "Two person review of every decision", "The person who proposed an outcome can never agree with, overrule or correct it, even after a change of role."],
  ["audit-log", "Append only audit log", "Sign-ins, refused requests, review actions, account changes and detection runs are recorded, and the database refuses to change or delete them."],
  ["secure-sessions", "Secure sessions", "A session lives in a cookie that page scripts cannot read, is sent only over secure connections in production, expires, and is checked against the account on every request."],
];

export const FOOTER = [
  ["Detection", [["The four signals", "signals"], ["The duplicate activation rule", "duplicate-rule"], ["How a flag is made", "how-a-flag-is-made"]]],
  ["Review", [["From flag to decision", "flag-to-decision"], ["Who can do what", "who-can-do-what"], ["Corrections and the audit trail", "corrections"]]],
  ["Security", [["Role based access", "role-based-access"], ["Two person review", "two-person-review"], ["Append only audit log", "audit-log"], ["Secure sessions", "secure-sessions"]]],
];
