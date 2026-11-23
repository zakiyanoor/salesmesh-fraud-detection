"""Agent deactivation: requests opened by confirmed_fraud decisions and confirmed by an administrator."""

import json
from datetime import datetime

import pytest
from sqlalchemy import inspect, text

from src.db import AdminActionLog, AgentDeactivation, engine, get_session, migrate_schema
from tests.helpers import ADMIN, ANALYST, COMPLIANCE, login, reviewable_flag

FRAUD, LEGITIMATE = "confirmed_fraud", "legitimate"
LIST = "/api/admin/agent-deactivations"


def as_role(client, account):
    client.post("/api/logout")
    login(client, account)


def proposed(client, outcome=FRAUD, skip=0):
    """The analyst proposes on a fresh flag, then the officer signs in; returns (decision_id, agent_id)."""
    flag_id, agent_id = reviewable_flag(skip=skip)
    as_role(client, ANALYST)
    response = client.post("/api/review-decisions", json={
        "flag_id": flag_id, "decision_outcome": outcome, "notes": "Shares customers with two other agents."})
    assert response.status_code == 201, response.get_json()
    as_role(client, COMPLIANCE)
    return response.get_json()["decision_id"], agent_id


def agree(client, decision_id):
    response = client.post(f"/api/review-decisions/{decision_id}/agree")
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def overrule(client, decision_id, outcome):
    response = client.post(f"/api/review-decisions/{decision_id}/overrule",
                           json={"final_outcome": outcome, "notes": "The evidence points the other way."})
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def correct(client, decision_id, new, expected):
    response = client.post(f"/api/review-decisions/{decision_id}/corrections", json={
        "new_outcome": new, "expected_current_outcome": expected, "notes": "The customer list was from the wrong month."})
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def requests_for(decision_id):
    db_session = get_session()
    try:
        return db_session.query(AgentDeactivation).filter(AgentDeactivation.decision_id == decision_id).all()
    finally:
        db_session.close()


def request_for(decision_id):
    (row,) = requests_for(decision_id)
    return row


def audit_entries(action, **match):
    db_session = get_session()
    try:
        rows = (db_session.query(AdminActionLog).filter(AdminActionLog.action == action)
                .order_by(AdminActionLog.timestamp).all())
        entries = [(r, json.loads(r.details or "{}")) for r in rows]
        return [(r, d) for r, d in entries if all(d.get(k) == v for k, v in match.items())]
    finally:
        db_session.close()


def detail_state(client, agent_id):
    response = client.get(f"/api/agents/{agent_id}")
    assert response.status_code == 200, response.get_json()
    return response.get_json()["deactivation"]


def account_status(agent_id):
    with engine.connect() as conn:
        return conn.execute(text("SELECT account_status FROM agents WHERE agent_id = :a"), {"a": agent_id}).scalar()


def confirm(client, deactivation_id):
    return client.post(f"{LIST}/{deactivation_id}/confirm")


# --- Schema ---

def test_the_table_exists_and_migrating_again_is_safe(database) -> None:
    migrate_schema()
    migrate_schema()
    columns = {c["name"] for c in inspect(engine).get_columns("agent_deactivations")}
    assert columns == {"deactivation_id", "agent_id", "decision_id", "requested_by", "requested_at", "status",
                       "actioned_by", "actioned_at", "note"}
    foreign = {fk["referred_table"] for fk in inspect(engine).get_foreign_keys("agent_deactivations")}
    assert {"review_decisions", "agents"} <= foreign


# --- Requests opened by the review outcome ---

def test_agreeing_a_fraud_proposal_opens_a_pending_request(client) -> None:
    decision_id, agent_id = proposed(client)
    assert detail_state(client, agent_id) == "active"
    body = agree(client, decision_id)
    assert (body["deactivation_requested"], body["deactivation"]) == (True, "pending_deactivation")
    row = request_for(decision_id)
    assert (row.agent_id, row.status, row.requested_by, row.actioned_by) == (
        agent_id, "pending_deactivation", COMPLIANCE["admin_id"], None)
    assert detail_state(client, agent_id) == "pending_deactivation"
    (entry, details), = audit_entries("deactivation_requested", decision_id=decision_id)
    assert (entry.admin_id, entry.category, entry.target_agent_id) == (COMPLIANCE["admin_id"], "review", agent_id)
    assert details["deactivation_id"] == row.deactivation_id


def test_overruling_a_legitimate_proposal_to_fraud_opens_a_request(client) -> None:
    decision_id, agent_id = proposed(client, outcome=LEGITIMATE)
    body = overrule(client, decision_id, FRAUD)
    assert body["deactivation_requested"] is True
    assert request_for(decision_id).status == "pending_deactivation"
    assert len(audit_entries("deactivation_requested", decision_id=decision_id)) == 1


@pytest.mark.parametrize("proposal, close", [(LEGITIMATE, "agree"), (FRAUD, "overrule")])
def test_a_legitimate_final_outcome_opens_nothing(client, proposal, close) -> None:
    decision_id, agent_id = proposed(client, outcome=proposal)
    body = agree(client, decision_id) if close == "agree" else overrule(client, decision_id, LEGITIMATE)
    assert (body["final_outcome"], body["deactivation_requested"], body["deactivation"]) == (LEGITIMATE, False, "active")
    assert requests_for(decision_id) == []
    assert audit_entries("deactivation_requested", decision_id=decision_id) == []


