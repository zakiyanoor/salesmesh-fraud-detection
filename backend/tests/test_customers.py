"""Customer view (issue #28): GET /api/customers/<customer_ref>, its roles, scope, audit and untrusted input."""

import json

import pytest
from sqlalchemy import text

from src import customers
from src.db import AdminActionLog, engine, get_session
from tests.helpers import ADMIN, ANALYST, COMPLIANCE, login


def sql(statement, **params):
    with engine.connect() as conn:
        return conn.execute(text(statement), params).all()


def latest_run_id():
    return sql("SELECT run_id FROM detection_runs WHERE status = 'succeeded' ORDER BY finished_at DESC LIMIT 1")[0][0]


@pytest.fixture
def shared(client):
    """(agent_id, customer_id, customer_ref) of a shared customer in the latest run's evidence, via agent detail."""
    agent_id, customer_id = sql(
        "SELECT agent_id, customer_id FROM duplicate_evidence WHERE run_id = :r AND reason = 'shared customer' "
        "ORDER BY customer_id, agent_id LIMIT 1", r=latest_run_id())[0]
    login(client, ANALYST)
    evidence = client.get(f"/api/agents/{agent_id}").get_json()["duplicate_evidence"]
    ref = next(e["customer_ref"] for e in evidence if e["customer_id"] == customer_id)
    return agent_id, customer_id, ref


def viewed_entries(ref):
    db_session = get_session()
    try:
        rows = (db_session.query(AdminActionLog).filter(AdminActionLog.action == "customer_viewed")
                .order_by(AdminActionLog.timestamp).all())
        return [(r, json.loads(r.details)) for r in rows if json.loads(r.details).get("customer_ref") == ref]
    finally:
        db_session.close()


def audit_rows(action=None):
    """Audit entries (optionally one action), read in a session that is always closed: an open one would
    hold a lock on admin_action_log and block the migrations later tests run."""
    db_session = get_session()
    try:
        query = db_session.query(AdminActionLog)
        if action:
            query = query.filter(AdminActionLog.action == action)
        return query.all()
    finally:
        db_session.close()


def all_entries_text():
    return " ".join(f"{r.details} {r.target_agent_id}" for r in audit_rows())


def test_evidence_rows_carry_a_reference_that_is_not_the_customer_id(client, shared) -> None:
    agent_id, customer_id, ref = shared
    assert customers.REF_PATTERN.fullmatch(ref) and customer_id not in ref
    evidence = client.get(f"/api/agents/{agent_id}").get_json()["duplicate_evidence"]
    assert all(customers.REF_PATTERN.fullmatch(e["customer_ref"]) for e in evidence)
    assert all(e["customer_id"].startswith("CUST") for e in evidence)  # shown in full, as before


@pytest.mark.parametrize("account", [ANALYST, COMPLIANCE], ids=["analyst", "compliance"])
def test_analysts_and_compliance_officers_can_open_a_customer(client, shared, account) -> None:
    agent_id, customer_id, ref = shared
    client.post("/api/logout")
    login(client, account)
    response = client.get(f"/api/customers/{ref}?from_agent={agent_id}")
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["customer"] == {"customer_ref": ref, "customer_id": customer_id}
    assert agent_id in [a["agent_id"] for a in body["agents"]]


def test_an_admin_is_refused_and_the_refusal_is_logged_without_the_customer_id(client, shared) -> None:
    _, customer_id, ref = shared
    before = len(viewed_entries(ref))
    client.post("/api/logout")
    login(client, ADMIN)
    assert client.get(f"/api/customers/{ref}").status_code == 403
    denied = [json.loads(r.details) for r in audit_rows("access_denied")]
    assert any(d["route"] == f"/api/customers/{ref}" and d["role"] == "admin" for d in denied)
    assert len(viewed_entries(ref)) == before
    assert customer_id not in all_entries_text()


def test_a_request_without_a_session_gets_401(client, shared) -> None:
    client.post("/api/logout")
    assert client.get(f"/api/customers/{shared[2]}").status_code == 401


@pytest.mark.parametrize("ref", ["c_" + "0" * 24, "CUST12345678", "c_short", "../agents"])
def test_unknown_or_malformed_references_are_404_and_not_audited(client, ref) -> None:
    login(client, ANALYST)
    before = len(audit_rows("customer_viewed"))
    assert client.get(f"/api/customers/{ref}").status_code == 404
    after = len(audit_rows("customer_viewed"))
    assert after == before


