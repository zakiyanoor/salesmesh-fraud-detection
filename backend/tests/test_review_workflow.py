"""Review workflow (issue #28): proposals, withdrawals, agreements, overrules and corrections."""

import json
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from sqlalchemy import insert, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from src.db import (
    AdminActionLog, FeatureVector, FraudFlag, ReviewCorrection, ReviewDecision, ReviewMigrationError, engine,
    get_session, migrate_review_workflow,
)
from tests.helpers import ANALYST, COMPLIANCE, login, reviewable_flag


def flagged_flag_ids(count=1):
    """flag_ids of model-flagged agents in the latest analysis period."""
    with engine.connect() as conn:
        return [r[0] for r in conn.execute(text(
            "SELECT flag_id FROM fraud_flags WHERE flag_status = 'flagged' ORDER BY flag_id LIMIT :n"), {"n": count})]


def decision_row(flag_id, **values):
    row = {"decision_id": f"RDT{uuid.uuid4().hex[:8]}", "flag_id": flag_id, "reviewer_id": "ADM_ANALYST_01",
           "decision_outcome": "confirmed_fraud", "decision_timestamp": datetime.utcnow(),
           "status": "pending_confirmation", "notes": "Test proposal."}
    row.update(values)
    return row


@contextmanager
def rolled_back():
    """A connection whose transaction is always rolled back, so a test leaves the database as it was."""
    conn = engine.connect()
    transaction = conn.begin()
    try:
        yield conn
    finally:
        transaction.rollback()
        conn.close()


# --- Schema and migration ---

def test_review_columns_corrections_table_checks_index_and_triggers_exist(database) -> None:
    table = inspect(engine)
    columns = {c["name"] for c in table.get_columns("review_decisions")}
    assert {"run_id", "flag_source", "final_outcome", "closed_by", "closed_at", "close_note"} <= columns
    assert {c["name"] for c in table.get_columns("review_corrections")} == {
        "correction_id", "decision_id", "corrected_by", "corrected_at", "previous_outcome", "new_outcome", "note"}
    with engine.connect() as conn:
        constraints = {r[0] for r in conn.execute(text("SELECT conname FROM pg_constraint"))}
        triggers = {r[0] for r in conn.execute(text("SELECT tgname FROM pg_trigger"))}
        index = conn.execute(text(
            "SELECT indexdef FROM pg_indexes WHERE indexname = 'ux_review_decisions_one_open'")).scalar()
    assert {"ck_review_decisions_status", "ck_review_decisions_closing", "ck_review_corrections_changes_outcome",
            "ck_review_corrections_outcome"} <= constraints
    assert {"review_decisions_write_once", "review_decisions_no_truncate", "review_corrections_append_only",
            "review_corrections_no_truncate"} <= triggers
    assert "UNIQUE" in index and "pending_confirmation" in index


def test_migration_renames_confirmed_to_agreed_with_the_audit_time_and_is_safe_twice(database) -> None:
    flag_id = flagged_flag_ids()[0]
    confirmed_at = datetime(2026, 10, 1, 9, 30)
    with rolled_back() as conn:
        # Recreate a decision from before issue #28: drop the new checks for this transaction only.
        conn.execute(text("ALTER TABLE review_decisions DROP CONSTRAINT ck_review_decisions_status"))
        conn.execute(text("ALTER TABLE review_decisions DROP CONSTRAINT ck_review_decisions_closing"))
        old = decision_row(flag_id, status="confirmed", confirmed_by="ADM_COMPLIANCE_01")
        conn.execute(insert(ReviewDecision.__table__).values(**old))
        conn.execute(insert(AdminActionLog.__table__).values(
            log_id=f"AL{uuid.uuid4().hex}", admin_id="ADM_COMPLIANCE_01", action="confirm_decision",
            category="review", actor_type="user", timestamp=confirmed_at,
            details=json.dumps({"decision_id": old["decision_id"]})))

        migrate_review_workflow(conn)
        migrate_review_workflow(conn)  # a second run changes nothing

        row = conn.execute(text("SELECT status, final_outcome, closed_by, closed_at, confirmed_by FROM review_decisions "
                                "WHERE decision_id = :d"), {"d": old["decision_id"]}).one()
        assert tuple(row) == ("agreed", "confirmed_fraud", "ADM_COMPLIANCE_01", confirmed_at, "ADM_COMPLIANCE_01")


