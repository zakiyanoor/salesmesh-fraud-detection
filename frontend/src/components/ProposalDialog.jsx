import NoteDialog from "./NoteDialog";
import { OUTCOME_LABELS, formatDateTime } from "../format";
import { closedMessage, otherOutcome } from "../review";
import { api } from "../api";

/**
 * Agree with or overrule an analyst's proposal, used by the confirm queue and agent detail. kind is "agree"
 * (note optional) or "overrule" (note required, the other outcome preset). onFinish(message, severity) runs
 * when the proposal is closed, or with "info" when someone else already decided or withdrew it. A refusal
 * because this officer made the proposal is shown in the dialog.
 */
export default function ProposalDialog({ kind, decision, onClose, onFinish }) {
  const summary = `Agent ${decision.agent_id}: ${decision.reviewer_id} proposed ${OUTCOME_LABELS[decision.decision_outcome]} on ${formatDateTime(decision.decision_timestamp)}. Notes: ${decision.notes || "none"}.`;

  const submit = async (send) => {
    try {
      const closed = await send();
      onFinish(closedMessage(decision.agent_id, closed.status, OUTCOME_LABELS[closed.final_outcome], closed.deactivation_requested), "success");
    } catch (err) {
      if (err.status === 409) {
        onFinish(`The proposal for ${decision.agent_id} was already withdrawn or decided by someone else.`, "info");
        return;
      }
      throw err.status === 403 ? new Error(`${err.message}. Another compliance officer must decide it.`) : err;
    }
  };

  if (kind === "agree") {
    return (
      <NoteDialog
        id="agree"
        title="Agree with this proposal?"
        description={`${summary} Once you agree, the outcome is final; only a correction can change it.`}
        submitLabel="Agree"
        onClose={onClose}
        onSubmit={({ notes }) => submit(() => api.agreeDecision({ decisionId: decision.decision_id, notes }))}
      />
    );
  }
  return (
    <NoteDialog
      id="overrule"
      title="Overrule this proposal?"
      description={`${summary} Choose the final outcome and explain why you disagree.`}
      outcome={otherOutcome(decision.decision_outcome)}
      noteRequired
      submitLabel="Overrule"
      onClose={onClose}
      onSubmit={({ outcome, notes }) => submit(() => api.overruleDecision({ decisionId: decision.decision_id, finalOutcome: outcome, notes }))}
    />
  );
}
