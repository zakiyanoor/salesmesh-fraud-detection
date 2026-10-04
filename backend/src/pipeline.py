from __future__ import annotations
import re
import uuid
from collections import Counter
import numpy as np
from src.db import get_session, migrate_schema, ActivationRecord, FeatureVector, FraudFlag
from src.detector import FraudDetector

ANALYSIS_PERIOD_FORMAT = "%Y-%m"


def compute_submission_frequency(records: list) -> int:
    return len(records)


def compute_time_of_day_entropy(records: list) -> float:
    hours = [r.timestamp.hour for r in records]
    counts = Counter(hours)
    total = sum(counts.values())
    if total == 0:
        return 0.0
    probabilities = [count / total for count in counts.values()]
    entropy = -sum(p * np.log2(p) for p in probabilities if p > 0)
    return float(entropy / np.log2(24))


def compute_repetition_score(customer_ids: list[str]) -> float:
    total = len(customer_ids)
    if total == 0:
        return 0.0
    return 1 - (len(set(customer_ids)) / total)


def compute_sequential_score(customer_ids: list[str]) -> float:
    numbers = sorted({int(m.group(1)) for cid in customer_ids if (m := re.search(r"(\d+)", cid))})
    if len(numbers) < 2:
        return 0.0
    consecutive = sum(1 for i in range(1, len(numbers)) if numbers[i] - numbers[i - 1] == 1)
    return consecutive / (len(numbers) - 1)


def compute_customer_similarity(customer_ids: list[str]) -> float:
    return max(compute_repetition_score(customer_ids), compute_sequential_score(customer_ids))


def compute_collusion_score(agent_id: str, customer_ids: list[str], all_records: list) -> float:
    """
    Fraction of this agent's distinct customers that also appear in any OTHER
    agent's records: 0 = no overlap, 1 = every customer is shared.

    Counted per distinct customer so an agent repeating one shared customer
    many times isn't weighted by its repetition. `all_records` is every
    activation record for the period; the agent's own rows are ignored.
    """
    own = set(customer_ids)
    if not own:
        return 0.0
    shared = {r.customer_id for r in all_records if r.agent_id != agent_id and r.customer_id in own}
    return len(shared) / len(own)


def compute_client_category_breakdown(records: list) -> dict:
    """
    Distinct clients and categories touched by an agent's activation records.

    client_id and category are pass-through context from other SalesMesh
    modules (not owned by this service): they carry no fraud signal, so they
    are deliberately never added to build_feature_row / FEATURE_COLUMNS.
    They're surfaced here, unchanged, as evidence for admins reviewing a flag
    (see GET /api/agents/<agent_id>) -- an agent can legitimately work across
    several clients and categories.
    """
    return {
        "client_ids": sorted({r.client_id for r in records if r.client_id}),
        "categories": sorted({r.category for r in records if r.category}),
    }


def derive_analysis_period(records: list) -> str:
    """
    The period the analysed records cover: "YYYY-MM" when they fall in one
    calendar month, else "YYYY-MM_to_YYYY-MM". Derived from the data (as in
    ml/feature_engineering.py), not from when the cycle runs, so re-running a
    cycle over the same records updates that period in place.
    """
    timestamps = [r.timestamp for r in records]
    first, last = min(timestamps).strftime(ANALYSIS_PERIOD_FORMAT), max(timestamps).strftime(ANALYSIS_PERIOD_FORMAT)
    return first if first == last else f"{first}_to_{last}"


def build_feature_row(agent_id: str, records: list, all_records: list) -> dict:
    customer_ids = [r.customer_id for r in records]
    return {
        "agent_id": agent_id,
        "submission_frequency": compute_submission_frequency(records),
        "time_of_day_dist": compute_time_of_day_entropy(records),
        "customer_similarity": compute_customer_similarity(customer_ids),
        "collusion_score": compute_collusion_score(agent_id, customer_ids, all_records),
    }


def load_existing_for_period(session, analysis_period: str) -> dict:
    """
    Map agent_id -> (vector, flag) already stored for this period, so a re-run
    updates them in place instead of stacking a second vector per agent (the
    API picks the "latest" vector per agent, and vector_id is random). Updating
    in place also keeps flag_ids stable for any review decisions pointing at them.
    If a period already holds several vectors for an agent, the highest
    vector_id is reused, matching how the API picks the latest one.
    """
    vectors = (
        session.query(FeatureVector)
        .filter(FeatureVector.analysis_period == analysis_period)
        .order_by(FeatureVector.vector_id)
        .all()
    )
    latest = {v.agent_id: v for v in vectors}
    flags = {
        f.vector_id: f
        for f in session.query(FraudFlag).filter(FraudFlag.vector_id.in_([v.vector_id for v in latest.values()]))
    }
    return {agent_id: (v, flags.get(v.vector_id)) for agent_id, v in latest.items()}


def run_detection_cycle() -> dict:
    migrate_schema()
    session = get_session()
    try:
        records = session.query(ActivationRecord).all()
        by_agent: dict[str, list] = {}
        for record in records:
            by_agent.setdefault(record.agent_id, []).append(record)

        if not records:
            return {"agents_processed": 0, "flagged": 0}

        analysis_period = derive_analysis_period(records)
        feature_rows = [build_feature_row(agent_id, recs, records) for agent_id, recs in by_agent.items()]

        detector = FraudDetector()
        results = detector.score(feature_rows)

        existing = load_existing_for_period(session, analysis_period)
        for row, result in zip(feature_rows, results):
            vector, flag = existing.get(row["agent_id"], (None, None))
            if vector is None:
                vector = FeatureVector(
                    vector_id=f"FV{uuid.uuid4().hex[:8]}",
                    agent_id=row["agent_id"],
                    analysis_period=analysis_period,
                )
                session.add(vector)
            vector.submission_frequency = row["submission_frequency"]
            vector.time_of_day_dist = row["time_of_day_dist"]
            vector.customer_similarity = row["customer_similarity"]
            vector.collusion_score = row["collusion_score"]

            if flag is None:
                flag = FraudFlag(flag_id=f"FL{uuid.uuid4().hex[:8]}", vector_id=vector.vector_id)
                session.add(flag)
            flag.suspicion_score = result.suspicion_score
            flag.flag_status = "flagged" if result.is_flagged else "clear"
            flag.model_version = detector.model_version

        session.commit()
        return {
            "analysis_period": analysis_period,
            "model_version": detector.model_version,
            "agents_processed": len(feature_rows),
            "flagged": sum(r.is_flagged for r in results),
        }
    finally:
        session.close()


if __name__ == "__main__":
    print(run_detection_cycle())