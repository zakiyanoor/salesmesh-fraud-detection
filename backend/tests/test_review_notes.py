"""Notes on review decisions (issue #13): validation, storage, history, audit, masking and migration."""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import inspect as sa_inspect

from src.db import FeatureVector, FraudFlag, ReviewDecision, engine, get_session, migrate_schema
from tests.helpers import ANALYST, COMPLIANCE, login
from tests.test_masking import identities, sweep_every_get_route  # noqa: F401  (identities is a fixture)

NOTES = "Two agents activated the same customer within an hour."


@pytest.fixture
def flag():
    db_session = get_session()
    try:
        row = (db_session.query(FraudFlag.flag_id, FeatureVector.agent_id)
               .join(FeatureVector, FraudFlag.vector_id == FeatureVector.vector_id).first())
        assert row is not None
        return row
    finally:
        db_session.close()


def propose(client, flag_id, **extra):
    return client.post("/api/review-decisions",
                       json={"flag_id": flag_id, "decision_outcome": "confirmed_fraud", **extra})


def stored_notes(decision_id):
    db_session = get_session()
    try:
        return db_session.get(ReviewDecision, decision_id).notes
    finally:
        db_session.close()


def history_entry(client, decision_id):
    return next(d for d in client.get("/api/review-decisions").get_json()["decisions"]
                if d["decision_id"] == decision_id)


def audit_entry(client, actor, action, decision_id):
    login(client, COMPLIANCE)
    entries = client.get(f"/api/audit-log?actor={actor}&limit=1000").get_json()["entries"]
    return next(e for e in entries if e["action"] == action and e["details"]["decision_id"] == decision_id)


def analyst_decision_count():
    db_session = get_session()
    try:
        return db_session.query(ReviewDecision).filter(ReviewDecision.reviewer_id == ANALYST["admin_id"]).count()
    finally:
        db_session.close()


@pytest.mark.parametrize("extra, message", [
    ({}, "notes is required"),
    ({"notes": None}, "notes is required"),
    ({"notes": ""}, "notes must not be empty"),
    ({"notes": "  \n\t "}, "notes must not be empty"),
    ({"notes": 42}, "notes must be a string"),
    ({"notes": "a" * 1001}, "at most 1000 characters"),
    ({"notes": "bell\x07"}, "plain text"),
], ids=["missing", "null", "empty", "whitespace", "not-a-string", "too-long", "control-character"])
def test_invalid_notes_return_400_and_store_nothing(client, flag, extra, message) -> None:
    login(client, ANALYST)
    before = analyst_decision_count()
    response = propose(client, flag[0], **extra)
    assert response.status_code == 400
    assert message in response.get_json()["error"]
    assert analyst_decision_count() == before


def test_missing_body_returns_400(client) -> None:
    login(client, ANALYST)
    response = client.post("/api/review-decisions")
    assert response.status_code == 400


def test_notes_are_trimmed_and_length_is_counted_after_trimming(client, flag) -> None:
    login(client, ANALYST)
    response = propose(client, flag[0], notes="  " + "a" * 1000 + "\n ")
    assert response.status_code == 201, response.get_json()
    assert response.get_json()["notes"] == "a" * 1000


def test_notes_are_stored_and_returned_in_payload_history_and_confirmation(client, flag) -> None:
    login(client, ANALYST)
    response = propose(client, flag[0], notes=f"  {NOTES}\r\nSecond line.  ")
    assert response.status_code == 201
    body = response.get_json()
    expected = f"{NOTES}\nSecond line."
    assert body["notes"] == expected and body["status"] == "pending_confirmation"
    assert stored_notes(body["decision_id"]) == expected
    assert history_entry(client, body["decision_id"])["notes"] == expected
    client.post("/api/logout")

    login(client, COMPLIANCE)
    confirmed = client.post(f"/api/review-decisions/{body['decision_id']}/confirm").get_json()
    assert confirmed["notes"] == expected and confirmed["status"] == "confirmed"
    listed = history_entry(client, body["decision_id"])
    assert listed["notes"] == expected and listed["confirmed_by"] == COMPLIANCE["admin_id"]


def test_notes_appear_in_the_proposal_and_confirmation_audit_entries(client, flag) -> None:
    login(client, ANALYST)
    decision_id = propose(client, flag[0], notes=NOTES).get_json()["decision_id"]
    client.post("/api/logout")
    login(client, COMPLIANCE)
    assert client.post(f"/api/review-decisions/{decision_id}/confirm").status_code == 200

    proposal = audit_entry(client, ANALYST["admin_id"], "propose_decision", decision_id)
    confirmation = audit_entry(client, COMPLIANCE["admin_id"], "confirm_decision", decision_id)
    assert proposal["details"]["notes"] == NOTES
    assert confirmation["details"]["notes"] == NOTES
    assert proposal["target_agent_id"] == confirmation["target_agent_id"] == flag[1]


def test_old_decision_without_notes_still_lists_and_confirms(client, flag) -> None:
    decision_id = f"RDOLD{uuid.uuid4().hex[:8]}"
    db_session = get_session()
    try:
        db_session.add(ReviewDecision(decision_id=decision_id, flag_id=flag[0], reviewer_id=ANALYST["admin_id"],
                                      decision_outcome="legitimate", decision_timestamp=datetime.utcnow(),
                                      status="pending_confirmation"))
        db_session.commit()
    finally:
        db_session.close()

    login(client, COMPLIANCE)
    assert history_entry(client, decision_id)["notes"] is None
    response = client.post(f"/api/review-decisions/{decision_id}/confirm")
    assert response.status_code == 200 and response.get_json()["notes"] is None
    assert audit_entry(client, COMPLIANCE["admin_id"], "confirm_decision", decision_id)["details"]["notes"] is None


def test_migration_adds_a_nullable_notes_column_and_is_safe_twice(database) -> None:
    migrate_schema()
    migrate_schema()
    column = next(c for c in sa_inspect(engine).get_columns("review_decisions") if c["name"] == "notes")
    assert column["nullable"] is True


def test_phone_and_national_id_in_notes_are_masked_everywhere(client, flag, identities, known_agent_id) -> None:  # noqa: F811
    _, phone, national_id = identities[0]
    spaced_phone = f"{phone[:4]} {phone[4:7]} {phone[7:10]} {phone[10:]}"
    login(client, ANALYST)
    response = propose(client, flag[0], notes=f"Called {phone} and {spaced_phone}; ID {national_id}. CUST12345678 shared.")
    assert response.status_code == 201
    notes = response.get_json()["notes"]
    assert phone not in notes and national_id not in notes and phone[1:] not in notes
    assert notes.count(f"{'*' * (len(phone) - 4)}{phone[-3:]}") == 2
    assert f"{'*' * (len(national_id) - 3)}{national_id[-3:]}" in notes
    assert "CUST12345678" in notes
    assert stored_notes(response.get_json()["decision_id"]) == notes
    client.post("/api/logout")

    sweep_every_get_route(client, identities, known_agent_id)
