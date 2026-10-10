import numpy as np
import pandas as pd
import pytest

import detectors
import metrics


def test_budget_flags_take_the_top_share_rounded_up():
    flags = metrics.budget_flags(np.arange(20), budget=0.15)
    assert flags.sum() == 3 and flags[-3:].all()


def test_evaluate_by_hand():
    y = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
    scores = [0.9, 0.1, 0.8, 0.2, 0.3, 0.4, 0.0, 0.05, 0.06, 0.07]
    profiles = ["ring", "weak", *["legit"] * 8]
    result = metrics.evaluate(y, scores, profiles, budget=0.2)  # flags 0.9 and 0.8
    assert (result["tp"], result["fp"], result["fn"]) == (1, 1, 1)
    assert result["precision"] == 0.5 and result["recall"] == 0.5
    assert result["recall_ring"] == 1.0 and result["recall_weak"] == 0.0
    assert result["pr_auc_random"] == 0.2
    assert metrics.direction_free(0.3) == 0.7


def frame(rows, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.normal(0, 1, (rows, 3)), columns=["a", "b", "c"])


@pytest.mark.parametrize("name", ["isolation_forest", "lof"])
def test_scores_are_higher_for_an_obvious_outlier(name):
    train = frame(300)
    detector = detectors.FITTERS[name](train, ["a", "b", "c"])
    test = pd.DataFrame({"a": [0.0, 8.0], "b": [0.0, 8.0], "c": [0.0, -8.0]})
    normal, outlier = detector.score(test)
    assert outlier > normal


@pytest.mark.parametrize("name", ["isolation_forest", "lof"])
def test_detectors_fit_their_scaler_on_training_only(name):
    train = frame(200)
    detector = detectors.FITTERS[name](train, ["a", "b", "c"])
    np.testing.assert_allclose(detector.scaler.mean_, train.mean().values)
    assert len(detector.training_scores(train)) == len(train)


def test_isolation_forest_is_deterministic_for_a_seed():
    train, val = frame(200), frame(50, seed=1)
    a = detectors.fit_isolation_forest(train, ["a", "b", "c"], seed=7).score(val)
    b = detectors.fit_isolation_forest(train, ["a", "b", "c"], seed=7).score(val)
    np.testing.assert_array_equal(a, b)


def test_lof_uses_novelty_mode():
    detector = detectors.fit_lof(frame(100), ["a", "b", "c"])
    assert detector.model.novelty is True and detector.model.n_neighbors == 20
