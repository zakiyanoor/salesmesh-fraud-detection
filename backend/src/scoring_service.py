"""
Scoring service (issue #4): scores every agent with the frozen lof_v3_4f model
and runs the duplicate activation rule beside it.

- Features: ml.feature_engineering.compute_feature_vectors (imported, not
  copied) over the analysis period derived from the records: from the first
  record's day to the day after the last record. On the v3 data that is
  2026-08-01 to 2026-08-31, the period the model was frozen on.
- Model: the frozen bundle (src.ml_bridge.load_frozen_bundle), scored with
  ml.scoring.score_agents at the bundle's cutoff (1.445). No refit, no new cutoff.
- Rule: ml.baselines.duplicate_activation_counts, with the evidence behind each
  count: a (customer, client) pair the agent shares with another agent, or a
  pair it repeated after a completed activation.
- flag_source: "Both", "ML", "Rule" or "None". The model flag is the primary
  flag (fraud_flags.flag_status follows it alone); the rule is reported beside it.

run_detection_cycle() writes one detection_runs row, agent_scores and
duplicate_evidence for that run, and updates feature_vectors / fraud_flags for
the analysis period so the review workflow keeps working. The threat
intelligence views are computed in the same transaction and stored in
threat_views (issue #28), so a run never succeeds without them. Labels are never read.
"""

from __future__ import annotations

import traceback
import uuid
from datetime import datetime

import pandas as pd
from sqlalchemy import insert, select

from src import audit, ml_bridge, threat_intel
from src.db import (
    ActivationRecord, Agent, AgentScore, DetectionRun, DuplicateEvidence, FeatureVector, FraudFlag, get_session,
    migrate_schema,
)

PAIR = ["customer_id", "client_id"]
SHARED, REPEAT = "shared customer", "repeat after completed"
RECORD_COLUMNS = ["record_id", "agent_id", "timestamp", "customer_id", "client_id", "category", "activation_status"]


def analysis_period(activations):
    timestamps = pd.to_datetime(activations["timestamp"])
    return timestamps.min().normalize(), timestamps.max().normalize() + pd.Timedelta(days=1)


def flag_source(ml_flag, rule_flag):
    return {(True, True): "Both", (True, False): "ML", (False, True): "Rule"}.get((bool(ml_flag), bool(rule_flag)), "None")


def duplicate_evidence(activations):
    """One row per (agent, pair, reason[, other agent]), with the agent's record ids for that pair."""
    acts = activations[RECORD_COLUMNS].assign(timestamp=pd.to_datetime(activations["timestamp"]))
    acts = acts.sort_values("timestamp", kind="mergesort")
    record_ids = acts.groupby(["agent_id", *PAIR])["record_id"].agg(lambda r: ",".join(r))
    users = acts.groupby(PAIR)["agent_id"].unique()
    rows = []
    for (customer, client), agents in users[users.map(len) > 1].items():
        for agent in agents:
            for other in agents:
                if other != agent:
                    rows.append({"agent_id": agent, "customer_id": customer, "client_id": client, "other_agent_id": other,
                                 "reason": SHARED, "record_ids": record_ids[(agent, customer, client)]})
    previous = acts.groupby(["agent_id", *PAIR])["activation_status"].shift()
    repeats = acts[previous.eq("completed")].drop_duplicates(["agent_id", *PAIR])
    for row in repeats.itertuples():
        rows.append({"agent_id": row.agent_id, "customer_id": row.customer_id, "client_id": row.client_id,
                     "other_agent_id": None, "reason": REPEAT,
                     "record_ids": record_ids[(row.agent_id, row.customer_id, row.client_id)]})
    return pd.DataFrame(rows, columns=["agent_id", "customer_id", "client_id", "other_agent_id", "reason", "record_ids"])


