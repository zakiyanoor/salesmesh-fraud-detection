"""Threat intelligence views (issue #18): numbers checked against direct SQL on the latest successful run."""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

from src.db import engine
from tests.helpers import ALL_ACCOUNTS, ANALYST, login

VIEWS = ["summary", "by-region", "by-client", "by-category", "timeline", "customer-sharing", "ring-candidates"]


def sql(statement, **params):
    with engine.connect() as conn:
        return conn.execute(text(statement), params).all()


def latest_run_id():
    return sql("SELECT run_id FROM detection_runs WHERE status = 'succeeded' ORDER BY finished_at DESC LIMIT 1")[0][0]


def view(client, name):
    login(client, ANALYST)
    response = client.get(f"/api/threat-intelligence/{name}")
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["run"]["run_id"] == latest_run_id()
    return body


@pytest.mark.parametrize("name", VIEWS)
def test_views_need_login_and_are_open_to_every_role(client, name) -> None:
    assert client.get(f"/api/threat-intelligence/{name}").status_code == 401
    for account in ALL_ACCOUNTS:
        login(client, account)
        assert client.get(f"/api/threat-intelligence/{name}").status_code == 200
        client.post("/api/logout")


def test_summary_matches_sql(client) -> None:
    body = view(client, "summary")
    run = latest_run_id()
    counts = dict(sql("SELECT flag_source, count(*) FROM agent_scores WHERE run_id = :r GROUP BY flag_source", r=run))
    assert body["flag_sources"] == {k: counts.get(k, 0) for k in ("ML", "Rule", "Both", "None")}
    assert body["agents_scored"] == sum(counts.values()) == 1000
    assert body["flagged"] == counts.get("ML", 0) + counts.get("Both", 0)
    assert body["flagged_rate"] == pytest.approx(body["flagged"] / 1000)
    assert body["rule_flagged"] == sql("SELECT count(*) FROM agent_scores WHERE run_id = :r AND rule_flagged", r=run)[0][0]
    assert sum(body["risk_bands"].values()) == 1000 and body["risk_bands"]["high"] == body["flagged"]
    total, flagged = sql(
        "SELECT sum(r.commission_kes), sum(CASE WHEN s.flag_source IN ('ML', 'Both') THEN r.commission_kes ELSE 0 END) "
        "FROM activation_records r JOIN agent_scores s ON s.agent_id = r.agent_id AND s.run_id = :r", r=run)[0]
    assert body["commission_kes"]["total"] == total and body["commission_kes"]["flagged_agents"] == flagged
    assert body["commission_kes"]["flagged_share"] == pytest.approx(flagged / total, abs=1e-6)
    first = dict(sql("SELECT split_part(top_features, ';', 1), count(*) FROM agent_scores "
                     "WHERE run_id = :r AND flag_source IN ('ML', 'Both') GROUP BY 1", r=run))
    assert {f["feature"]: f["agents"] for f in body["top_features"]["as_top_feature"]} == first


def test_by_region_matches_sql(client) -> None:
    body = view(client, "by-region")
    expected = {row[0]: row[1:] for row in sql(
        "SELECT a.region, count(*), sum(CASE WHEN s.flag_source IN ('ML', 'Both') THEN 1 ELSE 0 END), "
        "sum(CASE WHEN s.rule_flagged THEN 1 ELSE 0 END) FROM agent_scores s JOIN agents a ON a.agent_id = s.agent_id "
        "WHERE s.run_id = :r GROUP BY a.region", r=latest_run_id())}
    assert {r["region"]: (r["agents"], r["flagged"], r["rule_flagged"]) for r in body["regions"]} == expected
    assert len(body["regions"]) == 47
    top = body["top_by_flagged_rate"]
    assert len(top) == 10 and all(r["agents"] >= 5 for r in top)
    rates = [r["flagged_rate"] for r in top]
    assert rates == sorted(rates, reverse=True)
    eligible = [r["flagged_rate"] for r in body["regions"] if r["agents"] >= 5]
    assert rates[-1] >= sorted(eligible, reverse=True)[9]


@pytest.mark.parametrize("name, column, key", [("by-client", "client_id", "clients"), ("by-category", "category", "categories")])
def test_by_client_and_category_match_sql(client, name, column, key) -> None:
    body = view(client, name)
    expected = {row[0]: row[1:] for row in sql(
        f"SELECT r.{column}, count(*), sum(CASE WHEN s.flag_source IN ('ML', 'Both') THEN 1 ELSE 0 END), "
        f"count(DISTINCT CASE WHEN s.flag_source IN ('ML', 'Both') THEN r.agent_id END) FROM activation_records r "
        f"JOIN agent_scores s ON s.agent_id = r.agent_id AND s.run_id = :r GROUP BY r.{column}", r=latest_run_id())}
    rows = body[key]
    assert {r[column]: (r["activations"], r["flagged_activations"], r["flagged_agents"]) for r in rows} == expected
    assert sum(r["share_of_all_flagged_activations"] for r in rows) == pytest.approx(1.0, abs=1e-4)
    assert len(rows) == (20 if name == "by-client" else 12)


