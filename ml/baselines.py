"""
Baselines (Step 7): fitted on TRAINING agents, evaluated on VALIDATION agents.

(a) trivial: seeded random scores, averaged over RANDOM_SEEDS;
(b) rule (Chapter 1, fixed volume cap): flag submission_frequency above the
    RULE_PERCENTILE of training agents; its score is submission_frequency;
(c) each feature alone as an anomaly score, in the direction with the higher
    TRAINING AUC (decided on training only);
(d) duplicate_activation_rule (reported, never a selection candidate): from the
    unlabelled activation records only, the number of the agent's (customer,
    client) pairs that another agent also used, or that the agent repeated after
    a completed activation; flagged when the count is above 0.
Test labels are never loaded (labels_guard).

Usage: python baselines.py [--data-dir DIR]
Output: ml/runs/<run_id>/ with run_info.json, baseline_metrics.csv, single_feature_directions.csv,
        baselines_train_and_validation.csv
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
DUPLICATE_RULE = "duplicate_activation_rule"
PAIR = ["customer_id", "client_id"]


def duplicate_activation_counts(activations):
    """Per agent: pairs used by another agent or repeated after a completed activation (no labels)."""
    acts = activations[["agent_id", "timestamp", *PAIR, "activation_status"]]
    acts = acts.assign(timestamp=pd.to_datetime(acts["timestamp"])).sort_values("timestamp", kind="mergesort")
    shared = acts.groupby(PAIR)["agent_id"].transform("nunique") > 1
    after_completed = acts.groupby(["agent_id", *PAIR])["activation_status"].shift().eq("completed")
    pairs = acts[shared | after_completed].drop_duplicates(["agent_id", *PAIR])
    return pairs.groupby("agent_id").size().reindex(acts["agent_id"].unique(), fill_value=0).rename(DUPLICATE_RULE)


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

    counts = duplicate_activation_counts(pd.read_csv(Path(data_dir) / "activation_records_clean.csv"))
    dup_val = val["agent_id"].map(counts).fillna(0).values
    rows.append({"baseline": f"rule: {DUPLICATE_RULE} (pairs > 0)", **evaluate(y, dup_val, profiles, flags=dup_val > 0)})
    table = pd.DataFrame(rows)
    return table, directions, len(train), len(val), int(val["is_fraud"].sum()), \
        train_and_validation(train, val, table, directions, cap, counts)


def train_and_validation(train, val, table, directions, cap, counts):
    """Random, volume rule, best single feature (by validation PR AUC) and the duplicate rule on both splits."""
    single = table[table["baseline"].str.startswith("single feature")]
    best = single.sort_values("pr_auc", ascending=False).iloc[0]["baseline"]
    feature = best.split(": ")[1].split(" ")[0]
    rows = []
    for name, part in [("train", train), ("validation", val)]:
        y, profiles = part["is_fraud"].values, part["profile"].values
        random_runs = pd.DataFrame([evaluate(y, np.random.default_rng(seed).random(len(part)), profiles)
                                    for seed in RANDOM_SEEDS])
        dup = part["agent_id"].map(counts).fillna(0).values
        for baseline, result in [
            (f"random scores (mean of {len(RANDOM_SEEDS)} seeds)", random_runs.mean().to_dict()),
            (f"rule: {RULE_FEATURE} > training P{int(RULE_PERCENTILE * 100)} ({cap:g})",
             evaluate(y, part[RULE_FEATURE].values, profiles, flags=part[RULE_FEATURE].values > cap)),
            (f"best single feature: {best.split(': ')[1]}",
             evaluate(y, directions.loc[feature, "direction"] * part[feature].values, profiles)),
            (f"rule: {DUPLICATE_RULE} (pairs > 0)", evaluate(y, dup, profiles, flags=dup > 0)),
        ]:
            rows.append({"split": name, "baseline": baseline, **result})
    return pd.DataFrame(rows)


def main(argv=None):
    from run_utils import start_run

    parser = argparse.ArgumentParser(description="Step 7 baselines on validation.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    inputs = [args.data_dir / f for f in ["feature_vectors.csv", "split.csv", "labels.csv", "activation_records_clean.csv"]]
    table, directions, n_train, n_val, n_val_fraud, both = run_baselines(args.data_dir)
    run_dir = start_run("baselines", None, {"alert_budget": ALERT_BUDGET, "random_seeds": list(RANDOM_SEEDS),
                                            "rule": f"{RULE_FEATURE} > train P{RULE_PERCENTILE}",
                                            "duplicate_rule": "pairs used by another agent or repeated after completed > 0",
                                            "evaluated_on": "validation", "fitted_on": "train"}, inputs)
    table.to_csv(run_dir / "baseline_metrics.csv", index=False)
    directions.to_csv(run_dir / "single_feature_directions.csv")
    both.to_csv(run_dir / "baselines_train_and_validation.csv", index=False)

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
    print("\nTraining and validation (reported baselines):")
    print(both.set_index(["split", "baseline"])[cols].round(3).to_string())
    print(f"\nRandom-score spread over seeds: ROC AUC std {table.iloc[0]['random_std_roc_auc']:.3f}, "
          f"PR AUC std {table.iloc[0]['random_std_pr_auc']:.3f}")
    print(f"Run folder {run_dir}")


if __name__ == "__main__":
    main()
