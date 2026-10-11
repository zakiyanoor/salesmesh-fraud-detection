import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

import learning_curve
import selection


def test_weighted_average_precision_matches_sklearn():
    rng = np.random.default_rng(3)
    y = rng.random(150) < 0.13
    scores = rng.random(150) + 0.3 * y
    weights = selection.bootstrap_weights(y, resamples=20, seed=1)
    ours = selection.weighted_average_precision(y, scores, weights)
    theirs = [average_precision_score(y, scores, sample_weight=w) for w in weights]
    np.testing.assert_allclose(ours, theirs)
    assert (weights * y).sum(axis=1).min() > 0


def test_ci_overlap_share_by_hand():
    assert selection.ci_overlap_share(0.0, 1.0, 0.5, 1.5) == 0.5
    assert selection.ci_overlap_share(0.0, 1.0, 0.2, 0.4) == 1.0
    assert selection.ci_overlap_share(0.0, 1.0, 2.0, 3.0) == 0.0


def grid_row(name, n_features, mean, low, high, size):
    return {"model": name, "features": f"{n_features} features", "n_features": n_features, "pr_auc_mean": mean,
            "pr_auc_ci_low": low, "pr_auc_ci_high": high, "model_bytes": size}


def test_original_rule_prefers_four_features_within_margin():
    grid = pd.DataFrame([grid_row("a", 5, 0.80, 0.70, 0.90, 100), grid_row("b", 4, 0.79, 0.69, 0.89, 500),
                         grid_row("c", 4, 0.60, 0.59, 0.61, 50)])
    chosen, ties, top = selection.choose_original(grid)
    assert top["model"] == "a" and chosen["model"] == "b"
    assert "c" not in set(ties["model"])


def test_original_rule_uses_heavy_ci_overlap_and_then_model_size():
    grid = pd.DataFrame([grid_row("a", 4, 0.80, 0.60, 1.00, 900), grid_row("b", 4, 0.70, 0.55, 0.95, 100)])
    chosen, ties, _ = selection.choose_original(grid)
    assert len(ties) == 2 and chosen["model"] == "b"


def test_min_cost_count_by_hand():
    y = np.array([1, 0, 1, 0, 0])
    scores = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    k, cost = selection.min_cost_count(y, scores, ratio=5)
    # k=0 -> 10, k=1 -> 5, k=2 -> 6, k=3 -> 1, k=4 -> 2, k=5 -> 3
    assert cost.tolist() == [10, 5, 6, 1, 2, 3] and k == 3
    k2, _ = selection.min_cost_count(y, scores, ratio=0.5)
    assert k2 == 1  # flag only the first: 0.5*1 + 0 = 0.5 vs k=0: 1.0


def test_cutoff_sits_between_flagged_and_unflagged():
    scores = np.array([5.0, 4.0, 3.0, 2.0])
    assert selection.midpoint_cutoff(scores, 2) == 3.5
    assert (scores >= selection.midpoint_cutoff(scores, 2)).sum() == 2


def test_operating_points_report_every_rule():
    rng = np.random.default_rng(0)
    y = rng.random(100) < 0.15
    scores = rng.random(100) + y
    points = selection.operating_points(y, scores, np.where(y, "ring", "legit"))
    assert {"min expected cost 5:1", "min expected cost 2:1", "min expected cost 10:1", "max F1",
            "alert budget 15%"} == set(points["rule"])
    assert {"precision", "recall", "f1", "alert_rate"} <= set(points.columns)


def test_learning_curve_subsample_is_stratified():
    train = pd.DataFrame({"agent_id": range(200), "is_fraud": [True] * 40 + [False] * 160,
                          "profile": ["ring"] * 20 + ["weak"] * 20 + ["legit"] * 160})
    part = learning_curve.subsample(train, 0.25, seed=1)
    assert len(part) == 50 and part["profile"].value_counts().to_dict() == {"legit": 40, "ring": 5, "weak": 5}
    assert learning_curve.subsample(train, 1.0, seed=1) is train


@pytest.mark.parametrize("module", ["selection.py", "learning_curve.py"])
def test_step_9_code_never_asks_for_test_labels(module):
    from pathlib import Path

    source = (Path(selection.__file__).parent / module).read_text(encoding="utf-8")
    assert "unlock_test_labels" not in source
    assert '"test"' not in source and "'test'" not in source


def amended_row(name, n_features, mean, trees, samples, ms, low=0.5, high=0.95):
    return {**grid_row(name, n_features, mean, low, high, 1), "n_estimators": trees, "max_samples": samples,
            "score_ms_per_agent": ms}


def test_amended_rule_ignores_ci_overlap():
    grid = pd.DataFrame([amended_row("a", 4, 0.80, 500, 64, 0.2), amended_row("b", 4, 0.70, 100, 64, 0.1)])
    chosen, ties, _ = selection.choose(grid)
    assert list(ties["model"]) == ["a"] and chosen["model"] == "a"


def test_amended_rule_simplicity_order():
    grid = pd.DataFrame([
        amended_row("five", 5, 0.800, 100, 64, 0.01),
        amended_row("many_trees", 4, 0.799, 500, 64, 0.01),
        amended_row("big_sample", 4, 0.795, 100, 256, 0.01),
        amended_row("slow", 4, 0.790, 100, 64, 0.09),
        amended_row("fast", 4, 0.785, 100, 64, 0.05),
        amended_row("outside", 4, 0.700, 50, 32, 0.01),
    ])
    chosen, ties, _ = selection.choose(grid)
    assert "outside" not in set(ties["model"])
    assert chosen["model"] == "fast"


def test_acceptance_checks_on_validation_report_q1_to_q6():
    rng = np.random.default_rng(0)
    y = rng.random(150) < 0.13
    scores = rng.random(150) + 2 * y
    table = selection.acceptance_on_validation({"pr_auc_mean": 0.9}, y, scores, 0.95, cutoff=1.5)
    assert list(table["criterion"]) == ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]
    assert set(table["result"]) <= {"PASS", "FAIL"}
