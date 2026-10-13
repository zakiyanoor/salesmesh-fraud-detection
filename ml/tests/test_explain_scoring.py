import numpy as np
import pandas as pd
import pytest

import detectors
import explain
import scoring
import system_checks

COLUMNS = ["submission_frequency", "time_of_day_entropy", "customer_similarity", "collusion_score"]


def features(n=200, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "submission_frequency": rng.normal(14, 3, n), "time_of_day_entropy": rng.normal(0.79, 0.03, n),
        "customer_similarity": rng.normal(0.10, 0.003, n), "collusion_score": np.abs(rng.normal(0, 0.02, n)),
    })
    df.insert(0, "agent_id", [f"A{10000 + i}" for i in range(n)])
    df["analysis_period_start"], df["analysis_period_end"] = "2026-08-01", "2026-08-31"
    return df


def bundle_for(model_name, threshold):
    train = features()
    detector = detectors.FITTERS[model_name](train, COLUMNS)
    return {**detector.artifact(), "model_version": f"{model_name}_test",
            "operating_point": {"threshold": threshold}, "reference_stats": explain.reference_stats(train, COLUMNS)}


def ring_like_agent():
    row = features(1, seed=9)
    row.loc[0, "collusion_score"] = 0.61
    row.loc[0, "agent_id"] = "A99999"
    return row


def test_reference_stats_are_training_median_and_iqr():
    train = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 100.0]})
    stats = explain.reference_stats(train, ["x"])["x"]
    assert stats["median"] == 3.0 and stats["iqr"] == 2.0


def test_robust_deviation_by_hand_and_iqr_floor():
    reference = {"a": {"median": 10.0, "iqr": 2.0}, "b": {"median": 0.0, "iqr": 0.0}}
    row = pd.DataFrame({"a": [14.0], "b": [0.002]})
    d = explain.deviations(reference, ["a", "b"], row)
    assert d[0, 0] == 2.0
    assert d[0, 1] == pytest.approx(0.002 / explain.IQR_FLOOR)


def test_outliers_do_not_hide_a_moderate_deviation():
    # 90 typical agents, 10 extreme ones: the SD is inflated, the IQR is not
    train = pd.DataFrame({"s": [0.10] * 45 + [0.104] * 45 + [0.45] * 10})
    reference = explain.reference_stats(train, ["s"])
    moderate = pd.DataFrame({"s": [0.12]})
    robust = explain.deviations(reference, ["s"], moderate)[0, 0]
    z = (0.12 - train["s"].mean()) / train["s"].std(ddof=0)
    assert robust > 3 and abs(z) < 1


def test_top_contribution_and_reason_by_hand():
    bundle = bundle_for("isolation_forest", 0.0)
    row = ring_like_agent()
    assert explain.top_features(bundle["reference_stats"], COLUMNS, row)[0].split(";")[0] == "collusion_score"
    assert explain.reasons(bundle["reference_stats"], COLUMNS, row)[0].startswith("61% of customers also used by other agents")


def test_reason_skips_features_that_are_not_unusual():
    reference = {c: {"median": 0.0, "iqr": 1.0} for c in COLUMNS}
    row = pd.DataFrame({"submission_frequency": [5.0], "time_of_day_entropy": [0.5],
                        "customer_similarity": [0.2], "collusion_score": [0.1]})
    assert explain.top_features(reference, COLUMNS, row) == ["submission_frequency;time_of_day_entropy;customer_similarity"]
    assert explain.reasons(reference, COLUMNS, row)[0].count(";") == 0


