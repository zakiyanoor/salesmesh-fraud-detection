from __future__ import annotations
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
import numpy as np
from src.db import get_session, ActivationRecord, FeatureVector, FraudFlag
from src.detector import FraudDetector

MODEL_VERSION = "lof_v1"
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


def build_feature_row(agent_id: str, records: list) -> dict:
    customer_ids = [r.customer_id for r in records]
    return {
        "agent_id": agent_id,
        "submission_frequency": compute_submission_frequency(records),
        "time_of_day_dist": compute_time_of_day_entropy(records),
        "customer_similarity": compute_customer_similarity(customer_ids),
    }


def run_detection_cycle() -> dict:
    session = get_session()
    try:
        records = session.query(ActivationRecord).all()
        by_agent: dict[str, list] = {}
        for record in records:
            by_agent.setdefault(record.agent_id, []).append(record)

        analysis_period = datetime.now(timezone.utc).strftime(ANALYSIS_PERIOD_FORMAT)
        feature_rows = [build_feature_row(agent_id, recs) for agent_id, recs in by_agent.items()]

        detector = FraudDetector()
        results = detector.score(feature_rows)

        for row, result in zip(feature_rows, results):
            vector_id = f"FV{uuid.uuid4().hex[:8]}"
            session.merge(FeatureVector(
                vector_id=vector_id,
                agent_id=row["agent_id"],
                analysis_period=analysis_period,
                submission_frequency=row["submission_frequency"],
                time_of_day_dist=row["time_of_day_dist"],
                customer_similarity=row["customer_similarity"],
            ))
            session.merge(FraudFlag(
                flag_id=f"FL{uuid.uuid4().hex[:8]}",
                vector_id=vector_id,
                suspicion_score=result.suspicion_score,
                flag_status="flagged" if result.is_flagged else "clear",
                model_version=MODEL_VERSION,
            ))

        session.commit()
        return {"agents_processed": len(feature_rows), "flagged": sum(r.is_flagged for r in results)}
    finally:
        session.close()


if __name__ == "__main__":
    print(run_detection_cycle())