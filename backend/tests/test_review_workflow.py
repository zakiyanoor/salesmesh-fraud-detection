"""Review workflow (issue #28): proposals, withdrawals, agreements, overrules and corrections."""

import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from sqlalchemy import insert, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from src.db import (
    AdminActionLog, ReviewCorrection, ReviewDecision, ReviewMigrationError, engine, migrate_review_workflow,
)


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
