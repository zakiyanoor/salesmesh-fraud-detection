"""
Tests for role-based access control, the admin audit log, dual-control review
decisions, login rate limiting, and admin account validation.
"""

import uuid
from datetime import datetime

import pytest
from flask import Flask, session

from src.auth import (
    Administrator, create_admin_user, role_required,
    ROLE_FRAUD_ANALYST, ROLE_COMPLIANCE_OFFICER,
)
from src.db import get_session, FeatureVector, FraudFlag, ReviewDecision
from tests.helpers import ANALYST, COMPLIANCE, login


def _any_flag():
    """(flag_id, agent_id) of some fraud flag in the database."""
    db_session = get_session()
    try:
        row = (
            db_session.query(FraudFlag.flag_id, FeatureVector.agent_id)
            .join(FeatureVector, FraudFlag.vector_id == FeatureVector.vector_id)
            .first()
        )
        assert row is not None, "tests need at least one fraud flag in the database"
        return row
    finally:
        db_session.close()


def _audit_entries(client, admin_id):
    return client.get(f"/api/audit-log?actor={admin_id}&limit=1000").get_json()["entries"]


def _propose(client, flag_id):
    response = client.post(
        "/api/review-decisions", json={"flag_id": flag_id, "decision_outcome": "confirmed_fraud"}
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


# --- role_required ---

@pytest.fixture
def role_app():
    app = Flask(__name__)
    app.secret_key = "test"

    @app.route("/set-session/<role>")
    def set_session(role):
        session["admin_id"] = "X1"
        session["role"] = role
        return "ok"

    @app.route("/analyst-only")
    @role_required(ROLE_FRAUD_ANALYST)
    def analyst_only():
        return "ok"

    return app.test_client()


def test_role_required_rejects_unauthenticated(role_app) -> None:
    assert role_app.get("/analyst-only").status_code == 401


def test_role_required_rejects_wrong_role(role_app) -> None:
    role_app.get(f"/set-session/{ROLE_COMPLIANCE_OFFICER}")
    assert role_app.get("/analyst-only").status_code == 403


def test_role_required_allows_matching_role(role_app) -> None:
    role_app.get(f"/set-session/{ROLE_FRAUD_ANALYST}")
    assert role_app.get("/analyst-only").status_code == 200


def test_role_required_rejects_unknown_role_name() -> None:
    with pytest.raises(ValueError):
        role_required("administrator")


def test_compliance_officer_cannot_propose_decision(client) -> None:
    flag_id, _ = _any_flag()
    login(client, COMPLIANCE)
    response = client.post(
        "/api/review-decisions", json={"flag_id": flag_id, "decision_outcome": "confirmed_fraud"}
    )
    assert response.status_code == 403


# --- Dual control ---

def test_analyst_proposal_is_pending_until_compliance_confirms(client) -> None:
    flag_id, _ = _any_flag()
    login(client, ANALYST)
    proposed = _propose(client, flag_id)
    assert proposed["status"] == "pending_confirmation"
    client.post("/api/logout")

    login(client, COMPLIANCE)
    response = client.post(f"/api/review-decisions/{proposed['decision_id']}/confirm")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "confirmed"
    assert body["confirmed_by"] == COMPLIANCE["admin_id"]

    listed = next(
        d for d in client.get("/api/review-decisions").get_json()["decisions"]
        if d["decision_id"] == proposed["decision_id"]
    )
    assert listed["status"] == "confirmed"
    assert listed["reviewer_id"] == ANALYST["admin_id"]
    assert listed["confirmed_by"] == COMPLIANCE["admin_id"]


def test_analyst_cannot_confirm_own_decision(client) -> None:
    flag_id, _ = _any_flag()
    login(client, ANALYST)
    proposed = _propose(client, flag_id)

    response = client.post(f"/api/review-decisions/{proposed['decision_id']}/confirm")
    assert response.status_code == 403

    status = next(
        d["status"] for d in client.get("/api/review-decisions").get_json()["decisions"]
        if d["decision_id"] == proposed["decision_id"]
    )
    assert status == "pending_confirmation"


def test_decision_cannot_be_confirmed_by_its_proposer(client) -> None:
    # Roles alone can't express this with the seeded accounts (only analysts
    # propose), so write a decision proposed by the compliance officer directly
    # to exercise the separate same-person check.
    flag_id, _ = _any_flag()
    decision_id = f"RDTEST{uuid.uuid4().hex[:8]}"
    db_session = get_session()
    try:
        db_session.add(ReviewDecision(
            decision_id=decision_id,
            flag_id=flag_id,
            reviewer_id=COMPLIANCE["admin_id"],
            decision_outcome="confirmed_fraud",
            decision_timestamp=datetime.utcnow(),
            status="pending_confirmation",
        ))
        db_session.commit()
    finally:
        db_session.close()

    login(client, COMPLIANCE)
    response = client.post(f"/api/review-decisions/{decision_id}/confirm")
    assert response.status_code == 403
    assert "proposed" in response.get_json()["error"]


def test_confirmed_decision_cannot_be_confirmed_again(client) -> None:
    flag_id, _ = _any_flag()
    login(client, ANALYST)
    proposed = _propose(client, flag_id)
    client.post("/api/logout")

    login(client, COMPLIANCE)
    assert client.post(f"/api/review-decisions/{proposed['decision_id']}/confirm").status_code == 200
    assert client.post(f"/api/review-decisions/{proposed['decision_id']}/confirm").status_code == 409


def test_confirming_unknown_decision_returns_404(client) -> None:
    login(client, COMPLIANCE)
    assert client.post("/api/review-decisions/NONEXISTENT/confirm").status_code == 404


# --- Audit log ---

def test_audit_log_rejects_unauthenticated(client) -> None:
    assert client.get("/api/audit-log").status_code == 401


@pytest.mark.parametrize("account", [ANALYST, COMPLIANCE], ids=["analyst", "compliance"])
def test_audit_log_accessible_to_both_roles(client, account) -> None:
    login(client, account)
    response = client.get("/api/audit-log")
    assert response.status_code == 200
    assert isinstance(response.get_json()["count"], int)


def test_audit_log_records_login_and_logout(client) -> None:
    login(client, ANALYST)
    client.post("/api/logout")

    login(client, COMPLIANCE)
    actions = [e["action"] for e in _audit_entries(client, ANALYST["admin_id"])]
    # Newest first.
    assert actions[:2] == ["logout", "login"]


def test_failed_login_is_not_recorded_as_login(client) -> None:
    # Compares the analyst's entries before and after the failed attempt, so
    # entries left by earlier runs or other tests cannot make it fail.
    login(client, COMPLIANCE)
    before = {e["log_id"] for e in _audit_entries(client, ANALYST["admin_id"])}
    client.post("/api/logout")

    response = client.post("/api/login", json={"username": ANALYST["username"], "password": "wrong-password"})
    assert response.status_code == 401
    login(client, COMPLIANCE)
    after = [e for e in _audit_entries(client, ANALYST["admin_id"]) if e["log_id"] not in before]
    assert after == []


def test_audit_log_records_decision_actions_with_target_agent(client) -> None:
    flag_id, agent_id = _any_flag()
    login(client, ANALYST)
    proposed = _propose(client, flag_id)
    client.post("/api/logout")

    login(client, COMPLIANCE)
    client.post(f"/api/review-decisions/{proposed['decision_id']}/confirm")

    proposal = next(e for e in _audit_entries(client, ANALYST["admin_id"]) if e["action"] == "propose_decision")
    confirmation = next(e for e in _audit_entries(client, COMPLIANCE["admin_id"]) if e["action"] == "confirm_decision")
    assert proposal["target_agent_id"] == agent_id
    assert confirmation["target_agent_id"] == agent_id


def test_rejected_action_is_not_recorded(client) -> None:
    flag_id, _ = _any_flag()
    login(client, COMPLIANCE)
    client.post("/api/review-decisions", json={"flag_id": flag_id, "decision_outcome": "confirmed_fraud"})

    actions = [e["action"] for e in _audit_entries(client, COMPLIANCE["admin_id"])]
    assert "propose_decision" not in actions


# --- Rate limiting ---

def test_login_is_rate_limited_to_five_per_minute(client) -> None:
    from src.api import limiter

    limiter.reset()
    limiter.enabled = True
    bad = {"username": ANALYST["username"], "password": "wrong-password"}
    for _ in range(5):
        assert client.post("/api/login", json=bad).status_code == 401
    assert client.post("/api/login", json=bad).status_code == 429


# --- Account validation ---

def test_create_admin_user_rejects_short_password() -> None:
    with pytest.raises(ValueError):
        create_admin_user("ADMSHORT", "short_pw_user", "elevenchars", ROLE_FRAUD_ANALYST)


def test_administrator_rejects_unknown_role() -> None:
    with pytest.raises(ValueError):
        Administrator(admin_id="ADMX", username="x", password_hash="h", role="administrator")