def test_a_customer_outside_the_duplicate_evidence_is_404(client) -> None:
    from src.api import CONFIG

    outside = sql("SELECT customer_id FROM activation_records WHERE customer_id NOT IN "
                  "(SELECT customer_id FROM duplicate_evidence WHERE run_id = :r) LIMIT 1", r=latest_run_id())[0][0]
    ref = customers.customer_ref(CONFIG["CUSTOMER_REF_KEY"], outside)
    login(client, ANALYST)
    assert client.get(f"/api/customers/{ref}").status_code == 404
    assert viewed_entries(ref) == []


def test_agents_clients_and_dates_match_the_activation_records(client, shared) -> None:
    _, customer_id, ref = shared
    body = client.get(f"/api/customers/{ref}").get_json()
    rows = sql("SELECT agent_id, client_id, timestamp FROM activation_records WHERE customer_id = :c", c=customer_id)
    assert {a["agent_id"] for a in body["agents"]} == {r[0] for r in rows} and body["agent_count"] == len({r[0] for r in rows})
    assert body["client_ids"] == sorted({r[1] for r in rows}) and body["client_count"] == len({r[1] for r in rows})
    assert body["first_seen"] == min(r[2] for r in rows).isoformat()
    assert body["last_seen"] == max(r[2] for r in rows).isoformat()
    assert body["activations_total"] == len(rows) == sum(a["activations"] for a in body["agents"])
    stamps = [a["timestamp"] for a in body["activations"]]
    assert stamps == sorted(stamps, reverse=True) and body["run_id"] == latest_run_id()
    assert set(body["activations"][0]) == {"timestamp", "agent_id", "client_id", "status"}  # no record ids


def test_the_activations_list_is_capped_with_the_total_returned(client, shared, monkeypatch) -> None:
    _, customer_id, ref = shared
    total = len(sql("SELECT 1 FROM activation_records WHERE customer_id = :c", c=customer_id))
    assert total >= 2
    monkeypatch.setattr(customers, "ACTIVATIONS_LIMIT", 1)
    body = client.get(f"/api/customers/{ref}").get_json()
    assert len(body["activations"]) == 1 and body["activations_total"] == total and body["activations_limit"] == 1
    assert customers.ACTIVATIONS_LIMIT == 1 and body["activations"][0]["timestamp"] == body["last_seen"]


def test_every_open_is_audited_with_who_opened_it_and_never_the_customer_id(client, shared) -> None:
    agent_id, customer_id, ref = shared
    before = len(viewed_entries(ref))
    client.get(f"/api/customers/{ref}?from_agent={agent_id}")
    client.post("/api/logout")
    login(client, COMPLIANCE)
    client.get(f"/api/customers/{ref}")
    entries = viewed_entries(ref)[before:]
    assert [(e.admin_id, d["role"], d["opened_from"]) for e, d in entries] == [
        (ANALYST["admin_id"], "fraud_analyst", agent_id), (COMPLIANCE["admin_id"], "compliance_officer", None)]
    assert all(e.category == "review" and e.actor_type == "user" for e, _ in entries)
    assert entries[0][0].target_agent_id == agent_id and entries[1][0].target_agent_id is None
    assert customer_id not in all_entries_text()


@pytest.mark.parametrize("value", ["A1234", "A123456", "a10053", "<script>", "../A10053", "A00000", ""])
def test_the_opened_from_agent_is_kept_only_if_well_formed_and_existing(client, shared, value) -> None:
    _, _, ref = shared
    before = len(viewed_entries(ref))
    assert client.get(f"/api/customers/{ref}", query_string={"from_agent": value}).status_code == 200
    entry, details = viewed_entries(ref)[before]
    assert details["opened_from"] is None and entry.target_agent_id is None


def test_nothing_is_shown_if_the_audit_entry_cannot_be_written(client, shared, monkeypatch) -> None:
    from src import api

    _, customer_id, ref = shared

    def broken(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(api, "log_admin_action", broken)
    response = client.get(f"/api/customers/{ref}")
    assert response.status_code == 500
    assert customer_id not in response.get_data(as_text=True)
    assert set(response.get_json()) == {"error"} and "not shown" in response.get_json()["error"]