def score_frame(activations, agents, bundle=None):
    """
    Pure scoring (no database): returns (scores, features, evidence) DataFrames.
    scores has one row per agent in `agents`.
    """
    bundle = bundle or ml_bridge.load_frozen_bundle()
    start, end = analysis_period(activations)
    features = ml_bridge.compute_feature_vectors(activations, agents, start, end)
    output = ml_bridge.score_agents(bundle, features)
    in_period = activations[(pd.to_datetime(activations["timestamp"]) >= start)
                            & (pd.to_datetime(activations["timestamp"]) < end)]
    counts = ml_bridge.duplicate_activation_counts(in_period)
    evidence = duplicate_evidence(in_period)
    evidence_pairs = evidence.drop_duplicates(["agent_id", *PAIR]).groupby("agent_id").size()
    if not evidence_pairs.reindex(counts.index, fill_value=0).equals(counts.astype(evidence_pairs.dtype)):
        raise RuntimeError("duplicate evidence does not match ml.baselines.duplicate_activation_counts")

    scores = output.rename(columns={"score": "anomaly_score", "flag": "flagged", "reason": "reasons"})
    scores["duplicate_pairs"] = scores["agent_id"].map(counts).fillna(0).astype(int)
    scores["rule_flagged"] = scores["duplicate_pairs"] > 0
    scores["flag_source"] = [flag_source(m, r) for m, r in zip(scores["flagged"], scores["rule_flagged"])]
    return scores, features, evidence


def frames_from_db(session):
    records = session.execute(select(*(getattr(ActivationRecord, c) for c in RECORD_COLUMNS))).all()
    agents = session.execute(select(Agent.agent_id, Agent.region)).all()
    return (pd.DataFrame(records, columns=RECORD_COLUMNS),
            pd.DataFrame(agents, columns=["agent_id", "region"]).sort_values("agent_id").reset_index(drop=True))


def period_label(start, end):
    first, last = start.strftime("%Y-%m"), (end - pd.Timedelta(days=1)).strftime("%Y-%m")
    return first if first == last else f"{first}_to_{last}"


def update_vectors_and_flags(session, scores, features, label):
    """feature_vectors / fraud_flags for this period, updated in place (stable flag ids for review decisions)."""
    vectors = {v.agent_id: v for v in session.query(FeatureVector).filter(FeatureVector.analysis_period == label)
               .order_by(FeatureVector.vector_id)}
    flags = {f.vector_id: f for f in session.query(FraudFlag).filter(
        FraudFlag.vector_id.in_([v.vector_id for v in vectors.values()]))}
    by_agent = features.set_index("agent_id")
    for row in scores.itertuples():
        f = by_agent.loc[row.agent_id]
        vector = vectors.get(row.agent_id)
        if vector is None:
            vector = FeatureVector(vector_id=f"FV{uuid.uuid4().hex[:8]}", agent_id=row.agent_id, analysis_period=label)
            session.add(vector)
        vector.submission_frequency = int(f["submission_frequency"])
        vector.time_of_day_dist = float(f["time_of_day_entropy"])
        vector.customer_similarity = float(f["customer_similarity"])
        vector.collusion_score = float(f["collusion_score"])
        flag = flags.get(vector.vector_id)
        if flag is None:
            flag = FraudFlag(flag_id=f"FL{uuid.uuid4().hex[:8]}", vector_id=vector.vector_id)
            session.add(flag)
        flag.suspicion_score = float(row.anomaly_score)
        flag.flag_status = "flagged" if row.flagged else "clear"
        flag.model_version = row.model_version


def system_actor(model_version=None):
    return f"system:{model_version or ml_bridge.MODEL_VERSION}"


def run_details(run):
    return {"run_id": run.run_id, "status": run.status, "trigger": run.trigger, "model_version": run.model_version,
            "threshold": run.threshold, "agents_scored": run.agents_scored, "flagged_count": run.flagged_count,
            "rule_flagged_count": run.rule_flagged_count, "both_count": run.both_count}


def previous_flag_sources(session, current_run_id):
    """agent_id -> flag_source in the newest successful run before this one ({} if there is none)."""
    previous = (session.query(DetectionRun)
                .filter(DetectionRun.status == "succeeded", DetectionRun.run_id != current_run_id)
                .order_by(DetectionRun.finished_at.desc()).first())
    if previous is None:
        return {}
    return dict(session.query(AgentScore.agent_id, AgentScore.flag_source).filter(AgentScore.run_id == previous.run_id))


