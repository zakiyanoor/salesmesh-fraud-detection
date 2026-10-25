"""Ring graph (issue #28): GET /api/threat-intelligence/ring-candidates/<candidate_id>."""

import json
import time
from itertools import combinations

import pytest
from sqlalchemy import text

from src.db import engine
from tests.helpers import ALL_ACCOUNTS, ANALYST, login


def sql(statement, **params):
    with engine.connect() as conn:
        return conn.execute(text(statement), params).all()


def rings(client):
    login(client, ANALYST)
    return client.get("/api/threat-intelligence/ring-candidates").get_json()["candidates"]


def graph(client, candidate_id):
    response = client.get(f"/api/threat-intelligence/ring-candidates/{candidate_id}")
    assert response.status_code == 200, response.get_json()
    return response.get_json()


@pytest.fixture
def largest(client):
    ring = max(rings(client), key=lambda c: (c["size"], c["shared_customers"]))
    return ring, graph(client, ring["candidate_id"])


def test_a_request_without_a_session_is_refused_and_logged(client) -> None:
    before = sql("SELECT count(*) FROM admin_action_log WHERE action = 'access_denied'")[0][0]
    assert client.get("/api/threat-intelligence/ring-candidates/cand_01").status_code == 401
    rows = sql("SELECT details FROM admin_action_log WHERE action = 'access_denied' ORDER BY timestamp")
    assert len(rows) == before + 1
    assert json.loads(rows[-1][0])["route"] == "/api/threat-intelligence/ring-candidates/cand_01"


def test_every_role_reads_it_like_the_other_threat_intelligence_views(client) -> None:
    for account in ALL_ACCOUNTS:
        login(client, account)
        assert client.get("/api/threat-intelligence/ring-candidates/cand_01").status_code == 200
        client.post("/api/logout")


@pytest.mark.parametrize("candidate_id", ["cand_99", "cand_x", "1", "cand_01;"])
def test_unknown_or_malformed_candidates_are_404(client, candidate_id) -> None:
    login(client, ANALYST)
    assert client.get(f"/api/threat-intelligence/ring-candidates/{candidate_id}").status_code == 404


def test_every_candidate_has_the_members_of_the_ring_candidates_view(client) -> None:
    for ring in rings(client):
        body = graph(client, ring["candidate_id"])
        assert [n["agent_id"] for n in body["nodes"]] == sorted(ring["agent_ids"])
        assert body["size"] == ring["size"]


def test_edges_carry_the_shared_customer_count_of_each_pair(client, largest) -> None:
    ring, body = largest
    members = sorted(ring["agent_ids"])
    customers = {a: {c for (c,) in sql("SELECT DISTINCT customer_id FROM activation_records WHERE agent_id = :a", a=a)}
                 for a in members}
    expected = {(a, b): len(customers[a] & customers[b]) for a, b in combinations(members, 2)
                if customers[a] & customers[b]}
    assert {(e["source"], e["target"]): e["shared_customers"] for e in body["edges"]} == expected
    assert all(e["meets_rule"] == (e["shared_customers"] >= 3) for e in body["edges"])
    assert set(body["edges"][0]) == {"source", "target", "shared_customers", "meets_rule"}


def test_no_customer_id_appears(client) -> None:
    for ring in rings(client):
        assert "CUST" not in json.dumps(graph(client, ring["candidate_id"]))


def test_county_per_member_and_distinct_counties_come_from_the_agents(client, largest) -> None:
    ring, body = largest
    regions = dict(sql("SELECT agent_id, region FROM agents WHERE agent_id = ANY(:m)", m=ring["agent_ids"]))
    assert {n["agent_id"]: n["county"] for n in body["nodes"]} == regions
    assert body["counties"] == sorted(set(regions.values())) and body["county_count"] == len(set(regions.values()))
    assert "never uses it" in body["county_note"]


def test_the_group_timeline_covers_the_data_window_and_adds_up(client, largest) -> None:
    ring, body = largest
    first, last = sql("SELECT min(timestamp)::date, max(timestamp)::date FROM activation_records")[0]
    assert (body["first_day"], body["last_day"]) == (first.isoformat(), last.isoformat())
    assert len(body["days"]) == (last - first).days + 1
    total = sql("SELECT count(*) FROM activation_records WHERE agent_id = ANY(:m)", m=ring["agent_ids"])[0][0]
    assert sum(d["activations"] for d in body["days"]) == total == sum(n["activations"] for n in body["nodes"])
    assert all(sum(d["by_agent"].values()) == d["activations"] for d in body["days"])


def test_nothing_is_written_and_it_is_fast(client, largest) -> None:
    ring, _ = largest
    counts = lambda: sql("SELECT (SELECT count(*) FROM admin_action_log), (SELECT count(*) FROM threat_views)")[0]  # noqa: E731
    before = counts()
    start = time.perf_counter()
    graph(client, ring["candidate_id"])
    assert time.perf_counter() - start < 1.0
    assert counts() == before
