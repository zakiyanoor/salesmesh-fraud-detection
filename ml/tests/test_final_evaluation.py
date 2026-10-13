"""Step 11 script: read-once guard, hash check, and a full run on a substitute dataset (never the real test set)."""

import json

import pandas as pd
import pytest
from sklearn.model_selection import train_test_split

import data_generation as dg
import detectors
import explain
import final_evaluation as fe
import labels_guard
import retrain
import selection
from clean_data import clean_data
from feature_engineering import MODEL_FEATURES, compute_feature_vectors
from split import strata


def test_marker_blocks_a_second_run(tmp_path, monkeypatch):
    marker = tmp_path / "test_read_once.json"
    marker.write_text(json.dumps({"run_id": "x"}))

    def refuse(*args, **kwargs):
        raise AssertionError("labels must not be touched")

    monkeypatch.setattr(fe, "MARKER", marker)
    monkeypatch.setattr(labels_guard, "unlock_test_labels", refuse)
    monkeypatch.setattr(labels_guard, "load_labelled", refuse)
    monkeypatch.setattr(fe, "verify_freeze", refuse)
    with pytest.raises(SystemExit, match="already been read once"):
        fe.main()
    with pytest.raises(SystemExit):
        fe.refuse_if_already_run(marker)
    fe.refuse_if_already_run(tmp_path / "absent.json")


def test_real_marker_blocks_a_second_run(monkeypatch):
    if not fe.MARKER.exists():
        pytest.skip("Step 11 has not been run")

    def refuse(*args, **kwargs):
        raise AssertionError("labels must not be touched")

    monkeypatch.setattr(labels_guard, "unlock_test_labels", refuse)
    monkeypatch.setattr(labels_guard, "load_labelled", refuse)
    with pytest.raises(SystemExit, match="already been read once"):
        fe.main()
    record = json.loads(fe.MARKER.read_text(encoding="utf-8"))
    assert {"timestamp", "run_id", "hashes"} <= set(record)


def test_freeze_hashes_all_match():
    hashes = fe.verify_freeze()
    assert len(hashes) >= 16
    assert all(expected == actual for _, expected, actual in hashes)


@pytest.fixture(scope="module")
def substitute():
    data = dg.generate_dataset(101, n_agents=400, fraud_rate=0.2)
    clean = clean_data(data.activations, data.agents, data.clients)[0]
    features = compute_feature_vectors(clean, data.agents).merge(data.labels, on="agent_id")
    stratum = strata(features)
    train, rest = train_test_split(features, train_size=0.7, stratify=stratum, random_state=42)
    val, test = train_test_split(rest, test_size=0.5, stratify=strata(rest), random_state=42)
    detector = detectors.fit_lof(train, MODEL_FEATURES, n_neighbors=50)
    val_scores = detector.score(val)
    points = selection.operating_points(val["is_fraud"].values, val_scores, val["profile"].values)
    config = {"model_version": "lof_v3_4f", "model": "lof", "params": {"n_neighbors": 50}, "feature_columns": MODEL_FEATURES,
              "model_seed": 42, "threshold": float(points.iloc[0]["cutoff"]), "threshold_rule": points.iloc[0]["rule"]}
    bundle = {**detector.artifact(), "model_version": "lof_v3_4f", "operating_point": config,
              "reference_stats": explain.reference_stats(train, MODEL_FEATURES)}
    parts = {"train": train.reset_index(drop=True), "validation": val.reset_index(drop=True), "test": test.reset_index(drop=True)}
    return parts, features.drop(columns=["is_fraud", "profile", "ring_id"]), clean, data.agents, bundle, points


@pytest.fixture(autouse=True)
def few_resamples(monkeypatch):
    monkeypatch.setattr(fe, "BOOTSTRAP_RESAMPLES", 50)


def test_full_evaluation_on_substitute_data(substitute, tmp_path):
    parts, all_features, clean, agents, bundle, points = substitute
    summary = fe.evaluate_test(parts, all_features, clean, agents, bundle, points, tmp_path)
    metrics = pd.read_csv(tmp_path / "test_metrics.csv")
    assert metrics["role"].tolist()[0] == "primary" and metrics["role"].tolist()[-1].startswith("secondary")
    assert (metrics["pr_auc_ci_low"] <= metrics["pr_auc"]).all() and (metrics["pr_auc"] <= metrics["pr_auc_ci_high"]).all()
    assert len(pd.read_csv(tmp_path / "cost_sensitivity.csv")) == 5
    for name in ["fig11_precision_recall", "fig12_roc", "fig13_score_distribution", "fig14_confusion_matrix",
                 "fig15_recall_by_pattern"]:
        assert (tmp_path / f"{name}.png").exists() and (tmp_path / f"{name}.caption.txt").exists()
    errors = pd.read_csv(tmp_path / "error_analysis.csv")
    assert set(errors["error"]) <= {"missed fraud", "false alarm"} and errors["explanation"].notna().all()
    assert set(summary["acceptance"]) == {"Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "S1", "S2", "S3", "S4"}
    assert summary["test_agents"] == len(parts["test"])
    model_flags = pd.read_csv(tmp_path / "test_scores.csv")["flag"]
    assert model_flags.sum() == metrics.iloc[0]["flagged"]
    assert retrain.quantile_cutoff is not None


def test_cutoff_is_never_chosen_on_test(substitute, tmp_path):
    parts, all_features, clean, agents, bundle, points = substitute
    fe.evaluate_test(parts, all_features, clean, agents, bundle, points, tmp_path)
    scores = pd.read_csv(tmp_path / "test_scores.csv")
    assert scores["threshold"].sub(bundle["operating_point"]["threshold"]).abs().max() < 1e-9
    costs = pd.read_csv(tmp_path / "cost_sensitivity.csv")
    assert (costs["cutoff"] - points["cutoff"].values).abs().max() < 1e-9
