"""
Ring graph for one ring candidate (issue #28): its members, the number of customers each pair of members
shares, each member's county, and the group's activations per day.

- Members come from the ring-candidates view of the latest run (src/threat_intel.py), so the graph shows
  exactly the groups listed there.
- An edge is a pair of members that share at least one customer; it carries only the count, never a
  customer ID. `meets_rule` says whether the pair alone reaches the ring-candidate rule (3 or more).
- County is the agent's region from the loaded data, shown as information only. The model never uses it.
- Computed on request from stored data; nothing is written.
"""

import re
from collections import defaultdict
from datetime import timedelta
from itertools import combinations

from sqlalchemy import text

from src import activity, threat_intel
from src.db import Agent, AgentScore
from src.risk import risk_band

CANDIDATE_PATTERN = re.compile(r"cand_\d{2,}")


def candidate(db_session, run, candidate_id):
    """The candidate from the run's ring-candidates view, or None."""
    if not isinstance(candidate_id, str) or not CANDIDATE_PATTERN.fullmatch(candidate_id):
        return None
    view = threat_intel.view_payload(db_session, run, "ring-candidates")
    return next((c for c in view["candidates"] if c["candidate_id"] == candidate_id), None)


def ring_graph(db_session, run, ring):
    members = sorted(ring["agent_ids"])
    rows = db_session.execute(text(
        "SELECT agent_id, customer_id, CAST(timestamp AS date) FROM activation_records WHERE agent_id = ANY(:m)"),
        {"m": members}).all()
    customers = defaultdict(set)
    per_day = defaultdict(lambda: defaultdict(int))
    for agent_id, customer_id, day in rows:
        customers[agent_id].add(customer_id)
        per_day[day][agent_id] += 1

    edges = []
    for a, b in combinations(members, 2):
        shared = len(customers[a] & customers[b])
        if shared:
            edges.append({"source": a, "target": b, "shared_customers": shared,
                          "meets_rule": shared >= threat_intel.RING_MIN_SHARED_CUSTOMERS})

    regions = dict(db_session.query(Agent.agent_id, Agent.region).filter(Agent.agent_id.in_(members)).all())
    scores = {s.agent_id: s for s in db_session.query(AgentScore).filter(
        AgentScore.run_id == run.run_id, AgentScore.agent_id.in_(members))}
    nodes = []
    for agent_id in members:
        score = scores.get(agent_id)
        nodes.append({
            "agent_id": agent_id,
            "county": regions.get(agent_id),
            "flag_source": score.flag_source if score else None,
            "risk_band": risk_band(score.flag_source, score.anomaly_score, score.threshold) if score else None,
            "activations": sum(n for counts in per_day.values() for a, n in counts.items() if a == agent_id),
            "linked_members": sum(1 for e in edges if agent_id in (e["source"], e["target"])),
        })

    first, last = activity.data_window(db_session)
    days = []
    if first is not None:
        day = first
        while day <= last:
            counts = per_day.get(day, {})
            days.append({"date": day.isoformat(), "activations": sum(counts.values()),
                         "by_agent": {a: counts.get(a, 0) for a in members}})
            day += timedelta(days=1)

    counties = sorted({n["county"] for n in nodes if n["county"]})
    return {
        "run_id": run.run_id,
        "candidate_id": ring["candidate_id"],
        "size": len(members),
        "rule": threat_intel.RING_RULE,
        "min_shared_customers": threat_intel.RING_MIN_SHARED_CUSTOMERS,
        "nodes": nodes,
        "edges": sorted(edges, key=lambda e: (-e["shared_customers"], e["source"], e["target"])),
        "counties": counties,
        "county_count": len(counties),
        "county_note": "County is the agent's region in the loaded data, shown for information only. The model never uses it.",
        "first_day": first.isoformat() if first else None,
        "last_day": last.isoformat() if last else None,
        "days": days,
        "note": "Days are as recorded in the data.",
    }