def test_timeline_matches_sql(client) -> None:
    body = view(client, "timeline")
    first, last = sql("SELECT min(timestamp)::date, max(timestamp)::date FROM activation_records")[0]
    assert (body["first_day"], body["last_day"]) == (first.isoformat(), last.isoformat())
    assert len(body["days"]) == (last - first).days + 1 == 30
    per_day = dict(sql("SELECT timestamp::date, count(*) FROM activation_records GROUP BY 1"))
    assert {date.fromisoformat(d["date"]): d["flagged_agents"] + d["other_agents"] for d in body["days"]} == per_day
    flagged = sql("SELECT count(*) FROM activation_records r JOIN agent_scores s ON s.agent_id = r.agent_id "
                  "AND s.run_id = :r WHERE s.flag_source IN ('ML', 'Both')", r=latest_run_id())[0][0]
    assert sum(d["flagged_agents"] for d in body["days"]) == flagged


def test_customer_sharing_matches_sql(client) -> None:
    body = view(client, "customer-sharing")
    run = latest_run_id()
    shared = sql("SELECT count(DISTINCT customer_id) FROM duplicate_evidence WHERE run_id = :r "
                 "AND reason = 'shared customer'", r=run)[0][0]
    assert body["shared_customers"] == shared and len(body["customers"]) == min(shared, 50)
    for customer in body["customers"][:10]:
        agents = {a for row in sql("SELECT agent_id, other_agent_id FROM duplicate_evidence WHERE run_id = :r "
                                   "AND reason = 'shared customer' AND customer_id = :c", r=run, c=customer["customer_id"])
                  for a in row}
        assert set(customer["agent_ids"]) == agents and customer["agent_count"] == len(agents) >= 2
    clusters = body["clusters"]
    members = [set(c["agent_ids"]) for c in clusters]
    assert all(a.isdisjoint(b) for i, a in enumerate(members) for b in members[i + 1:])
    edges = sql("SELECT DISTINCT agent_id, other_agent_id FROM duplicate_evidence WHERE run_id = :r "
                "AND reason = 'shared customer'", r=run)
    nodes = {a for edge in edges for a in edge}
    if body["clusters_total"] <= 50:
        assert set().union(*members) == nodes
    for a, b in edges:
        holders = [m for m in members if a in m or b in m]
        assert len(holders) <= 1 and (not holders or {a, b} <= holders[0])
    assert all(c["size"] == len(c["agent_ids"]) >= 2 for c in clusters)


# --- Ring candidates (issue #26): the Step 11 rule, on the run's model flags ---

FROZEN_RING_CANDIDATES = (Path(__file__).resolve().parents[2] / "ml" / "runs" / "20261013-103859_final_evaluation_s42"
                          / "ring_candidates.csv")


def test_ring_candidate_rule_by_hand() -> None:
    from src.threat_intel import ring_candidate_groups

    customers = {
        "A": {"c1", "c2", "c3", "x"}, "B": {"c1", "c2", "c3"},  # 3 shared: linked
        "C": {"c3", "d1", "d2", "d3"}, "D": {"d1", "d2", "d3"},  # C-D linked; C-B share only c3
        "E": {"e1", "e2"}, "F": {"e1", "e2", "f"},  # 2 shared: not linked
        "G": {"g1"},  # alone: never a candidate
    }
    groups = sorted(sorted(g) for g in ring_candidate_groups(customers))
    assert groups == [["A", "B"], ["C", "D"]]
    customers["D"] |= {"c1", "c2", "c3"}  # D now shares c1, c2, c3 with B: everything joins transitively
    assert sorted(sorted(g) for g in ring_candidate_groups(customers)) == [["A", "B", "C", "D"]]


def test_ring_candidates_match_step_11(client) -> None:
    body = view(client, "ring-candidates")
    frozen = pd.read_csv(FROZEN_RING_CANDIDATES)
    expected = {frozenset(g["agent_id"]) for _, g in frozen.groupby("candidate_id")}
    assert {frozenset(c["agent_ids"]) for c in body["candidates"]} == expected
    assert body["candidates_total"] == len(body["candidates"]) == 14
    assert body["min_shared_customers"] == 3


def test_ring_candidates_are_model_flagged_and_share_customers(client) -> None:
    body = view(client, "ring-candidates")
    run = latest_run_id()
    flagged = {r[0] for r in sql("SELECT agent_id FROM agent_scores WHERE run_id = :r AND flag_source IN ('ML', 'Both')",
                                 r=run)}
    assert body["flagged_agents"] == len(flagged)
    members = [set(c["agent_ids"]) for c in body["candidates"]]
    assert all(m <= flagged for m in members)
    assert all(a.isdisjoint(b) for i, a in enumerate(members) for b in members[i + 1:])
    for c in body["candidates"]:
        assert c["size"] == len(c["agent_ids"]) >= 2
        shared = sql("SELECT count(*) FROM (SELECT customer_id FROM activation_records WHERE agent_id = ANY(:a) "
                     "GROUP BY customer_id HAVING count(DISTINCT agent_id) >= 2) s", a=c["agent_ids"])[0][0]
        assert c["shared_customers"] == shared >= 3
    assert [c["candidate_id"] for c in body["candidates"]] == [f"cand_{i:02d}" for i in range(1, 15)]
    assert [c["size"] for c in body["candidates"]] == sorted((c["size"] for c in body["candidates"]), reverse=True)
