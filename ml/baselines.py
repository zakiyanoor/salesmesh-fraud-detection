"""
Baselines (Step 7): fitted on TRAINING agents, evaluated on VALIDATION agents.

(a) trivial: seeded random scores, averaged over RANDOM_SEEDS;
(b) rule (Chapter 1, fixed volume cap): flag submission_frequency above the
    RULE_PERCENTILE of training agents; its score is submission_frequency;
(c) each feature alone as an anomaly score, in the direction with the higher
    TRAINING AUC (decided on training only).
Test labels are never loaded (labels_guard).

Usage: python baselines.py [--data-dir DIR]
Output: ml/runs/<run_id>/ with run_info.json, baseline_metrics.csv, single_feature_directions.csv
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from data_generation import DEFAULT_OUT_DIR
from feature_engineering import ALL_FEATURES
from labels_guard import load_labelled
from metrics import ALERT_BUDGET, FRAUD_PATTERNS, direction_free, evaluate

RANDOM_SEEDS = range(20)
RULE_FEATURE = "submission_frequency"
RULE_PERCENTILE = 0.90


def feature_directions(train):
    """+1 if higher values are more fraud-like on training agents, else -1."""
    rows = []
    for feature in ALL_FEATURES:
        auc = roc_auc_score(train["is_fraud"], train[feature])
        rows.append({"feature": feature, "train_auc_raw": auc, "train_strength": direction_free(auc),
                     "direction": 1 if auc >= 0.5 else -1})
    return pd.DataFrame(rows).set_index("feature")


def run_baselines(data_dir=DEFAULT_OUT_DIR):
    parts = load_labelled(data_dir, ["train", "validation"])
    train, val = parts["train"], parts["validation"]
    y, profiles = val["is_fraud"].values, val["profile"].values
    rows = []

    random_runs = pd.DataFrame([evaluate(y, np.random.default_rng(seed).random(len(val)), profiles)
                                for seed in RANDOM_SEEDS])
    rows.append({"baseline": f"random scores (mean of {len(RANDOM_SEEDS)} seeds)", **random_runs.mean().to_dict(),
                 "random_std_roc_auc": random_runs["roc_auc"].std(), "random_std_pr_auc": random_runs["pr_auc"].std()})

    cap = float(train[RULE_FEATURE].quantile(RULE_PERCENTILE))
    rule_flags = val[RULE_FEATURE].values > cap
    rows.append({"baseline": f"rule: {RULE_FEATURE} > training P{int(RULE_PERCENTILE * 100)} ({cap:g})",
                 **evaluate(y, val[RULE_FEATURE].values, profiles, flags=rule_flags)})

    directions = feature_directions(train)
    for feature, d in directions.iterrows():
        scores = d["direction"] * val[feature].values
        result = evaluate(y, scores, profiles)
        raw_auc = roc_auc_score(y, val[feature].values)
        rows.append({"baseline": f"single feature: {feature} ({'+' if d['direction'] > 0 else '-'})", **result,
                     "val_auc_raw": raw_auc, "val_strength": direction_free(raw_auc)})
    return pd.DataFrame(rows), directions, len(train), len(val), int(val["is_fraud"].sum())


def main(argv=None):
    from run_utils import start_run

    parser = argparse.ArgumentParser(description="Step 7 baselines on validation.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    inputs = [args.data_dir / f for f in ["feature_vectors.csv", "split.csv", "labels.csv"]]
    table, directions, n_train, n_val, n_val_fraud = run_baselines(args.data_dir)
    run_dir = start_run("baselines", None, {"alert_budget": ALERT_BUDGET, "random_seeds": list(RANDOM_SEEDS),
                                            "rule": f"{RULE_FEATURE} > train P{RULE_PERCENTILE}",
                                            "evaluated_on": "validation", "fitted_on": "train"}, inputs)
    table.to_csv(run_dir / "baseline_metrics.csv", index=False)
    directions.to_csv(run_dir / "single_feature_directions.csv")

    cols = ["roc_auc", "pr_auc", "pr_auc_random", "flagged", "precision", "recall", "f1"]
    print(f"Fitted on {n_train} training agents; evaluated on {n_val} validation agents ({n_val_fraud} fraud). "
          f"Alert budget: top {ALERT_BUDGET:.0%} (rule row uses its own cap).\n")
    print(table.set_index("baseline")[cols].round(3).to_string())
    print("\nRecall by fraud pattern:")
    print(table.set_index("baseline")[[f"recall_{p}" for p in FRAUD_PATTERNS]].round(2).to_string())
    print("\nSingle-feature direction (training) and validation raw AUC / strength:")
    single = table[table["baseline"].str.startswith("single")].set_index("baseline")[["val_auc_raw", "val_strength"]]
    print(directions.round(3).to_string())
    print(single.round(3).to_string())
    print(f"\nRandom-score spread over seeds: ROC AUC std {table.iloc[0]['random_std_roc_auc']:.3f}, "
          f"PR AUC std {table.iloc[0]['random_std_pr_auc']:.3f}")
    print(f"Run folder {run_dir}")


if __name__ == "__main__":
    main()
