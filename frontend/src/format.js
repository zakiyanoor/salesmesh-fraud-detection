// Display helpers shared by every page. Identity masking happens on the server; nothing here unmasks.

// The model cutoff is not kept here: pages read it from GET /api/model-info, which reads the frozen results.

export const FLAG_SOURCE_LABELS = {
  ML: "Model",
  Rule: "Rule only",
  Both: "Model and rule",
  None: "Not flagged",
};

export const OUTCOME_LABELS = { confirmed_fraud: "Confirmed fraud", legitimate: "Legitimate" };

// Issue #28: a proposal is open until the analyst withdraws it or a compliance officer agrees or overrules it.
export const STATUS_LABELS = {
  pending_confirmation: "Proposed", withdrawn: "Withdrawn", agreed: "Agreed", overruled: "Overruled",
};

export const REVIEW_STATUS_LABELS = { none: "Not reviewed", ...STATUS_LABELS };

/** What a Proposed decision waits for: the Proposed chip's tooltip and the decision history use the same words. */
export const WAITING_TEXT = "Waiting for a compliance officer to agree or overrule";

/** The four model inputs, in the order the model uses them. `key` is the field name in API payloads. */
export const FEATURES = [
  {
    key: "submission_frequency",
    label: "Submission frequency",
    digits: 0,
    help: "The most activations the agent submitted in any 24-hour window. A burst far above the usual count is unusual.",
  },
  {
    // The API keeps the older key time_of_day_dist for the v3 time_of_day_entropy.
    key: "time_of_day_dist",
    label: "Time-of-day entropy",
    digits: 3,
    help: "How evenly submissions spread over the hours of the day, from 0 (all in one hour) to 1 (spread evenly). Work packed into a few hours, or spread over unusual hours, stands out.",
  },
  {
    key: "customer_similarity",
    label: "Customer similarity",
    digits: 3,
    help: "How alike the agent's customer ID numbers are, as the share of matching digits between pairs. Made-up or sequential IDs look more alike than real ones.",
  },
  {
    key: "collusion_score",
    label: "Collusion score",
    digits: 3,
    help: "The share of the agent's customers that at least one other agent also activated. Honest agents rarely share customers.",
  },
];

/** Labels for the model's own feature names (as in top_features and reasons). */
export const MODEL_FEATURE_LABELS = {
  submission_frequency: "Submission frequency",
  time_of_day_entropy: "Time-of-day entropy",
  customer_similarity: "Customer similarity",
  collusion_score: "Collusion score",
};

export function formatPercent(share, digits = 1) {
  return share == null ? "—" : `${(share * 100).toFixed(digits)}%`;
}

/**
 * score_percentile (0-100, from the API) as a rank for tables: "Top X%", X = 100 - percentile rounded up
 * to a whole percent, at least 1. 99.9 -> "Top 1%", 92.0 -> "Top 8%", 51.5 -> "Top 49%".
 */
export function formatPercentile(percentile) {
  if (percentile == null || Number.isNaN(percentile)) return "—";
  // toFixed(1) first: 100 - 99.9 is 0.0999... in floating point.
  return `Top ${Math.max(1, Math.ceil(Number((100 - percentile).toFixed(1))))}%`;
}

export function formatNumber(value, digits = 0) {
  return value == null || Number.isNaN(value) ? "—" : Number(value).toFixed(digits);
}

// One date format for every page and the footer: day, short month, year and 24 hour time in Nairobi time,
// for example "13 Oct 2026, 17:26", so no page shows a month first date or the browser's own zone.
export const TIME_ZONE = "Africa/Nairobi";
const DATE_PARTS = { day: "numeric", month: "short", year: "numeric", timeZone: TIME_ZONE };
const DATE_FORMAT = new Intl.DateTimeFormat("en-GB", DATE_PARTS);
const DATE_TIME_FORMAT = new Intl.DateTimeFormat("en-GB", { ...DATE_PARTS, hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

// The API sends times without a zone. System events (detection runs, decisions, audit entries) are stored in
// UTC; activation data (records, registrations) is stored as recorded, in Nairobi time. `recorded: true` marks
// the second kind, so neither is shifted by the browser's own zone.
const NAIVE = /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?$/;

function toDate(value, recorded) {
  if (value == null || value === "") return null;
  let date;
  if (value instanceof Date) date = value;
  else if (typeof value === "string" && NAIVE.test(value)) {
    date = new Date(`${value.includes("T") ? value : `${value}T00:00:00`}${recorded ? "+03:00" : "Z"}`);
  } else date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** "13 Oct 2026" in Nairobi time, or "—". */
export function formatDate(value, { recorded = false } = {}) {
  const date = toDate(value, recorded);
  return date ? DATE_FORMAT.format(date) : "—";
}

/** "13 Oct 2026, 17:26" in Nairobi time (24 hour clock), or "—". */
export function formatDateTime(value, { recorded = false } = {}) {
  const date = toDate(value, recorded);
  return date ? DATE_TIME_FORMAT.format(date) : "—";
}

/** "Agnes Omondi" -> "A. O."; the API masks phone and national ID, the client shortens the name too. */
export function initials(fullName) {
  if (!fullName) return "—";
  return fullName
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => `${part[0].toUpperCase()}.`)
    .join(" ");
}

/** Latest decision per agent: { [agent_id]: decision }, from GET /api/review-decisions (newest first). */
export function latestDecisionByAgent(decisions = []) {
  const latest = {};
  for (const d of decisions) {
    if (d.agent_id && !latest[d.agent_id]) latest[d.agent_id] = d;
  }
  return latest;
}