def test_migration_stops_when_a_flag_has_two_open_proposals(database) -> None:
    flag_id = flagged_flag_ids()[0]
    with rolled_back() as conn:
        conn.execute(text("DROP INDEX ux_review_decisions_one_open"))
        conn.execute(insert(ReviewDecision.__table__), [decision_row(flag_id), decision_row(flag_id)])
        with pytest.raises(ReviewMigrationError, match=flag_id):
            migrate_review_workflow(conn)


# --- Database rules ---

def test_only_one_open_proposal_per_flag_in_the_database(database) -> None:
    flag_id = flagged_flag_ids()[0]
    with rolled_back() as conn:
        conn.execute(insert(ReviewDecision.__table__).values(**decision_row(flag_id)))
        with pytest.raises(IntegrityError, match="ux_review_decisions_one_open"):
            conn.execute(insert(ReviewDecision.__table__).values(**decision_row(flag_id)))


@pytest.mark.parametrize("closing, constraint", [
    ({"status": "overruled", "final_outcome": "confirmed_fraud", "close_note": "Same."}, "ck_review_decisions_closing"),
    ({"status": "overruled", "final_outcome": "legitimate", "close_note": None}, "ck_review_decisions_closing"),
    ({"status": "withdrawn", "close_note": None}, "ck_review_decisions_closing"),
    ({"status": "agreed", "final_outcome": "legitimate"}, "ck_review_decisions_closing"),
    ({"status": "confirmed"}, "ck_review_decisions_status"),
])
def test_closing_checks_refuse_inconsistent_decisions(database, closing, constraint) -> None:
    flag_id = flagged_flag_ids()[0]
    values = {"closed_by": "ADM_COMPLIANCE_01", "closed_at": datetime.utcnow(), **closing}
    with rolled_back() as conn:
        if constraint == "ck_review_decisions_status":
            # An unknown status also fails the closing check; drop that one here to test this one alone.
            conn.execute(text("ALTER TABLE review_decisions DROP CONSTRAINT ck_review_decisions_closing"))
        with pytest.raises(IntegrityError, match=constraint):
            conn.execute(insert(ReviewDecision.__table__).values(**decision_row(flag_id, **values)))


def write_once_error(conn, sql, **params):
    with pytest.raises(DBAPIError) as error:
        conn.execute(text(sql), params)
    return str(error.value)


def test_a_proposal_is_closed_once_and_never_changed_or_deleted_afterwards(database) -> None:
    flag_id = flagged_flag_ids()[0]
    with rolled_back() as conn:
        row = decision_row(flag_id)
        conn.execute(insert(ReviewDecision.__table__).values(**row))
        d = {"d": row["decision_id"]}
        with conn.begin_nested() as step:
            assert "can only be closed" in write_once_error(
                conn, "UPDATE review_decisions SET notes = 'Edited.' WHERE decision_id = :d", **d)
            step.rollback()
        with conn.begin_nested() as step:
            assert "only the closing fields" in write_once_error(
                conn, "UPDATE review_decisions SET status = 'agreed', decision_outcome = 'legitimate', "
                "final_outcome = 'legitimate', closed_by = 'ADM_COMPLIANCE_01', closed_at = now() "
                "WHERE decision_id = :d", **d)
            step.rollback()
        conn.execute(text("UPDATE review_decisions SET status = 'agreed', final_outcome = decision_outcome, "
                          "closed_by = 'ADM_COMPLIANCE_01', closed_at = now() WHERE decision_id = :d"), d)
        for sql in ("UPDATE review_decisions SET close_note = 'Changed later.' WHERE decision_id = :d",
                    "UPDATE review_decisions SET status = 'overruled', final_outcome = 'legitimate', "
                    "close_note = 'x' WHERE decision_id = :d"):
            with conn.begin_nested() as step:
                assert "is closed and cannot be changed" in write_once_error(conn, sql, **d)
                step.rollback()
        with conn.begin_nested() as step:
            assert "never deleted" in write_once_error(conn, "DELETE FROM review_decisions WHERE decision_id = :d", **d)
            step.rollback()
        with conn.begin_nested() as step:
            assert "never deleted" in write_once_error(conn, "TRUNCATE review_decisions CASCADE")
            step.rollback()