def test_reason_display_rule_needs_iqr_and_range_size():
    # tiny IQR: 0.002 above the median is 2 IQRs but only 2% of the P5-P95 range (0.1), so it is not shown
    reference = {"customer_similarity": {"median": 0.102, "iqr": 0.001, "p5": 0.098, "p95": 0.198},
                 "collusion_score": {"median": 0.0, "iqr": 0.01, "p5": 0.0, "p95": 0.5}}
    columns = ["customer_similarity", "collusion_score"]
    small = pd.DataFrame({"customer_similarity": [0.104], "collusion_score": [0.30]})
    assert explain.reasons(reference, columns, small) == ["30% of customers also used by other agents vs typical 0%"]
    large = pd.DataFrame({"customer_similarity": [0.120], "collusion_score": [0.30]})
    assert explain.reasons(reference, columns, large)[0].count(";") == 1
    neither = pd.DataFrame({"customer_similarity": [0.1025], "collusion_score": [0.004]})
    assert explain.reasons(reference, columns, neither) == [explain.COMBINATION_REASON]
    assert explain.shown_in_reason(reference["collusion_score"], 0.05, 5.0)
    assert not explain.shown_in_reason(reference["collusion_score"], 0.04, 4.0)


def test_reason_adds_training_percentile():
    stats = explain.reference_stats(pd.DataFrame({"x": np.arange(100.0)}), ["x"])["x"]
    assert explain.percentile_phrase(stats, 98.5) == " (higher than 99 percent of training agents)"
    assert explain.percentile_phrase(stats, 2.0) == " (lower than 97 percent of training agents)"
    assert explain.percentile_phrase({"median": 0.0}, 1.0) == ""
    reference = {"collusion_score": {**explain.reference_stats(
        pd.DataFrame({"collusion_score": np.linspace(0, 0.5, 101)}), ["collusion_score"])["collusion_score"],
        "median": 0.0, "iqr": 0.01}}
    row = pd.DataFrame({"collusion_score": [0.30]})
    assert explain.reasons(reference, ["collusion_score"], row) == [
        "30% of customers also used by other agents vs typical 0% (higher than 59 percent of training agents)"]


def test_reference_stats_include_p5_and_p95():
    stats = explain.reference_stats(pd.DataFrame({"x": np.arange(101.0)}), ["x"])["x"]
    assert stats["p5"] == 5.0 and stats["p95"] == 95.0


def test_output_schema_top_features_on_every_row_reason_only_when_flagged():
    bundle = bundle_for("isolation_forest", threshold=0.6)
    out = scoring.score_agents(bundle, pd.concat([features(30, seed=3), ring_like_agent()]))
    assert list(out.columns) == scoring.OUTPUT_COLUMNS
    assert system_checks.schema_problems(out) == []
    assert (out["top_features"].str.count(";") == 2).all()
    assert (out.loc[out["flag"], "reason"] != scoring.NOT_FLAGGED_REASON).all()
    assert (out.loc[~out["flag"], "reason"] == scoring.NOT_FLAGGED_REASON).all()
    assert (out["threshold"] == 0.6).all()


def test_schema_check_catches_an_empty_field():
    out = scoring.score_agents(bundle_for("isolation_forest", 0.6), features(5, seed=3))
    out.loc[0, "top_features"] = ""
    assert system_checks.schema_problems(out) == ["top_features: 1 empty"]


def test_threshold_comes_from_the_bundle_not_the_code():
    data = features(50, seed=4)
    low = scoring.score_agents(bundle_for("isolation_forest", threshold=-1.0), data)
    high = scoring.score_agents(bundle_for("isolation_forest", threshold=10.0), data)
    assert low["flag"].all() and not high["flag"].any()


@pytest.mark.parametrize("model_name", ["isolation_forest", "lof"])
def test_any_detector_can_be_swapped_in_without_code_changes(model_name):
    out = scoring.score_agents(bundle_for(model_name, threshold=0.0), features(20, seed=5))
    assert len(out) == 20 and out["model_version"].iloc[0] == f"{model_name}_test"


def test_explanations_do_not_change_scores_or_flags():
    bundle = bundle_for("isolation_forest", threshold=0.6)
    data = pd.concat([features(30, seed=3), ring_like_agent()])
    out = scoring.score_agents(bundle, data)
    raw = scoring.detector_from(bundle).score(data)
    np.testing.assert_array_equal(out["score"].values, raw)
    np.testing.assert_array_equal(out["flag"].values, raw >= 0.6)
