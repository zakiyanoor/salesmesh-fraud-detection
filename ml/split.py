"""
Agent-level train/validation/test split (Step 5).

70/15/15, stratified by pattern (legit plus the five fraud patterns) so every
split holds every pattern. Labels are used here only to stratify. Fails if
validation or test has fewer than MIN_FRAUD_PER_EVAL_SPLIT fraud agents.

Rings can span splits: members of one ring may sit in different splits. This
is not label leakage, because no model is trained on labels, and
collusion_score is computed from platform-wide customer overlap, which is how
the feature works in deployment.

Usage: python split.py [--data-dir DIR]
Output: ml/runs/<run_id>/split.csv (agent_id, split), split_summary.csv,
        and a copy at <data-dir>/split.csv for later steps
"""

import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from data_generation import DEFAULT_OUT_DIR

SPLIT_SEED = 42
TRAIN_SHARE, VALIDATION_SHARE, TEST_SHARE = 0.70, 0.15, 0.15
MIN_FRAUD_PER_EVAL_SPLIT = 15
SPLIT_FILE = "split.csv"
SPLITS = ["train", "validation", "test"]


def strata(labels):
    """legit for every legitimate agent, else the fraud pattern."""
    return labels["profile"].where(labels["is_fraud"], "legit")


def split_agents(labels, seed=SPLIT_SEED):
    stratum = strata(labels)
    train_ids, rest_ids = train_test_split(labels["agent_id"], train_size=TRAIN_SHARE,
                                           stratify=stratum, random_state=seed)
    rest_stratum = stratum[labels["agent_id"].isin(rest_ids)]
    val_ids, test_ids = train_test_split(labels.loc[rest_stratum.index, "agent_id"],
                                         test_size=TEST_SHARE / (VALIDATION_SHARE + TEST_SHARE),
                                         stratify=rest_stratum, random_state=seed)
    split = pd.concat([pd.DataFrame({"agent_id": ids, "split": name})
                       for name, ids in zip(SPLITS, [train_ids, val_ids, test_ids])])
    split = split.sort_values("agent_id").reset_index(drop=True)
    check_split(split, labels)
    return split


def check_split(split, labels):
    if split["agent_id"].duplicated().any():
        raise ValueError("an agent is assigned to more than one split")
    if set(split["agent_id"]) != set(labels["agent_id"]):
        raise ValueError("split does not cover exactly the labelled agents")
    merged = split.merge(labels, on="agent_id")
    for name in ["validation", "test"]:
        n_fraud = int(merged.loc[merged["split"] == name, "is_fraud"].sum())
        if n_fraud < MIN_FRAUD_PER_EVAL_SPLIT:
            raise ValueError(f"{name} has {n_fraud} fraud agents; at least {MIN_FRAUD_PER_EVAL_SPLIT} are required")
    present = merged.assign(stratum=strata(merged)).groupby("split")["stratum"].nunique()
    if (present < strata(labels).nunique()).any():
        raise ValueError(f"not every pattern is present in every split: {present.to_dict()}")


def split_summary(split, labels):
    merged = split.merge(labels, on="agent_id")
    by_pattern = pd.crosstab(merged["profile"], merged["split"]).reindex(columns=SPLITS)
    totals = merged.groupby("split").agg(agents=("agent_id", "size"), fraud=("is_fraud", "sum")).reindex(SPLITS).T
    totals.loc["fraud_share"] = (totals.loc["fraud"] / totals.loc["agents"]).round(3)
    return pd.concat([totals, by_pattern])


def load_split(data_dir=DEFAULT_OUT_DIR):
    return pd.read_csv(Path(data_dir) / SPLIT_FILE)


def main(argv=None):
    from run_utils import start_run

    parser = argparse.ArgumentParser(description="Stratified 70/15/15 agent-level split.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    labels_path = args.data_dir / "labels.csv"
    labels = pd.read_csv(labels_path, keep_default_na=False)
    split = split_agents(labels)
    run_dir = start_run("split", SPLIT_SEED, {"train": TRAIN_SHARE, "validation": VALIDATION_SHARE, "test": TEST_SHARE,
                                              "stratify_by": "pattern (legit + 5 fraud patterns)",
                                              "min_fraud_per_eval_split": MIN_FRAUD_PER_EVAL_SPLIT}, [labels_path])
    split.to_csv(run_dir / SPLIT_FILE, index=False)
    split.to_csv(args.data_dir / SPLIT_FILE, index=False)
    summary = split_summary(split, labels)
    summary.to_csv(run_dir / "split_summary.csv")
    print(summary.to_string())
    print(f"Saved {run_dir / SPLIT_FILE} and a copy at {args.data_dir / SPLIT_FILE}")


if __name__ == "__main__":
    main()
