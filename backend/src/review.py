"""
Review workflow (issue #28).

A fraud analyst proposes an outcome for a flagged agent (flag_source ML, Rule
or Both in the latest successful run), with a note. A flag has at most one
open proposal, and none once it has a final decision. The analyst may withdraw
their own open proposal; a compliance officer other than the proposer agrees
or overrules it. A closed decision is never changed: a correction is a new
review_corrections row. Nothing here changes a score, a flag or a detection
run, and nothing closes a proposal because of time.

Each function checks the rules, changes the session and returns the decision;
the caller adds the audit entry and commits both together. A broken rule
raises ReviewError with the HTTP status to return.
"""

from datetime import datetime
import uuid

from sqlalchemy import func

from src import threat_intel
from src.db import (
    DECISION_AGREED, DECISION_FINAL, DECISION_OUTCOMES, DECISION_OVERRULED, DECISION_PENDING, DECISION_WITHDRAWN,
    AgentScore, FeatureVector, FraudFlag, ReviewCorrection, ReviewDecision,
)

REVIEWABLE_SOURCES = ("ML", "Rule", "Both")


class ReviewError(Exception):
    """A review rule was broken; status is the HTTP status to return (403, 404 or 409)."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def flag_and_agent(db_session, flag_id, lock=False):
    """(flag, vector) for a flag_id, or ReviewError 404. lock=True holds the flag row until commit."""
    query = db_session.query(FraudFlag).filter(FraudFlag.flag_id == flag_id)
    flag = (query.with_for_update() if lock else query).first()
    vector = db_session.get(FeatureVector, flag.vector_id) if flag else None
    if flag is None or vector is None:
        raise ReviewError(404, "Fraud flag not found")
    return flag, vector


def eligibility(db_session, vector, run=None):
    """(flag_source, None) when the flag can be reviewed, else (flag_source or None, reason)."""
    run = run or threat_intel.latest_run(db_session)
    if run is None:
        return None, "No successful detection run yet"
    newest = (db_session.query(func.max(FeatureVector.analysis_period))
              .filter(FeatureVector.agent_id == vector.agent_id).scalar())
    if vector.analysis_period != newest:
        return None, f"This flag is from an earlier analysis period ({vector.analysis_period})"
    score = (db_session.query(AgentScore)
             .filter(AgentScore.run_id == run.run_id, AgentScore.agent_id == vector.agent_id).first())
    source = score.flag_source if score else None
    if source not in REVIEWABLE_SOURCES:
        return source, "This agent is not flagged in the latest detection run"
    return source, None


def open_and_final(db_session, flag_id):
    """(the open proposal or None, the newest final decision or None) for a flag."""
    decisions = (db_session.query(ReviewDecision).filter(ReviewDecision.flag_id == flag_id)
                 .order_by(ReviewDecision.decision_timestamp).all())
    pending = next((d for d in decisions if d.status == DECISION_PENDING), None)
    final = [d for d in decisions if d.status in DECISION_FINAL]
    return pending, (max(final, key=lambda d: (d.closed_at or d.decision_timestamp)) if final else None)


def effective_outcome(decision):
    """The outcome in force: the newest correction, else the final outcome (None while open or withdrawn)."""
    if decision.status not in DECISION_FINAL:
        return None
    return decision.corrections[-1].new_outcome if decision.corrections else decision.final_outcome


def locked_decision(db_session, decision_id):
    decision = (db_session.query(ReviewDecision).filter(ReviewDecision.decision_id == decision_id)
                .with_for_update().first())
    if decision is None:
        raise ReviewError(404, "Review decision not found")
    return decision


def require_open(decision):
    if decision.status != DECISION_PENDING:
        raise ReviewError(409, f"Decision {decision.decision_id} is already {decision.status}")


def propose(db_session, analyst_id, flag_id, outcome, notes):
    flag, vector = flag_and_agent(db_session, flag_id, lock=True)
    run = threat_intel.latest_run(db_session)
    source, reason = eligibility(db_session, vector, run)
    if reason:
        raise ReviewError(409, reason)
    pending, final = open_and_final(db_session, flag_id)
    if pending is not None:
        raise ReviewError(409, f"This flag already has an open proposal ({pending.decision_id})")
    if final is not None:
        raise ReviewError(409, f"This flag already has a final decision ({final.decision_id}); "
                               "only a compliance officer's correction can change it")
    decision = ReviewDecision(
        decision_id=f"RD{uuid.uuid4().hex[:8]}", flag_id=flag_id, reviewer_id=analyst_id, decision_outcome=outcome,
        decision_timestamp=datetime.utcnow(), status=DECISION_PENDING, notes=notes, run_id=run.run_id,
        flag_source=source,
    )
    db_session.add(decision)
    return decision, vector.agent_id


def withdraw(db_session, analyst_id, decision_id, note):
    decision = locked_decision(db_session, decision_id)
    if decision.reviewer_id != analyst_id:
        raise ReviewError(403, "Only the analyst who proposed a decision can withdraw it")
    require_open(decision)
    decision.status, decision.closed_by, decision.closed_at = DECISION_WITHDRAWN, analyst_id, datetime.utcnow()
    decision.close_note = note
    return decision


def close(db_session, officer_id, decision_id, final_outcome, note):
    """Agree (final_outcome is the proposed outcome) or overrule (the other outcome); never by the proposer."""
    decision = locked_decision(db_session, decision_id)
    if decision.reviewer_id == officer_id:
        raise ReviewError(403, "A decision cannot be agreed or overruled by the admin who proposed it")
    require_open(decision)
    decision.status = DECISION_AGREED if final_outcome == decision.decision_outcome else DECISION_OVERRULED
    decision.final_outcome, decision.closed_by, decision.closed_at = final_outcome, officer_id, datetime.utcnow()
    decision.close_note = note
    return decision


def correct(db_session, officer_id, decision_id, new_outcome, expected_outcome, note):
    """
    A new review_corrections row for an agreed or overruled decision. expected_outcome is the outcome the
    officer saw; if another correction changed it meanwhile, the correction is refused.
    """
    decision = locked_decision(db_session, decision_id)
    if decision.reviewer_id == officer_id:
        raise ReviewError(403, "A decision cannot be corrected by the admin who proposed it")
    if decision.status not in DECISION_FINAL:
        raise ReviewError(409, f"Only an agreed or overruled decision can be corrected; this one is {decision.status}")
    current = effective_outcome(decision)
    if expected_outcome != current:
        raise ReviewError(409, f"The decision's outcome is now {current}, not {expected_outcome}; reload and try again")
    correction = ReviewCorrection(
        correction_id=f"RC{uuid.uuid4().hex[:8]}", decision_id=decision_id, corrected_by=officer_id,
        corrected_at=datetime.utcnow(), previous_outcome=current, new_outcome=new_outcome, note=note,
    )
    db_session.add(correction)
    return decision, correction


__all__ = ["DECISION_OUTCOMES", "ReviewError", "close", "correct", "effective_outcome", "eligibility",
           "open_and_final", "propose", "withdraw"]
