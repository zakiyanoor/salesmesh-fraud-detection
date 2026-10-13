import numpy as np
import pandas as pd
import pytest

import preprocessing as pp
from feature_engineering import FEATURE_COLUMNS


def make_parts(seed=0):
    rng = np.random.default_rng(seed)
    parts = {}
    for name, n, shift in [("train", 70, 0.0), ("validation", 15, 5.0), ("test", 15, -5.0)]:
        frame = pd.DataFrame(rng.normal(shift, 1 + shift ** 2, (n, len(FEATURE_COLUMNS))), columns=FEATURE_COLUMNS)
        frame.insert(0, "agent_id", [f"A{name[0]}{i}" for i in range(n)])
        parts[name] = frame
    return parts


def test_scaler_statistics_come_from_training_only():
    parts = make_parts()
    scaler = pp.fit_scaler(parts["train"])
    train = parts["train"][FEATURE_COLUMNS]
    np.testing.assert_allclose(scaler.mean_, train.mean().values)
    np.testing.assert_allclose(scaler.scale_, train.std(ddof=0).values)
    everything = pd.concat(parts.values())[FEATURE_COLUMNS]
    assert not np.allclose(scaler.mean_, everything.mean().values)


def test_changing_validation_or_test_does_not_change_the_scaler():
    parts = make_parts()
    before = pp.fit_scaler(parts["train"])
    parts["validation"][FEATURE_COLUMNS] *= 100
    parts["test"][FEATURE_COLUMNS] += 1000
    after = pp.fit_scaler(parts["train"])
    np.testing.assert_array_equal(before.mean_, after.mean_)
    np.testing.assert_array_equal(before.scale_, after.scale_)


def test_validation_is_transformed_with_training_statistics():
    parts = make_parts()
    scaler = pp.fit_scaler(parts["train"])
    expected = (parts["validation"][FEATURE_COLUMNS].values - scaler.mean_) / scaler.scale_
    np.testing.assert_allclose(pp.scaled_features(scaler, parts["validation"]), expected)


def test_saved_scaler_round_trips(tmp_path):
    parts = make_parts()
    scaler = pp.fit_scaler(parts["train"])
    pp.save_scaler(scaler, tmp_path / "scaler.joblib", FEATURE_COLUMNS, len(parts["train"]))
    import joblib

    saved = joblib.load(tmp_path / "scaler.joblib")
    assert saved["fitted_on"] == "train" and saved["feature_columns"] == list(FEATURE_COLUMNS)
    np.testing.assert_array_equal(saved["scaler"].mean_, scaler.mean_)


@pytest.mark.skipif(not (pp.DEFAULT_OUT_DIR / "split.csv").exists(), reason="pipeline outputs not generated")
def test_real_scaler_matches_training_agents():
    parts = pp.load_partitions()
    scaler = pp.fit_scaler(parts["train"])
    np.testing.assert_allclose(scaler.mean_, parts["train"][FEATURE_COLUMNS].mean().values)
    assert len(parts["train"]) == 700
