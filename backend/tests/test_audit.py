"""Audit log (issue #18): columns, append-only rule, event types, filters and IP masking."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import inspect as sa_inspect, text

from src import audit
from src.api import app
from src.db import AUDIT_CATEGORIES, engine, migrate_schema
from tests.helpers import ADMIN, ANALYST, COMPLIANCE, login


def entries(client, **filters):
    query = "&".join(f"{k}={v}" for k, v in {**filters, "limit": 1000}.items())
    response = client.get(f"/api/audit-log?{query}")
    assert response.status_code == 200, response.get_json()
    return response.get_json()["entries"]


def newest(client, account, **filters):
    login(client, account)
    return entries(client, **filters)


def test_migration_adds_audit_columns_and_is_safe_twice(database) -> None:
    migrate_schema()
    migrate_schema()
    columns = {c["name"] for c in sa_inspect(engine).get_columns("admin_action_log")}
    assert {"category", "actor_type", "details", "request_ip"} <= columns
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM admin_action_log WHERE category IS NULL")).scalar() == 0


@pytest.mark.parametrize("statement", [
    "UPDATE admin_action_log SET action = 'tampered'",
    "DELETE FROM admin_action_log",
    "TRUNCATE admin_action_log",
])
def test_database_refuses_changes_to_audit_rows(database, statement) -> None:
    audit.record_now("ADM_TEST", "test_entry", "admin")
    with pytest.raises(Exception, match="append only"):
        with engine.begin() as conn:
            conn.execute(text(statement))


def test_no_route_can_change_or_delete_audit_entries(client) -> None:
    methods = {m for r in app.url_map.iter_rules() if "audit" in r.rule for m in r.methods} - {"HEAD", "OPTIONS"}
    assert methods == {"GET"}
    login(client, ADMIN)
    for method in ("put", "patch", "delete", "post"):
        assert getattr(client, method)("/api/audit-log").status_code == 405


def test_login_success_failure_and_logout_are_recorded(client) -> None:
    started = datetime.utcnow() - timedelta(seconds=1)
    client.post("/api/login", json={"username": ANALYST["username"], "password": "wrong-password"})
    login(client, ANALYST)
    client.post("/api/logout")
    found = newest(client, ADMIN, category="authentication", date_from=started.isoformat())
    failure = next(e for e in found if e["action"] == "login_failure")
    assert failure["actor"] == audit.ANONYMOUS and failure["details"]["username"] == ANALYST["username"]
    assert "password" not in str(failure["details"]).lower().replace("invalid credentials", "")
    actions = [e["action"] for e in found if e["actor"] == ANALYST["admin_id"]]
    assert actions[:2] == ["logout", "login"]
    assert all(e["actor_type"] == "user" and e["request_ip"] == "127.0.*.*" for e in found)


def test_failed_sign_in_with_an_unknown_username_does_not_store_the_typed_text(client) -> None:
    started = datetime.utcnow() - timedelta(seconds=1)
    typed = "someone-typed-this-0712345678"
    client.post("/api/login", json={"username": typed, "password": "wrong-password"})
    found = newest(client, ADMIN, category="authentication", date_from=started.isoformat())
    failure = next(e for e in found if e["action"] == "login_failure")
    assert failure["details"] == {"username": "unknown username", "reason": "invalid credentials"}
    assert typed not in str(found)


def test_actor_filter_accepts_a_username(client) -> None:
    login(client, ANALYST)
    client.post("/api/logout")
    by_id = newest(client, ADMIN, actor=ANALYST["admin_id"], category="authentication")
    by_name = entries(client, actor=ANALYST["username"], category="authentication")
    assert by_name and [e["log_id"] for e in by_name] == [e["log_id"] for e in by_id]


def test_unauthenticated_request_is_recorded_as_access_denied(client) -> None:
    started = datetime.utcnow() - timedelta(seconds=1)
    assert client.get("/api/flagged-agents").status_code == 401
    denied = newest(client, ADMIN, category="authorization", actor=audit.ANONYMOUS, date_from=started.isoformat())
    entry = next(e for e in denied if e["details"]["route"] == "/api/flagged-agents")
    assert entry["action"] == "access_denied" and entry["details"]["status"] == 401
    assert entry["details"]["role"] is None and entry["details"]["reason"] == "Authentication required"


def test_wrong_role_is_recorded_as_access_denied(client) -> None:
    login(client, COMPLIANCE)
    started = datetime.utcnow() - timedelta(seconds=1)
    assert client.post("/api/review-decisions", json={"flag_id": "x", "decision_outcome": "y"}).status_code == 403
    login(client, ADMIN)
    denied = entries(client, category="authorization", actor=COMPLIANCE["admin_id"], date_from=started.isoformat())
    entry = next(e for e in denied if e["details"]["route"] == "/api/review-decisions")
    assert entry["details"]["status"] == 403 and entry["details"]["role"] == "compliance_officer"
    assert "fraud_analyst" in entry["details"]["reason"]


def test_filters_and_paging(client) -> None:
    login(client, ADMIN)
    for category in AUDIT_CATEGORIES:
        assert all(e["category"] == category for e in entries(client, category=category))
    assert client.get("/api/audit-log?category=nope").status_code == 400
    assert client.get("/api/audit-log?date_from=yesterday").status_code == 400
    body = client.get("/api/audit-log?limit=5000").get_json()
    assert body["limit"] == 1000 and body["count"] <= 1000
    page = client.get("/api/audit-log?limit=2&offset=1").get_json()
    full = client.get("/api/audit-log?limit=3").get_json()
    assert [e["log_id"] for e in page["entries"]] == [e["log_id"] for e in full["entries"][1:3]]
    times = [e["timestamp"] for e in full["entries"]]
    assert times == sorted(times, reverse=True)
    today = datetime.utcnow().date().isoformat()
    assert all(e["timestamp"].startswith(today) for e in entries(client, date_from=today, date_to=today))


def test_mask_ip() -> None:
    assert audit.mask_ip("192.168.10.25") == "192.168.*.*"
    assert audit.mask_ip("2001:db8::1") == "2001:db8:*"
    assert audit.mask_ip(None) is None and audit.mask_ip("not-an-ip") == "masked"


def test_record_rejects_unknown_category() -> None:
    with pytest.raises(ValueError):
        audit.record(None, "x", "y", "misc")