def test_corrections_are_never_changed_or_deleted(database) -> None:
    flag_id = flagged_flag_ids()[0]
    with rolled_back() as conn:
        row = decision_row(flag_id, status="agreed", final_outcome="confirmed_fraud", closed_by="ADM_COMPLIANCE_01",
                           closed_at=datetime.utcnow())
        conn.execute(insert(ReviewDecision.__table__).values(**row))
        conn.execute(insert(ReviewCorrection.__table__).values(
            correction_id="RCT1", decision_id=row["decision_id"], corrected_by="ADM_COMPLIANCE_01",
            corrected_at=datetime.utcnow() + timedelta(minutes=1), previous_outcome="confirmed_fraud",
            new_outcome="legitimate", note="Wrong customer list."))
        for sql in ("UPDATE review_corrections SET note = 'Edited.' WHERE correction_id = 'RCT1'",
                    "DELETE FROM review_corrections WHERE correction_id = 'RCT1'",
                    "TRUNCATE review_corrections"):
            with conn.begin_nested() as step:
                assert "never changed or deleted" in write_once_error(conn, sql)
                step.rollback()
        with conn.begin_nested() as step:
            with pytest.raises(IntegrityError, match="ck_review_corrections_changes_outcome"):
                conn.execute(insert(ReviewCorrection.__table__).values(
                    correction_id="RCT2", decision_id=row["decision_id"], corrected_by="ADM_COMPLIANCE_01",
                    corrected_at=datetime.utcnow(), previous_outcome="legitimate", new_outcome="legitimate",
                    note="No change."))
            step.rollback()


def test_the_maintenance_setting_lets_cleanup_delete_review_rows(database) -> None:
    flag_id = flagged_flag_ids()[0]
    with rolled_back() as conn:
        row = decision_row(flag_id)
        conn.execute(insert(ReviewDecision.__table__).values(**row))
        conn.execute(text("SET LOCAL salesmesh.review_maintenance = 'on'"))
        assert conn.execute(text("DELETE FROM review_decisions WHERE decision_id = :d"),
                            {"d": row["decision_id"]}).rowcount == 1


# --- API helpers ---

def propose(client, flag_id, outcome="confirmed_fraud", notes="Shares customers with two other agents."):
    return client.post("/api/review-decisions", json={"flag_id": flag_id, "decision_outcome": outcome, "notes": notes})


def as_role(client, account):
    client.post("/api/logout")
    login(client, account)


def stored(decision_id):
    db_session = get_session()
    try:
        return db_session.get(ReviewDecision, decision_id)
    finally:
        db_session.close()


def audit_entries(action, **match):
    """Audit entries for an action whose details contain every key and value in match, oldest first."""
    db_session = get_session()
    try:
        rows = (db_session.query(AdminActionLog).filter(AdminActionLog.action == action)
                .order_by(AdminActionLog.timestamp).all())
        entries = [(r, json.loads(r.details or "{}")) for r in rows]
        return [(r, d) for r, d in entries if all(d.get(k) == v for k, v in match.items())]
    finally:
        db_session.close()


def latest_run_id():
    with engine.connect() as conn:
        return conn.execute(text("SELECT run_id FROM detection_runs WHERE status = 'succeeded' "
                                 "ORDER BY finished_at DESC LIMIT 1")).scalar()


def delete_review_rows(flag_id):
    """Removes a flag's review rows (for tests that cannot use the client fixture's cleanup)."""
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL salesmesh.review_maintenance = 'on'"))
        conn.execute(text("DELETE FROM review_corrections WHERE decision_id IN "
                          "(SELECT decision_id FROM review_decisions WHERE flag_id = :f)"), {"f": flag_id})
        conn.execute(text("DELETE FROM review_decisions WHERE flag_id = :f"), {"f": flag_id})


