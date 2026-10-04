"""
Train/test split for the SalesMesh fraud detection pipeline.

Splits AGENTS (not activation records) so no agent appears in both sets,
stratified 80/20 on is_fraud. The assignment is saved so every later step
reads the same split. No model, scaler, threshold or contamination value may
be fitted on, or chosen by looking at, the test agents; they are only scored
in evaluate.py.

is_fraud is used here only to stratify, which keeps the fraud share equal in
both partitions; the models never see it.

Usage: python split.py [--data-dir DIR] [--seed N]
Input:  <data-dir>/agents.csv
Output: <data-dir>/train_test_split.csv (agent_id, split)
"""

import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from data_generation import DEFAULT_OUT_DIR, DEFAULT_SEED

TEST_SIZE = 0.20
SPLIT_FILE = "train_test_split.csv"


def split_agents(agents_df, seed=DEFAULT_SEED):
    train_ids, test_ids = train_test_split(
        agents_df["agent_id"],
        test_size=TEST_SIZE,
        stratify=agents_df["is_fraud"],
        random_state=seed,
    )
    split = pd.concat([
        pd.DataFrame({"agent_id": train_ids, "split": "train"}),
        pd.DataFrame({"agent_id": test_ids, "split": "test"}),
    ])
    return split.sort_values("agent_id").reset_index(drop=True)


def load_split(data_dir=DEFAULT_OUT_DIR):
    return pd.read_csv(Path(data_dir) / SPLIT_FILE)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Stratified 80/20 train/test split of agents.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)

    agents_df = pd.read_csv(args.data_dir / "agents.csv")
    split = split_agents(agents_df, args.seed)
    split.to_csv(args.data_dir / SPLIT_FILE, index=False)

    summary = split.merge(agents_df[["agent_id", "is_fraud"]], on="agent_id")
    print(summary.groupby("split")["is_fraud"].agg(agents="size", fraud="sum").to_string())
    print(f"Saved to {args.data_dir / SPLIT_FILE}")


if __name__ == "__main__":
    main()
