"""Scoring service (issue #4): frozen bundle, ML parity, duplicate rule evidence, flag_source. No database."""

import builtins
from pathlib import Path

import pandas as pd
import pytest

from src import ml_bridge, scoring_service
from src.load_data import read_files
from src.scoring_service import REPEAT, SHARED, duplicate_evidence, flag_source, score_frame

ML_RUNS = ml_bridge.ML_DIR / "runs"
FROZEN_OUTPUTS = [ML_RUNS / "20261013-100433_explain" / "validation_scores.csv",
                  ML_RUNS / "20261013-103859_final_evaluation_s42" / "test_scores.csv"]
SRC = Path(__file__).resolve().parents[1] / "src"


@pytest.fixture(scope="module")
def scored():
    frames = read_files()
    return score_frame(frames["activation_records"], frames["agents"][["agent_id", "region"]])


def test_flag_source_values() -> None:
    assert flag_source(True, True) == "Both"
    assert flag_source(True, False) == "ML"
    assert flag_source(False, True) == "Rule"
    assert flag_source(False, False) == "None"


def test_duplicate_evidence_by_hand() -> None:
    acts = pd.DataFrame([
        ("R1", "A1", "2026-08-01 10:00", "CUST1", "CL01", "banking", "completed"),
        ("R2", "A2", "2026-08-02 10:00", "CUST1", "CL01", "banking", "completed"),
        ("R3", "A3", "2026-08-01 10:00", "CUST2", "CL01", "banking", "completed"),
        ("R4", "A3", "2026-08-02 10:00", "CUST2", "CL01", "banking", "failed"),
        ("R5", "A4", "2026-08-01 10:00", "CUST3", "CL01", "banking", "failed"),
        ("R6", "A4", "2026-08-02 10:00", "CUST3", "CL01", "banking", "completed"),
        ("R7", "A4", "2026-08-03 10:00", "CUST3", "CL02", "banking", "completed"),
    ], columns=scoring_service.RECORD_COLUMNS)
    evidence = duplicate_evidence(acts)
    shared = evidence[evidence["reason"] == SHARED]
    assert set(zip(shared["agent_id"], shared["other_agent_id"])) == {("A1", "A2"), ("A2", "A1")}
    repeat = evidence[evidence["reason"] == REPEAT]
    assert repeat[["agent_id", "customer_id", "record_ids"]].values.tolist() == [["A3", "CUST2", "R3,R4"]]
    counts = ml_bridge.duplicate_activation_counts(acts)
    assert counts.to_dict() == {"A1": 1, "A2": 1, "A3": 1, "A4": 0}


def test_frozen_bundle_is_the_v3_lof_model_with_the_validation_cutoff() -> None:
    bundle = ml_bridge.load_frozen_bundle()
    assert bundle["model_version"] == "lof_v3_4f"
    assert bundle["name"] == "lof" and bundle["model"].n_neighbors == 50
    assert bundle["operating_point"]["threshold"] == pytest.approx(1.4447993633890617, abs=0)
    assert list(bundle["feature_columns"]) == ml_bridge.MODEL_FEATURES


def test_changed_bundle_is_refused(monkeypatch) -> None:
    ml_bridge.load_frozen_bundle.cache_clear()
    monkeypatch.setattr(ml_bridge, "frozen_bundle_hash", lambda: "0" * 64)
    try:
        with pytest.raises(ml_bridge.FrozenModelError, match="hash"):
            ml_bridge.load_frozen_bundle()
    finally:
        ml_bridge.load_frozen_bundle.cache_clear()


def test_scores_match_the_frozen_ml_pipeline(scored) -> None:
    scores, _, _ = scored
    expected = pd.concat([pd.read_csv(p) for p in FROZEN_OUTPUTS])
    merged = expected.merge(scores, on="agent_id")
    assert len(merged) == 300
    assert (merged["score"] - merged["anomaly_score"]).abs().max() < 1e-9
    assert (merged["flag"] == merged["flagged"]).all()
    assert (merged["reason"] == merged["reasons"]).all()


def test_every_agent_is_scored_and_flag_source_is_consistent(scored) -> None:
    scores, features, evidence = scored
    assert len(scores) == 1000 and scores["agent_id"].is_unique
    assert set(scores["flag_source"]) <= {"ML", "Rule", "Both", "None"}
    expected = [flag_source(m, r) for m, r in zip(scores["flagged"], scores["rule_flagged"])]
    assert scores["flag_source"].tolist() == expected
    assert (scores["flagged"] == (scores["anomaly_score"] >= scores["threshold"])).all()
    assert (scores["rule_flagged"] == (scores["duplicate_pairs"] > 0)).all()
    per_agent = evidence.drop_duplicates(["agent_id", "customer_id", "client_id"]).groupby("agent_id").size()
    assert per_agent.reindex(scores["agent_id"], fill_value=0).tolist() == scores["duplicate_pairs"].tolist()


def test_scoring_never_reads_labels_or_rings(monkeypatch) -> None:
    opened = []
    real_open = builtins.open

    def spy(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    ml_bridge.load_frozen_bundle.cache_clear()
    frames = read_files()
    score_frame(frames["activation_records"].head(5000), frames["agents"][["agent_id", "region"]].head(100))
    assert not [p for p in opened if Path(p).name in {"labels.csv", "rings.csv"}]


def test_backend_never_references_v2_artifacts_or_leftovers() -> None:
    stale = ["isolation_forest_v2", "fraud_flags.csv", "fraud_flags_lof.csv", "train_test_split.csv",
             "activation_records_clean.csv", "feature_vectors.csv", "labels.csv", "rings.csv"]
    import ast

    for path in SRC.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                      if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
                      and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
        strings = [n.value for n in ast.walk(tree)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings]
        allowed = {"labels.csv", "rings.csv"} if path.name == "load_data.py" else set()
        found = [s for s in stale if s not in allowed and any(s in value for value in strings)]
        assert not found, f"{path.name} uses {found}"
