"""
Parity (issue #4): scores written by the backend's detection run match the
frozen ML pipeline's scores for the same agents within 1e-9.

The expected scores are the pipeline's own outputs for the 150 validation and
150 test agents (score column only; no label is read).
"""

import pandas as pd

from src import ml_bridge
from src.db import AgentScore, FeatureVector, FraudFlag, get_session

ML_RUNS = ml_bridge.ML_DIR / "runs"
FROZEN_OUTPUTS = [ML_RUNS / "20261013-100433_explain" / "validation_scores.csv",
                  ML_RUNS / "20261013-103859_final_evaluation_s42" / "test_scores.csv"]
TOLERANCE = 1e-9


def stored_scores(run_id):
    db_session = get_session()
    try:
        rows = db_session.query(AgentScore.agent_id, AgentScore.anomaly_score, AgentScore.flagged,
                                AgentScore.reasons, AgentScore.threshold).filter(AgentScore.run_id == run_id).all()
        return pd.DataFrame(rows, columns=["agent_id", "anomaly_score", "flagged", "reasons", "threshold"])
    finally:
        db_session.close()


def test_backend_scores_match_the_ml_pipeline_within_1e_9(database) -> None:
    stored = stored_scores(database["run_id"])
    expected = pd.concat([pd.read_csv(p, usecols=["agent_id", "score", "flag", "threshold", "reason"]) for p in FROZEN_OUTPUTS])
    merged = expected.merge(stored, on="agent_id", how="left", suffixes=("_ml", "_backend"))
    assert len(merged) == 300 and merged["anomaly_score"].notna().all()
    assert (merged["score"] - merged["anomaly_score"]).abs().max() < TOLERANCE
    assert (merged["flag"] == merged["flagged"]).all()
    assert (merged["reason"] == merged["reasons"]).all()
    assert (merged["threshold_ml"] - merged["threshold_backend"]).abs().max() < TOLERANCE


def test_run_scored_every_loaded_agent_with_the_frozen_cutoff(database) -> None:
    stored = stored_scores(database["run_id"])
    assert len(stored) == 1000 and database["agents_scored"] == 1000
    assert stored["threshold"].nunique() == 1
    assert abs(stored["threshold"].iloc[0] - 1.4447993633890617) < TOLERANCE
    assert database["model_version"] == "lof_v3_4f"
    assert database["flagged"] == int(stored["flagged"].sum())


def test_fraud_flags_follow_the_model_flag_only(database) -> None:
    db_session = get_session()
    try:
        rows = (db_session.query(FeatureVector.agent_id, FraudFlag.flag_status, FraudFlag.suspicion_score)
                .join(FraudFlag, FraudFlag.vector_id == FeatureVector.vector_id)
                .filter(FeatureVector.analysis_period == database["analysis_period"]).all())
    finally:
        db_session.close()
    flags = pd.DataFrame(rows, columns=["agent_id", "flag_status", "suspicion_score"])
    stored = stored_scores(database["run_id"]).merge(flags, on="agent_id")
    assert len(stored) == 1000
    assert ((stored["flag_status"] == "flagged") == stored["flagged"]).all()
    assert (stored["suspicion_score"] - stored["anomaly_score"]).abs().max() < TOLERANCE
