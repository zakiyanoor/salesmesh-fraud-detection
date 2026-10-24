// Review workflow wording and rules, shared by agent detail, the confirm queue and review history.
// A proposal has no effect until a compliance officer agrees or overrules it (issue #28), so the wording
// never calls a proposal saved, recorded or final.

export const NOTES_MAX = 1000;

export const PROPOSED_MESSAGE =
  "Decision proposed. It is waiting for a compliance officer to confirm it and has no effect until then.";

export const WITHDRAWN_MESSAGE = "Proposal withdrawn. You can propose again on this flag.";

export function correctedMessage(agentId, outcome) {
  return `Correction recorded for ${agentId}. The outcome in force is now ${outcome}; the history keeps the original decision.`;
}

/** The other outcome: what an overrule or a correction changes to. */
export function otherOutcome(outcome) {
  return outcome === "confirmed_fraud" ? "legitimate" : "confirmed_fraud";
}

export function closedMessage(agentId, status, outcomeLabel) {
  return `Proposal for ${agentId} ${status === "overruled" ? "overruled" : "agreed"}. The final outcome is ${outcomeLabel}.`;
}

export const NOTES_HINT =
  "Explain the decision in plain text. Runs of 7 or more digits, such as phone or ID numbers, are masked when saved.";

/** The same rules as the server (trimmed, 1 to 1000 characters); returns an error message or null. */
export function notesError(notes) {
  const trimmed = notes.trim();
  if (!trimmed) return "Notes are required.";
  if (trimmed.length > NOTES_MAX) return `Notes must be at most ${NOTES_MAX} characters (now ${trimmed.length}).`;
  return null;
}
