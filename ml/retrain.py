"""
Step 13a: retrain command (periodic retraining). Reads NO label.

Refits the scaler and the model of the current scoring bundle (same model,
settings, seed and 4 features) on new unlabelled agent features, recomputes the
explanation reference statistics (median, IQR, P5, P95) on the same agents, and
sets the cutoff without labels: the score quantile that flags the validated
alert rate. That rate comes from the selection run's chosen operating point
(min expected cost 5:1: 20 of 150 validation agents, 13.3%); it is a number,
not a label. The new bundle gets its own model_version, which every score row
carries.

Usage: python retrain.py (--features CSV | --splits train,validation) [--bundle PATH] [--alert-rate R]
Output: ml/runs/<run_id>/ with scoring_bundle.joblib, operating_point.json and retrain_report.json
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from data_generation import DEFAULT_OUT_DIR
from detectors import FITTERS
from explain import EXPLANATION_METHOD, reference_stats
from run_utils import RUNS_DIR
from scoring import score_agents


def validated_alert_rate(bundle):
    """Alert rate of the chosen operating point, read from the selection run (a result file, not labels)."""
    config = bundle["operating_point"]
    points = pd.read_csv(RUNS_DIR / config["selection_run"] / "operating_points.csv")
    return float(points.loc[points["rule"] == config["threshold_rule"], "alert_rate"].iloc[0])


def quantile_cutoff(scores, alert_rate):
    """Cutoff that flags round(alert_rate * n) agents: halfway between the last flagged and first unflagged score."""
    ordered = np.sort(np.asarray(scores, dtype=float))[::-1]
    k = int(round(alert_rate * len(ordered)))
    if k <= 0:
        return float(ordered[0]) + 1e-9
    if k >= len(ordered):
        return float(ordered[-1])
    return float((ordered[k - 1] + ordered[k]) / 2)


def retrain(bundle, features, alert_rate, version_suffix=None):
    """New bundle fitted on unlabelled features; the cutoff flags alert_rate of these agents."""
    config = bundle["operating_point"]
    columns = list(bundle["feature_columns"])
    detector = FITTERS[bundle["name"]](features, columns, config["model_seed"], **config["params"])
    cutoff = quantile_cutoff(detector.score(features), alert_rate)
    base_version = config.get("base_model_version", bundle["model_version"])
    model_version = f"{base_version}_r{version_suffix or datetime.now().strftime('%Y%m%d-%H%M%S')}"
    operating_point = {**config, "model_version": model_version, "base_model_version": base_version,
                       "threshold": cutoff, "threshold_rule": f"score quantile for alert rate {alert_rate:.4f} (no labels)",
                       "alert_rate_target": alert_rate, "retrained_on_agents": len(features)}
    return {**detector.artifact(), "model_version": model_version, "operating_point": operating_point,
            "reference_stats": reference_stats(features, columns), "explanation_method": EXPLANATION_METHOD}


def main(argv=None):
    from labels_guard import load_unlabelled
    from run_utils import start_run
    from system_checks import latest_explain_run

    parser = argparse.ArgumentParser(description="Retrain the scoring bundle on unlabelled agent features.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--features", type=Path, help="CSV of agent feature vectors (no labels)")
    source.add_argument("--splits", help="comma-separated splits of data/synthetic/feature_vectors.csv, e.g. train,validation")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bundle", type=Path, default=None)
    parser.add_argument("--alert-rate", type=float, default=None)
    args = parser.parse_args(argv)

    bundle_path = args.bundle or latest_explain_run() / "scoring_bundle.joblib"
    bundle = joblib.load(bundle_path)
    if args.features:
        features, inputs = pd.read_csv(args.features), [args.features]
    else:
        features = pd.concat([load_unlabelled(args.data_dir, s) for s in args.splits.split(",")], ignore_index=True)
        inputs = [args.data_dir / "feature_vectors.csv", args.data_dir / "split.csv"]
    alert_rate = args.alert_rate if args.alert_rate is not None else validated_alert_rate(bundle)
    new = retrain(bundle, features, alert_rate)

    run_dir = start_run("retrain", new["operating_point"]["model_seed"], {
        "base_bundle": str(bundle_path), "alert_rate": alert_rate, "agents": len(features),
        "source": str(args.features or args.splits), "labels_read": False}, inputs + [bundle_path])
    joblib.dump(new, run_dir / "scoring_bundle.joblib")
    (run_dir / "operating_point.json").write_text(json.dumps(new["operating_point"], indent=2, default=str), encoding="utf-8")
    output = score_agents(new, features)
    report = {"model_version": new["model_version"], "agents": len(features), "cutoff": new["operating_point"]["threshold"],
              "alert_rate_target": alert_rate, "flagged": int(output["flag"].sum()),
              "alert_rate_achieved": float(output["flag"].mean())}
    (run_dir / "retrain_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    output.to_csv(run_dir / "scores.csv", index=False)
    print(json.dumps(report, indent=2))
    print(f"Run folder {run_dir}")


if __name__ == "__main__":
    main()
