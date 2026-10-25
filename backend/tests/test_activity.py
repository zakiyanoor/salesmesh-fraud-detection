"""Daily activity for one agent (issue #28): GET /api/agents/<agent_id>/activity."""

import json
import time
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from src.db import engine
from tests.helpers import ALL_ACCOUNTS, ANALYST, login


def sql(statement, **params):
    with engine.connect() as conn:
        return conn.execute(text(statement), params).all()


def latest_run_id():
    return sql("SELECT run_id FROM detection_runs WHERE status = 'succeeded' ORDER BY finished_at DESC LIMIT 1")[0][0]


@pytest.fixture(scope="module")
def busiest(database):
    """The agent with the most activation records."""
    return sql("SELECT agent_id FROM activation_records GROUP BY 1 ORDER BY count(*) DESC, agent_id LIMIT 1")[0][0]


def activity(client, agent_id):
    login(client, ANALYST)
    response = client.get(f"/api/agents/{agent_id}/activity")
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def audit_count():
    return sql("SELECT count(*) FROM admin_action_log")[0][0]


def test_a_request_without_a_session_is_refused_and_logged(client, busiest) -> None:
    before = sql("SELECT count(*) FROM admin_action_log WHERE action = 'access_denied'")[0][0]
    assert client.get(f"/api/agents/{busiest}/activity").status_code == 401
    rows = sql("SELECT details FROM admin_action_log WHERE action = 'access_denied' ORDER BY timestamp")
    assert len(rows) == before + 1 and json.loads(rows[-1][0])["route"] == f"/api/agents/{busiest}/activity"


def test_every_role_that_reads_agent_detail_reads_activity(client, busiest) -> None:
    for account in ALL_ACCOUNTS:
        login(client, account)
        assert client.get(f"/api/agents/{busiest}").status_code == client.get(f"/api/agents/{busiest}/activity").status_code
        client.post("/api/logout")


def test_an_unknown_agent_is_404(client) -> None:
    login(client, ANALYST)
    assert client.get("/api/agents/A00000/activity").status_code == 404


def test_one_row_per_day_of_the_data_window_with_counts_from_the_records(client, busiest) -> None:
    body = activity(client, busiest)
    first, last = sql("SELECT min(timestamp)::date, max(timestamp)::date FROM activation_records")[0]
    assert (body["first_day"], body["last_day"]) == (first.isoformat(), last.isoformat())
    expected_days = [(first + timedelta(days=i)).isoformat() for i in range((last - first).days + 1)]
    assert [d["date"] for d in body["days"]] == expected_days
    counts = {d.isoformat(): (n, c) for d, n, c in sql(
        "SELECT timestamp::date, count(*), count(*) FILTER (WHERE activation_status = 'completed') "
        "FROM activation_records WHERE agent_id = :a GROUP BY 1", a=busiest)}
    for d in body["days"]:
        assert (d["activations"], d["completed"]) == counts.get(d["date"], (0, 0)), d["date"]
    assert body["totals"]["activations"] == sum(n for n, _ in counts.values())
    assert body["totals"]["completed"] == sum(c for _, c in counts.values())


def test_hours_cover_0_to_23_and_add_up_to_the_total(client, busiest) -> None:
    body = activity(client, busiest)
    assert [h["hour"] for h in body["hours"]] == list(range(24))
    assert sum(h["activations"] for h in body["hours"]) == body["totals"]["activations"]
    by_hour = dict(sql("SELECT extract(hour FROM timestamp)::int, count(*) FROM activation_records "
                       "WHERE agent_id = :a GROUP BY 1", a=busiest))
    assert all(h["activations"] == by_hour.get(h["hour"], 0) for h in body["hours"])


def test_days_with_duplicate_evidence_are_marked_from_the_latest_run(client, busiest) -> None:
    body = activity(client, busiest)
    ids = {i for (r,) in sql("SELECT record_ids FROM duplicate_evidence WHERE run_id = :r AND agent_id = :a",
                             r=latest_run_id(), a=busiest) for i in r.split(",")}
    expected = {d.isoformat() for (d,) in sql(
        "SELECT DISTINCT timestamp::date FROM activation_records WHERE record_id = ANY(:ids)", ids=sorted(ids))}
    assert expected, "the busiest agent should have duplicate evidence"
    assert {d["date"] for d in body["days"] if d["duplicate_evidence"]} == expected
    assert body["run_id"] == latest_run_id()


def test_an_agent_without_duplicate_evidence_has_no_marked_day(client) -> None:
    agent_id = sql("SELECT agent_id FROM agent_scores WHERE run_id = :r AND duplicate_pairs = 0 "
                   "ORDER BY agent_id LIMIT 1", r=latest_run_id())[0][0]
    body = activity(client, agent_id)
    assert not any(d["duplicate_evidence"] for d in body["days"])


def test_no_customer_id_no_flag_per_day_and_the_recording_note(client, busiest) -> None:
    body = activity(client, busiest)
    raw = json.dumps(body)
    assert "CUST" not in raw and "customer" not in raw
    assert set(body["days"][0]) == {"date", "activations", "completed", "duplicate_evidence"}
    assert "flagged" not in raw
    assert body["note"] == "Days and hours are as recorded in the data."


def test_reads_are_not_audited(client, busiest) -> None:
    login(client, ANALYST)
    before = audit_count()
    client.get(f"/api/agents/{busiest}/activity")
    assert audit_count() == before


def test_it_is_fast_for_the_agent_with_the_most_records(client, busiest) -> None:
    login(client, ANALYST)
    client.get(f"/api/agents/{busiest}/activity")
    start = time.perf_counter()
    assert client.get(f"/api/agents/{busiest}/activity").status_code == 200
    assert time.perf_counter() - start < 1.0
    assert isinstance(date.fromisoformat(activity(client, busiest)["first_day"]), date)
