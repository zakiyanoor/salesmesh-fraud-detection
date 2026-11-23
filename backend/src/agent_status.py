"""
Agent deactivation: an internal application status for an agent, kept in agent_deactivations.

When a compliance officer closes a review decision with the final outcome confirmed_fraud (agreeing with a
fraud proposal, or overruling a legitimate one), a request with status pending_deactivation is opened for
that decision. An administrator then confirms it, which sets the status to deactivated. Nothing is deleted,
and agents.account_status (loaded from the data files) is never changed.

A correction to legitimate cancels a request that is still pending; a correction back to confirmed_fraud
opens it again. A deactivated agent is never reactivated automatically, and a detection run never touches
this table.

Each function changes the session and returns what changed; the caller adds the audit entry and commits
both together. A broken rule raises DeactivationError with the HTTP status to return.
"""

import uuid
from datetime import datetime

from src.db import (
    DEACTIVATION_CANCELLED, DEACTIVATION_DONE, DEACTIVATION_PENDING, AgentDeactivation, ReviewDecision,
)
from src.review import effective_outcome

CONFIRMED_FRAUD = "confirmed_fraud"
ACTIVE = "active"

REQUESTED = "deactivation_requested"
CANCELLED = "deactivation_cancelled"
DEACTIVATED = "agent_deactivated"


class DeactivationError(Exception):
    """A deactivation rule was broken; status is the HTTP status to return (404 or 409)."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def agent_state(db_session, agent_id):
    """active, pending_deactivation or deactivated: deactivated wins over a pending request."""
    statuses = {s for (s,) in db_session.query(AgentDeactivation.status)
                .filter(AgentDeactivation.agent_id == agent_id)}
    if DEACTIVATION_DONE in statuses:
        return DEACTIVATION_DONE
    if DEACTIVATION_PENDING in statuses:
        return DEACTIVATION_PENDING
    return ACTIVE


def _open_elsewhere(db_session, agent_id, decision_id):
    """True when another decision already holds a pending or completed request for the agent."""
    return db_session.query(AgentDeactivation.deactivation_id).filter(
        AgentDeactivation.agent_id == agent_id,
        AgentDeactivation.decision_id != decision_id,
        AgentDeactivation.status.in_((DEACTIVATION_PENDING, DEACTIVATION_DONE)),
    ).first() is not None


def apply_outcome(db_session, decision_id, agent_id, outcome, actor_id, note=None):
    """
    Brings the decision's request in line with the outcome now in force (after an agreement, an overrule or
    a correction). Returns (request, audit action) when something changed, else (None, None).
    """
    if agent_id is None:
        return None, None
    request = (db_session.query(AgentDeactivation).filter(AgentDeactivation.decision_id == decision_id)
               .with_for_update().first())
    now = datetime.utcnow()
    if outcome == CONFIRMED_FRAUD:
        if request is not None and request.status != DEACTIVATION_CANCELLED:
            return None, None
        if _open_elsewhere(db_session, agent_id, decision_id):
            return None, None
        if request is None:
            request = AgentDeactivation(
                deactivation_id=f"DA{uuid.uuid4().hex[:8]}", agent_id=agent_id, decision_id=decision_id,
                requested_by=actor_id, requested_at=now, status=DEACTIVATION_PENDING, note=note,
            )
            db_session.add(request)
        else:
            request.status, request.requested_by, request.requested_at = DEACTIVATION_PENDING, actor_id, now
            request.actioned_by, request.actioned_at, request.note = None, None, note
        return request, REQUESTED
    if request is not None and request.status == DEACTIVATION_PENDING:
        request.status, request.actioned_by, request.actioned_at, request.note = (
            DEACTIVATION_CANCELLED, actor_id, now, note)
        return request, CANCELLED
    return None, None


def confirm(db_session, admin_id, deactivation_id):
    """Marks a pending request deactivated, once. Deletes nothing."""
    request = (db_session.query(AgentDeactivation).filter(AgentDeactivation.deactivation_id == deactivation_id)
               .with_for_update().first())
    if request is None:
        raise DeactivationError(404, "Deactivation request not found")
    if request.status != DEACTIVATION_PENDING:
        raise DeactivationError(409, f"Deactivation request {deactivation_id} is already {request.status}")
    request.status, request.actioned_by, request.actioned_at = DEACTIVATION_DONE, admin_id, datetime.utcnow()
    return request


def request_payload(request, decision=None):
    decision = decision or request.decision
    return {
        "deactivation_id": request.deactivation_id,
        "agent_id": request.agent_id,
        "decision_id": request.decision_id,
        "decision_status": decision.status if decision else None,
        "final_outcome": decision.final_outcome if decision else None,
        "effective_outcome": effective_outcome(decision) if decision else None,
        "requested_by": request.requested_by,
        "requested_at": request.requested_at.isoformat(),
        "status": request.status,
        "actioned_by": request.actioned_by,
        "actioned_at": request.actioned_at.isoformat() if request.actioned_at else None,
        "note": request.note,
    }


def list_requests(db_session):
    """Every request, pending first, then newest first."""
    rows = (db_session.query(AgentDeactivation, ReviewDecision)
            .join(ReviewDecision, ReviewDecision.decision_id == AgentDeactivation.decision_id)
            .order_by((AgentDeactivation.status != DEACTIVATION_PENDING), AgentDeactivation.requested_at.desc())
            .all())
    return [request_payload(r, d) for r, d in rows]


__all__ = ["ACTIVE", "CANCELLED", "DEACTIVATED", "DeactivationError", "REQUESTED", "agent_state", "apply_outcome",
           "confirm", "list_requests", "request_payload"]