def at_the_same_moment(requests):
    """Runs each request(test_client) in its own thread, released together; returns the status codes."""
    from src.api import app, limiter

    app.config["TESTING"], limiter.enabled = True, False
    start, codes = threading.Barrier(len(requests)), []

    def send(request):
        with app.test_client() as c:
            prepared = request(c)
            start.wait()
            codes.append(prepared().status_code)

    threads = [threading.Thread(target=send, args=(r,)) for r in requests]
    try:
        [t.start() for t in threads]
        [t.join() for t in threads]
    finally:
        limiter.enabled = True
    return sorted(codes)


# --- Propose (rules 1 and 2) ---

@pytest.mark.parametrize("source", ["ML", "Rule", "Both"])
def test_any_flagged_agent_can_be_proposed_and_the_run_and_source_are_stored(client, source) -> None:
    flag_id, agent_id = reviewable_flag((source,))
    login(client, ANALYST)
    response = propose(client, flag_id)
    assert response.status_code == 201, response.get_json()
    body = response.get_json()
    assert body["flag_source"] == source and body["run_id"] == latest_run_id()
    row = stored(body["decision_id"])
    assert (row.status, row.flag_source, row.run_id) == ("pending_confirmation", source, latest_run_id())
    (entry, details), = audit_entries("propose_decision", decision_id=body["decision_id"])
    assert entry.target_agent_id == agent_id and entry.admin_id == ANALYST["admin_id"]
    assert details["flag_source"] == source and details["run_id"] == latest_run_id()


def test_an_unflagged_agent_is_refused_and_the_refusal_is_recorded(client) -> None:
    flag_id, _ = reviewable_flag(("None",))
    login(client, ANALYST)
    response = propose(client, flag_id)
    assert response.status_code == 409
    assert "not flagged in the latest detection run" in response.get_json()["error"]
    assert audit_entries("review_refused", flag_id=flag_id)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM review_decisions WHERE flag_id = :f"),
                            {"f": flag_id}).scalar() == 0


def test_a_flag_from_an_earlier_analysis_period_is_refused(client) -> None:
    _, agent_id = reviewable_flag()
    vector_id, flag_id = f"FVT{uuid.uuid4().hex[:6]}", f"FLT{uuid.uuid4().hex[:6]}"
    db_session = get_session()
    db_session.add(FeatureVector(vector_id=vector_id, agent_id=agent_id, analysis_period="2026-07"))
    db_session.flush()
    db_session.add(FraudFlag(flag_id=flag_id, vector_id=vector_id, flag_status="flagged", suspicion_score=2.0))
    db_session.commit()
    try:
        login(client, ANALYST)
        response = propose(client, flag_id)
        assert response.status_code == 409
        assert "earlier analysis period (2026-07)" in response.get_json()["error"]
    finally:
        db_session.query(FraudFlag).filter(FraudFlag.flag_id == flag_id).delete()
        db_session.query(FeatureVector).filter(FeatureVector.vector_id == vector_id).delete()
        db_session.commit()
        db_session.close()


def test_unknown_flag_returns_404(client) -> None:
    login(client, ANALYST)
    assert propose(client, "FL_DOES_NOT_EXIST").status_code == 404


def test_a_second_open_proposal_on_the_same_flag_is_refused(client) -> None:
    flag_id, _ = reviewable_flag()
    login(client, ANALYST)
    first = propose(client, flag_id).get_json()["decision_id"]
    second = propose(client, flag_id, outcome="legitimate")
    assert second.status_code == 409 and first in second.get_json()["error"]
    (_, details), = audit_entries("review_refused", flag_id=flag_id)
    assert details["route"] == "/api/review-decisions" and first in details["reason"]


def test_two_proposals_at_the_same_moment_store_exactly_one(database) -> None:
    flag_id, _ = reviewable_flag()

    def proposal(c):
        login(c, ANALYST)
        return lambda: propose(c, flag_id)

    try:
        assert at_the_same_moment([proposal, proposal]) == [201, 409]
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM review_decisions WHERE flag_id = :f"),
                                {"f": flag_id}).scalar() == 1
    finally:
        delete_review_rows(flag_id)


