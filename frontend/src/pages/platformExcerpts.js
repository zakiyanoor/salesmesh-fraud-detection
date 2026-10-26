// Example rows for the landing page's product excerpts (issue #28). The agent IDs are invented, in the app's
// format; the labels, event names and roles are the product's own. No scores, counts of accuracy or names.
import { COMPLIANCE_OFFICER, FRAUD_ANALYST, ADMIN, ROLE_LABELS } from "../auth/roles";

/** Detection: the top of the Flagged agents list. Values are the API's (flag_source ML, Rule, Both; risk_band; review status). */
export const FLAGGED_TITLE = "Flagged agents";
export const FLAGGED_SUBTITLE = "Agents the model or the duplicate rule flagged in the latest detection run";
export const RANKED_AGENTS = [
  { rank: 1, agent_id: "A10482", region: "Nairobi", risk_band: "high", flag_source: "Both", review: "agreed" },
  { rank: 2, agent_id: "A13017", region: "Mombasa", risk_band: "high", flag_source: "ML", review: "pending_confirmation" },
  { rank: 3, agent_id: "A11265", region: "Kisumu", risk_band: "review", flag_source: "Rule", review: "pending_confirmation" },
  { rank: 4, agent_id: "A14530", region: "Nakuru", risk_band: "review", flag_source: "ML", review: null },
  { rank: 5, agent_id: "A12904", region: "Kiambu", risk_band: "review", flag_source: "Rule", review: null },
  { rank: 6, agent_id: "A15338", region: "Machakos", risk_band: "low", flag_source: "Rule", review: null },
  { rank: 7, agent_id: "A16071", region: "Nyeri", risk_band: "low", flag_source: "Rule", review: null },
  { rank: 8, agent_id: "A17219", region: "Kakamega", risk_band: "low", flag_source: "Rule", review: null },
];

/** Review: one proposal and its agreement, as the decision history shows them. */
export const REVIEW_STEPS = {
  outcome: "confirmed_fraud",
  proposedBy: ROLE_LABELS[FRAUD_ANALYST].toLowerCase(),
  agreedBy: ROLE_LABELS[COMPLIANCE_OFFICER].toLowerCase(),
};

/** Investigation: pairs in a ring candidate that share customers, and the counties of its members. */
export const RING_PAIRS = [
  { source: "A10482", target: "A12904", shared: 5 },
  { source: "A10482", target: "A15338", shared: 4 },
  { source: "A12904", target: "A15338", shared: 3 },
];
export const RING_COUNTIES = ["Nairobi", "Kiambu", "Machakos"];

/** Accountability: audit log entries, with the action exactly as the server records it. */
export const AUDIT_ROWS = [
  { time: "08:02", action: "login", role: ROLE_LABELS[FRAUD_ANALYST] },
  { time: "08:15", action: "customer_viewed", role: ROLE_LABELS[FRAUD_ANALYST] },
  { time: "09:40", action: "agree_decision", role: ROLE_LABELS[COMPLIANCE_OFFICER] },
  { time: "10:03", action: "access_denied", role: ROLE_LABELS[ADMIN] },
];