def flag_changes(previous, scores):
    """
    One entry per agent whose flag_source differs from the previous run, or that
    is flagged (ML, Rule or Both) with no previous score.
    """
    changes = []
    for row in scores.itertuples():
        before = previous.get(row.agent_id)
        if before == row.flag_source or (before is None and row.flag_source == "None"):
            continue
        if before in (None, "None"):
            change = "newly flagged"
        elif row.flag_source == "None":
            change = "cleared"
        else:
            change = "flag source changed"
        changes.append({
            "agent_id": row.agent_id, "change": change,
            "previous_flag_source": before, "flag_source": row.flag_source,
            "anomaly_score": float(row.anomaly_score), "threshold": float(row.threshold),
            "top_features": row.top_features.split(";") if row.top_features else [],
            "reasons": row.reasons, "model_version": row.model_version,
        })
    return changes


def run_detection_cycle(trigger="manual"):
    """Scores every agent; returns a summary dict. Failures are recorded on the run and re-raised."""
    migrate_schema()
    session = get_session()
    run = DetectionRun(run_id=f"RUN{datetime.utcnow():%Y%m%d%H%M%S}{uuid.uuid4().hex[:6]}", trigger=trigger,
                       status="running", started_at=datetime.utcnow())
    session.add(run)
    session.commit()
    try:
        activations, agents = frames_from_db(session)
        if activations.empty:
            raise RuntimeError("no activation records to score; load the data first")
        bundle = ml_bridge.load_frozen_bundle()
        scores, features, evidence = score_frame(activations, agents, bundle)
        now = datetime.utcnow()
        session.execute(insert(AgentScore), [{
            "run_id": run.run_id, "agent_id": r.agent_id, "anomaly_score": float(r.anomaly_score),
            "threshold": float(r.threshold), "flagged": bool(r.flagged), "rule_flagged": bool(r.rule_flagged),
            "duplicate_pairs": int(r.duplicate_pairs), "flag_source": r.flag_source, "top_features": r.top_features,
            "reasons": r.reasons, "model_version": r.model_version, "created_at": now} for r in scores.itertuples()])
        if not evidence.empty:
            session.execute(insert(DuplicateEvidence), [
                {"run_id": run.run_id, **{k: (None if pd.isna(v) else v) for k, v in e.items()}}
                for e in evidence.to_dict("records")])
        start, end = analysis_period(activations)
        update_vectors_and_flags(session, scores, features, period_label(start, end))
        run.status, run.finished_at = "succeeded", datetime.utcnow()
        run.model_version, run.threshold = bundle["model_version"], float(bundle["operating_point"]["threshold"])
        run.agents_scored, run.flagged_count = len(scores), int(scores["flagged"].sum())
        run.rule_flagged_count = int(scores["rule_flagged"].sum())
        run.both_count = int((scores["flag_source"] == "Both").sum())
        threat_intel.store_views(session, run)
        changes = flag_changes(previous_flag_sources(session, run.run_id), scores)
        actor = system_actor(run.model_version)
        for change in changes:
            audit.record(session, actor, "ai_flag", "ai_decision", actor_type="system",
                         target_agent_id=change["agent_id"], details={"run_id": run.run_id, **change})
        audit.record(session, actor, "ai_detection_run", "ai_decision", actor_type="system",
                     details={**run_details(run), "flag_changes": len(changes)})
        session.commit()
        return {"run_id": run.run_id, "status": run.status, "analysis_period": period_label(start, end),
                "model_version": run.model_version, "threshold": run.threshold, "agents_scored": run.agents_scored,
                "flagged": run.flagged_count, "rule_flagged": run.rule_flagged_count, "both": run.both_count}
    except Exception:
        session.rollback()
        failed = session.get(DetectionRun, run.run_id)
        failed.status, failed.finished_at = "failed", datetime.utcnow()
        failed.error = traceback.format_exc(limit=5)[-4000:]
        audit.record(session, system_actor(failed.model_version), "ai_detection_run", "ai_decision",
                     actor_type="system",
                     details={**run_details(failed), "error": failed.error.strip().splitlines()[-1]})
        session.commit()
        raise
    finally:
        session.close()