# --- Administrator only ---

@pytest.mark.parametrize("account", [ANALYST, COMPLIANCE])
def test_only_the_administrator_can_list_or_confirm(client, account) -> None:
    decision_id, _ = proposed(client)
    agree(client, decision_id)
    deactivation_id = request_for(decision_id).deactivation_id
    as_role(client, account)
    assert client.get(LIST).status_code == 403
    assert confirm(client, deactivation_id).status_code == 403
    assert request_for(decision_id).status == "pending_deactivation"
    as_role(client, ADMIN)
    listed = client.get(LIST).get_json()["deactivations"]
    row = next(r for r in listed if r["deactivation_id"] == deactivation_id)
    assert (row["decision_id"], row["status"], row["effective_outcome"]) == (decision_id, "pending_deactivation", FRAUD)


def test_signed_out_requests_are_refused(client) -> None:
    assert client.get(LIST).status_code == 401
    assert confirm(client, "DAnothing").status_code == 401


# --- Confirming ---

def test_the_administrator_confirms_once_and_nothing_is_deleted(client) -> None:
    decision_id, agent_id = proposed(client)
    agree(client, decision_id)
    deactivation_id = request_for(decision_id).deactivation_id
    status_before = account_status(agent_id)
    as_role(client, ADMIN)
    before = datetime.utcnow()
    response = confirm(client, deactivation_id)
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["deactivation"]["status"] == "deactivated"
    row = request_for(decision_id)
    assert (row.status, row.actioned_by) == ("deactivated", ADMIN["admin_id"])
    assert row.actioned_at >= before
    (entry, details), = audit_entries("agent_deactivated", deactivation_id=deactivation_id)
    assert (entry.admin_id, entry.category, entry.target_agent_id) == (ADMIN["admin_id"], "admin", agent_id)
    assert entry.timestamp >= before and details["actioned_at"] == row.actioned_at.isoformat()
    # A second confirmation is refused and changes nothing.
    again = confirm(client, deactivation_id)
    assert again.status_code == 409
    assert len(audit_entries("agent_deactivated", deactivation_id=deactivation_id)) == 1
    # The agent, its decision and its loaded account status are all still there.
    assert account_status(agent_id) == status_before
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM agents WHERE agent_id = :a"), {"a": agent_id}).scalar() == 1
        assert conn.execute(text("SELECT status FROM review_decisions WHERE decision_id = :d"),
                            {"d": decision_id}).scalar() == "agreed"
    as_role(client, COMPLIANCE)
    assert detail_state(client, agent_id) == "deactivated"


def test_an_unknown_request_returns_404(client) -> None:
    login(client, ADMIN)
    assert confirm(client, "DAnothing").status_code == 404


# --- Corrections ---

def test_a_correction_cancels_a_pending_request_and_a_correction_back_reopens_it(client) -> None:
    decision_id, agent_id = proposed(client)
    agree(client, decision_id)
    body = correct(client, decision_id, LEGITIMATE, FRAUD)
    assert body["deactivation"] == "active"
    row = request_for(decision_id)
    assert (row.status, row.actioned_by) == ("cancelled", COMPLIANCE["admin_id"])
    (entry, _), = audit_entries("deactivation_cancelled", decision_id=decision_id)
    assert (entry.category, entry.target_agent_id) == ("review", agent_id)

    body = correct(client, decision_id, FRAUD, LEGITIMATE)
    assert body["deactivation"] == "pending_deactivation"
    row = request_for(decision_id)
    assert (row.status, row.actioned_by, row.actioned_at) == ("pending_deactivation", None, None)
    assert len(audit_entries("deactivation_requested", decision_id=decision_id)) == 2


def test_a_deactivated_agent_is_never_reactivated_by_a_correction(client) -> None:
    decision_id, agent_id = proposed(client)
    agree(client, decision_id)
    deactivation_id = request_for(decision_id).deactivation_id
    as_role(client, ADMIN)
    assert confirm(client, deactivation_id).status_code == 200
    as_role(client, COMPLIANCE)
    assert correct(client, decision_id, LEGITIMATE, FRAUD)["deactivation"] == "deactivated"
    assert request_for(decision_id).status == "deactivated"
    assert audit_entries("deactivation_cancelled", decision_id=decision_id) == []
    assert correct(client, decision_id, FRAUD, LEGITIMATE)["deactivation"] == "deactivated"
    assert len(requests_for(decision_id)) == 1


# --- Detection runs ---

def test_a_detection_run_does_not_change_any_status(client) -> None:
    from src.scoring_service import run_detection_cycle

    pending_id, pending_agent = proposed(client)
    agree(client, pending_id)
    done_id, done_agent = proposed(client, skip=0)
    agree(client, done_id)
    as_role(client, ADMIN)
    assert confirm(client, request_for(done_id).deactivation_id).status_code == 200

    def snapshot():
        return [(r.status, r.actioned_by, r.actioned_at) for r in (request_for(pending_id), request_for(done_id))]

    before = snapshot()
    run_detection_cycle(trigger="test-deactivation")
    assert snapshot() == before == [("pending_deactivation", None, None), before[1]]
    assert before[1][0] == "deactivated"
    as_role(client, COMPLIANCE)
    assert detail_state(client, pending_agent) == "pending_deactivation"
    assert detail_state(client, done_agent) == "deactivated"