def test_a_new_proposal_is_allowed_after_a_withdrawal(client) -> None:
    flag_id, _ = reviewable_flag()
    login(client, ANALYST)
    first = propose(client, flag_id).get_json()["decision_id"]
    assert client.post(f"/api/review-decisions/{first}/withdraw", json={"notes": "Wrong agent."}).status_code == 200
    assert propose(client, flag_id, outcome="legitimate").status_code == 201


def test_a_new_proposal_is_refused_after_a_final_decision(client) -> None:
    flag_id, _ = reviewable_flag()
    login(client, ANALYST)
    decided = propose(client, flag_id).get_json()["decision_id"]
    as_role(client, COMPLIANCE)
    assert client.post(f"/api/review-decisions/{decided}/confirm").status_code == 200
    as_role(client, ANALYST)
    response = propose(client, flag_id, outcome="legitimate")
    assert response.status_code == 409
    assert "final decision" in response.get_json()["error"] and "correction" in response.get_json()["error"]


# --- Withdraw (rule 3) ---

def test_the_proposer_withdraws_with_a_note_and_the_audit_log_records_it(client) -> None:
    flag_id, agent_id = reviewable_flag()
    login(client, ANALYST)
    decision_id = propose(client, flag_id).get_json()["decision_id"]
    url = f"/api/review-decisions/{decision_id}/withdraw"
    assert client.post(url, json={}).status_code == 400
    assert client.post(url, json={"notes": "  "}).status_code == 400
    response = client.post(url, json={"notes": " Proposed on the wrong agent. "})
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert (body["status"], body["closed_by"], body["close_note"]) == (
        "withdrawn", ANALYST["admin_id"], "Proposed on the wrong agent.")
    row = stored(decision_id)
    assert row.status == "withdrawn" and row.final_outcome is None and row.closed_at is not None
    (entry, details), = audit_entries("withdraw_decision", decision_id=decision_id)
    assert entry.admin_id == ANALYST["admin_id"] and entry.target_agent_id == agent_id and entry.category == "review"
    assert details == {"decision_id": decision_id, "flag_id": flag_id, "decision_outcome": "confirmed_fraud",
                       "notes": "Proposed on the wrong agent."}


def test_a_withdrawn_proposal_cannot_be_withdrawn_or_confirmed_again(client) -> None:
    flag_id, _ = reviewable_flag()
    login(client, ANALYST)
    decision_id = propose(client, flag_id).get_json()["decision_id"]
    client.post(f"/api/review-decisions/{decision_id}/withdraw", json={"notes": "Not needed."})
    again = client.post(f"/api/review-decisions/{decision_id}/withdraw", json={"notes": "Again."})
    assert again.status_code == 409 and "already withdrawn" in again.get_json()["error"]
    assert audit_entries("review_refused", decision_id=decision_id)
    as_role(client, COMPLIANCE)
    assert client.post(f"/api/review-decisions/{decision_id}/confirm").status_code == 409


def test_only_the_proposer_can_withdraw(client) -> None:
    from src.auth import ROLE_FRAUD_ANALYST, create_admin_user

    other = {"admin_id": "ADM_ANALYST_02", "username": "analyst_02", "password": uuid.uuid4().hex}
    create_admin_user(other["admin_id"], other["username"], other["password"], ROLE_FRAUD_ANALYST)
    flag_id, _ = reviewable_flag()
    login(client, ANALYST)
    decision_id = propose(client, flag_id).get_json()["decision_id"]
    as_role(client, other)
    response = client.post(f"/api/review-decisions/{decision_id}/withdraw", json={"notes": "Not mine."})
    assert response.status_code == 403 and "Only the analyst who proposed" in response.get_json()["error"]
    assert audit_entries("access_denied", route=f"/api/review-decisions/{decision_id}/withdraw")
    assert stored(decision_id).status == "pending_confirmation"


def test_withdrawing_an_unknown_decision_returns_404(client) -> None:
    login(client, ANALYST)
    assert client.post("/api/review-decisions/RD_NONE/withdraw", json={"notes": "x"}).status_code == 404
