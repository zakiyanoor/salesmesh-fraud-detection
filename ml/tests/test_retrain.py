"""Step 13a retrain command: refits on unlabelled features and sets the cutoff without labels."""

import inspect

import numpy as np
import pandas as pd
import pytest

import detectors
import explain
import labels_guard
import retrain
import scoring

COLUMNS = ["submission_frequency", "time_of_day_entropy", "customer_similarity", "collusion_score"]


def features(n, seed):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"submission_frequency": rng.normal(14, 4, n), "time_of_day_entropy": rng.normal(0.78, 0.04, n),
                       "customer_similarity": rng.normal(0.102, 0.003, n), "collusion_score": np.abs(rng.normal(0, 0.05, n))})
    df.insert(0, "agent_id", [f"A{10000 + i}" for i in range(n)])
    df["analysis_period_start"], df["analysis_period_end"] = "2026-09-01", "2026-10-01"
    return df


def base_bundle():
    train = features(300, 0)
    detector = detectors.fit_lof(train, COLUMNS, n_neighbors=50)
    config = {"model_version": "lof_v3_4f", "model": "lof", "params": {"n_neighbors": 50}, "feature_columns": COLUMNS,
              "model_seed": 42, "threshold": 1.445, "threshold_rule": "min expected cost 5:1", "selection_run": "x"}
    return {**detector.artifact(), "model_version": "lof_v3_4f", "operating_point": config,
            "reference_stats": explain.reference_stats(train, COLUMNS)}


def test_retrain_sets_the_cutoff_from_the_alert_rate_without_labels(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("retrain must not load labels")

    monkeypatch.setattr(labels_guard, "load_labelled", refuse)
    monkeypatch.setattr(labels_guard, "load_labels", refuse)
    new_agents = features(450, 1)
    assert not {"is_fraud", "profile", "ring_id"} & set(new_agents.columns)
    new = retrain.retrain(base_bundle(), new_agents, alert_rate=20 / 150, version_suffix="test")
    output = scoring.score_agents(new, new_agents)
    assert output["flag"].sum() == round(450 * 20 / 150)
    assert new["model_version"] == "lof_v3_4f_rtest"
    assert new["operating_point"]["threshold"] != 1.445
    assert new["reference_stats"]["submission_frequency"]["median"] == pytest.approx(new_agents["submission_frequency"].median())
    assert list(new["feature_columns"]) == COLUMNS


def test_retrain_source_reads_no_label():
    source = inspect.getsource(retrain)
    assert not any(word in source for word in ["labels.csv", "is_fraud", "load_labelled", "load_labels(", "unlock_test_labels"])


def test_quantile_cutoff_by_hand():
    scores = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    assert retrain.quantile_cutoff(scores, 0.4) == 3.5
    assert (scores >= retrain.quantile_cutoff(scores, 0.4)).sum() == 2
