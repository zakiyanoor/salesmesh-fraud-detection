"""
Customer view (issue #28): the agents, clients and dates behind one customer in
the duplicate evidence, opened from an agent's evidence table.

- Only customers in the latest successful run's duplicate evidence can be
  opened; any other reference is unknown (404).
- URLs and the audit log carry customer_ref, a keyed hash of the customer ID
  (CUSTOMER_REF_KEY), never the customer ID itself. The response shows the
  customer ID as the evidence table already does.
- The agent page the view was opened from is untrusted input: it is kept only
  if it has the agent ID format and the agent exists.
- Read only: nothing here changes a score, a flag or a review decision.
"""

import hashlib
import hmac
import re
import threading

from src.db import ActivationRecord, Agent, AgentScore, DuplicateEvidence
from src.risk import risk_band

REF_PREFIX = "c_"
REF_HEX_LENGTH = 24
REF_PATTERN = re.compile(rf"{REF_PREFIX}[0-9a-f]{{{REF_HEX_LENGTH}}}")
AGENT_ID_PATTERN = re.compile(r"A\d{5}")
ACTIVATIONS_LIMIT = 200

_REFS = {}
_REFS_RUNS = 4
_REFS_LOCK = threading.Lock()


def customer_ref(key, customer_id):
    """The customer's reference: HMAC-SHA256 of the customer ID under key, shortened."""
    digest = hmac.new(key.encode("utf-8"), customer_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return REF_PREFIX + digest[:REF_HEX_LENGTH]


def evidence_refs(db_session, run, key):
    """{customer_ref: customer_id} for every customer in the run's duplicate evidence (cached per run)."""
    cached = _REFS.get(run.run_id)
    if cached is None:
        ids = {c for (c,) in db_session.query(DuplicateEvidence.customer_id)
               .filter(DuplicateEvidence.run_id == run.run_id).distinct()}
        cached = {customer_ref(key, c): c for c in ids}
        with _REFS_LOCK:
            while len(_REFS) >= _REFS_RUNS:
                _REFS.pop(next(iter(_REFS)))
            _REFS[run.run_id] = cached
    return cached


def resolve(db_session, run, key, ref):
    """The customer ID for a reference in the run's evidence, or None (also for anything not shaped like one)."""
    if not isinstance(ref, str) or not REF_PATTERN.fullmatch(ref):
        return None
    return evidence_refs(db_session, run, key).get(ref)


def opened_from(db_session, value):
    """The agent page the view was opened from, if it is a well-formed, existing agent ID; else None."""
    if not isinstance(value, str) or not AGENT_ID_PATTERN.fullmatch(value):
        return None
    return value if db_session.get(Agent, value) is not None else None


def customer_view(db_session, run, customer_id, ref, limit=None):
    """The agents who used the customer, the clients, the dates, and the latest activations (capped)."""
    limit = ACTIVATIONS_LIMIT if limit is None else limit
    records = (db_session.query(ActivationRecord.agent_id, ActivationRecord.timestamp, ActivationRecord.client_id,
                                ActivationRecord.activation_status)
               .filter(ActivationRecord.customer_id == customer_id)
               .order_by(ActivationRecord.timestamp.desc(), ActivationRecord.agent_id).all())
    scores = {s.agent_id: s for s in db_session.query(AgentScore).filter(
        AgentScore.run_id == run.run_id, AgentScore.agent_id.in_({r.agent_id for r in records}))}

    agents = {}
    for r in records:
        a = agents.setdefault(r.agent_id, {"agent_id": r.agent_id, "activations": 0, "client_ids": set(),
                                           "first_seen": r.timestamp, "last_seen": r.timestamp})
        a["activations"] += 1
        a["client_ids"].add(r.client_id)
        a["first_seen"], a["last_seen"] = min(a["first_seen"], r.timestamp), max(a["last_seen"], r.timestamp)
    agent_rows = []
    for a in sorted(agents.values(), key=lambda a: (-a["activations"], a["agent_id"])):
        score = scores.get(a["agent_id"])
        agent_rows.append({
            "agent_id": a["agent_id"],
            "flag_source": score.flag_source if score else None,
            "risk_band": risk_band(score.flag_source, score.anomaly_score, score.threshold) if score else None,
            "activations": a["activations"],
            "client_ids": sorted(c for c in a["client_ids"] if c),
            "first_seen": a["first_seen"].isoformat(),
            "last_seen": a["last_seen"].isoformat(),
        })
    clients = sorted({r.client_id for r in records if r.client_id})
    return {
        "customer": {"customer_ref": ref, "customer_id": customer_id},
        "run_id": run.run_id,
        "agent_count": len(agent_rows),
        "client_count": len(clients),
        "client_ids": clients,
        "first_seen": records[-1].timestamp.isoformat() if records else None,
        "last_seen": records[0].timestamp.isoformat() if records else None,
        "agents": agent_rows,
        "activations_total": len(records),
        "activations_limit": limit,
        "activations": [{"timestamp": r.timestamp.isoformat(), "agent_id": r.agent_id, "client_id": r.client_id,
                         "status": r.activation_status} for r in records[:limit]],
    }
