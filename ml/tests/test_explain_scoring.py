import numpy as np
import pandas as pd
import pytest

import detectors
import explain
import scoring

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
            "operating_point": {"threshold": threshold}, "reference_medians": explain.reference_medians(train, COLUMNS)}


def ring_like_agent():
    row = features(1, seed=9)
    row.loc[0, "collusion_score"] = 0.61
    row.loc[0, "agent_id"] = "A99999"
    return row


def test_top_contribution_and_reason_by_hand():
    bundle = bundle_for("isolation_forest", 0.0)
    tops, reasons = explain.explain_rows(bundle["scaler"], COLUMNS, bundle["reference_medians"], ring_like_agent())
    assert tops[0].split(";")[0] == "collusion_score"
    assert reasons[0].startswith("61% of customers also used by other agents vs typical")


def test_weak_deviations_are_not_listed():
    bundle = bundle_for("isolation_forest", 0.0)
    row = features(1, seed=9)
    row[COLUMNS] = [bundle["scaler"].mean_ + np.array([3, 0.1, 0.1, 0.1]) * bundle["scaler"].scale_]
    tops, _ = explain.explain_rows(bundle["scaler"], COLUMNS, bundle["reference_medians"], row)
    assert tops == ["submission_frequency"]


def test_output_schema_and_unflagged_rows():
    bundle = bundle_for("isolation_forest", threshold=0.6)
    out = scoring.score_agents(bundle, pd.concat([features(30, seed=3), ring_like_agent()]))
    assert list(out.columns) == scoring.OUTPUT_COLUMNS
    assert out[["agent_id", "analysis_period_start", "analysis_period_end", "model_version"]].notna().all().all()
    flagged, clear = out[out["flag"]], out[~out["flag"]]
    assert (flagged["top_features"] != "").all() and (flagged["reason"] != scoring.NOT_FLAGGED_REASON).all()
    assert (clear["reason"] == scoring.NOT_FLAGGED_REASON).all()
    assert (out["threshold"] == 0.6).all()


def test_threshold_comes_from_the_bundle_not_the_code():
    data = features(50, seed=4)
    low = scoring.score_agents(bundle_for("isolation_forest", threshold=-1.0), data)
    high = scoring.score_agents(bundle_for("isolation_forest", threshold=10.0), data)
    assert low["flag"].all() and not high["flag"].any()


@pytest.mark.parametrize("model_name", ["isolation_forest", "lof"])
def test_any_detector_can_be_swapped_in_without_code_changes(model_name):
    out = scoring.score_agents(bundle_for(model_name, threshold=0.0), features(20, seed=5))
    assert len(out) == 20 and out["model_version"].iloc[0] == f"{model_name}_test"


def test_explanations_only_for_flagged_agents(monkeypatch):
    calls = []
    original = scoring.explain_rows

    def counting(scaler, columns, reference, df):
        calls.append(len(df))
        return original(scaler, columns, reference, df)

    monkeypatch.setattr(scoring, "explain_rows", counting)
    out = scoring.score_agents(bundle_for("isolation_forest", threshold=0.6), pd.concat([features(30, seed=3), ring_like_agent()]))
    assert calls == [int(out["flag"].sum())]
