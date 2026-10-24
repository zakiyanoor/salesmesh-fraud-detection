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
# A proposal waiting longer than this is overdue. It is only shown; nothing decides it.
OVERDUE_HOURS = 72


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


def is_overdue(decision, now=None):
    """An open proposal waiting more than OVERDUE_HOURS, by the server's clock (UTC)."""
    now = now or datetime.utcnow()
    return (decision.status == DECISION_PENDING
            and (now - decision.decision_timestamp).total_seconds() > OVERDUE_HOURS * 3600)


def decision_payload(decision, agent_id=None, still_flagged=None, now=None):
    """A decision with its closing fields, corrections and the outcome in force, for the API."""
    return {
        "decision_id": decision.decision_id,
        "flag_id": decision.flag_id,
        "agent_id": agent_id,
        "reviewer_id": decision.reviewer_id,
        "decision_outcome": decision.decision_outcome,
        "decision_timestamp": decision.decision_timestamp.isoformat(),
        "notes": decision.notes,
        "run_id": decision.run_id,
        "flag_source": decision.flag_source,
        "status": decision.status,
        "final_outcome": decision.final_outcome,
        "closed_by": decision.closed_by,
        "closed_at": decision.closed_at.isoformat() if decision.closed_at else None,
        "close_note": decision.close_note,
        "corrections": [{
            "correction_id": c.correction_id, "previous_outcome": c.previous_outcome, "new_outcome": c.new_outcome,
            "corrected_by": c.corrected_by, "corrected_at": c.corrected_at.isoformat(), "note": c.note,
        } for c in decision.corrections],
        "effective_outcome": effective_outcome(decision),
        "overdue": is_overdue(decision, now),
        "still_flagged": still_flagged,
    }


def review_block(db_session, vector, flag, run=None):
    """Agent detail (issue #28): whether the agent's flag can be reviewed now, and its open and final decisions."""
    if vector is None or flag is None:
        return {"reviewable": False, "reason": "This agent has no flag to review", "flag_id": None,
                "flag_source": None, "open_decision_id": None, "open_proposed_by": None, "final_decision_id": None,
                "effective_outcome": None}
    source, reason = eligibility(db_session, vector, run)
    pending, final = open_and_final(db_session, flag.flag_id)
    if reason is None and pending is not None:
        reason = "This flag already has an open proposal"
    elif reason is None and final is not None:
        reason = "This flag already has a final decision; only a compliance officer's correction can change it"
    return {"reviewable": reason is None, "reason": reason, "flag_id": flag.flag_id, "flag_source": source,
            "open_decision_id": pending.decision_id if pending else None,
            "open_proposed_by": pending.reviewer_id if pending else None,
            "final_decision_id": final.decision_id if final else None,
            "effective_outcome": effective_outcome(final) if final else None}


def review_stats(db_session, now=None):
    """
    Counts for analytics. overrule_rate = overruled / (agreed + overruled): the share of officer decisions
    that overruled the analyst; withdrawn and open proposals are left out, corrections are counted
    separately, and the rate is None until an officer has decided something.
    """
    decisions = db_session.query(ReviewDecision).all()
    counts = {status: sum(d.status == status for d in decisions) for status in
              (DECISION_PENDING, DECISION_WITHDRAWN, DECISION_AGREED, DECISION_OVERRULED)}
    decided = counts[DECISION_AGREED] + counts[DECISION_OVERRULED]
    return {
        "proposals": len(decisions),
        "open": counts[DECISION_PENDING],
        "overdue": sum(is_overdue(d, now) for d in decisions),
        "withdrawn": counts[DECISION_WITHDRAWN],
        "agreed": counts[DECISION_AGREED],
        "overruled": counts[DECISION_OVERRULED],
        "corrections": db_session.query(ReviewCorrection).count(),
        "overrule_rate": round(counts[DECISION_OVERRULED] / decided, 4) if decided else None,
        "overdue_hours": OVERDUE_HOURS,
    }


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


__all__ = ["DECISION_OUTCOMES", "OVERDUE_HOURS", "ReviewError", "close", "correct", "decision_payload",
           "effective_outcome", "eligibility", "is_overdue", "open_and_final", "propose", "review_block",
           "review_stats", "withdraw"]
