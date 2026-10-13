"""
Preprocessing (Step 6): partitions and scaling.

StandardScaler is fitted on TRAINING agents' features only and then applied
(transform only) to validation and test, so no validation or test agent
influences the means and standard deviations. is_fraud and profile are
carried along for evaluation only; models read FEATURE_COLUMNS alone.

Usage: python preprocessing.py [--data-dir DIR]
Output: ml/runs/<run_id>/ with scaler.joblib, scaler_stats.csv and scaling_sample.md
"""

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.preprocessing import StandardScaler

from data_generation import DEFAULT_OUT_DIR
from feature_engineering import FEATURE_COLUMNS
from labels_guard import load_labelled, load_unlabelled

SAMPLE_SEED = 0
SAMPLE_PER_SPLIT = 5


def load_partitions(data_dir=DEFAULT_OUT_DIR, splits=("train", "validation")):
    """{split: labelled frame}, through the test-set guard (test only after Step 11 unlocks it)."""
    return load_labelled(data_dir, splits)


def fit_scaler(train_df, columns=None):
    """StandardScaler fitted on the training partition's features only."""
    columns = list(columns or FEATURE_COLUMNS)
    return StandardScaler().fit(train_df[columns].values)


def scaled_features(scaler, df, columns=None):
    """Applies an already-fitted scaler (transform only, never fit)."""
    return scaler.transform(df[list(columns or FEATURE_COLUMNS)].values)


def save_scaler(scaler, path, columns, train_agents):
    joblib.dump({"scaler": scaler, "feature_columns": list(columns), "fitted_on": "train",
                 "train_agents": int(train_agents)}, path)


def scaling_sample(parts, scaler, columns):
    rows = []
    for name in ["train", "validation"]:
        sample = parts[name].sample(SAMPLE_PER_SPLIT, random_state=SAMPLE_SEED)
        scaled = pd.DataFrame(scaled_features(scaler, sample, columns), columns=columns, index=sample.index)
        for idx in sample.index:
            rows.append({"split": name, "agent_id": sample.at[idx, "agent_id"], "values": "raw",
                         **{c: round(float(sample.at[idx, c]), 3) for c in columns}})
            rows.append({"split": name, "agent_id": sample.at[idx, "agent_id"], "values": "scaled",
                         **{c: round(float(scaled.at[idx, c]), 3) for c in columns}})
    return pd.DataFrame(rows)


def md_table(df):
    header = "| " + " | ".join(df.columns) + " |"
    return "\n".join([header, "|" + "---|" * len(df.columns)]
                     + ["| " + " | ".join(str(v) for v in row) + " |" for row in df.values])


def main(argv=None):
    from run_utils import start_run

    parser = argparse.ArgumentParser(description="Fit the StandardScaler on training agents only.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    columns = list(FEATURE_COLUMNS)
    inputs = [args.data_dir / f for f in ["feature_vectors.csv", "split.csv"]]
    parts = load_partitions(args.data_dir)
    parts["test"] = load_unlabelled(args.data_dir, "test")
    scaler = fit_scaler(parts["train"], columns)
    run_dir = start_run("preprocess", SAMPLE_SEED, {"scaler": "StandardScaler", "fitted_on": "train",
                                                    "feature_columns": columns}, inputs)
    save_scaler(scaler, run_dir / "scaler.joblib", columns, len(parts["train"]))

    all_agents = pd.concat(parts.values())
    stats = pd.DataFrame({"scaler_mean": scaler.mean_, "train_mean": parts["train"][columns].mean().values,
                          "all_agents_mean": all_agents[columns].mean().values,
                          "scaler_std": scaler.scale_, "train_std_ddof0": parts["train"][columns].std(ddof=0).values,
                          "all_agents_std_ddof0": all_agents[columns].std(ddof=0).values}, index=columns).round(4)
    stats.to_csv(run_dir / "scaler_stats.csv")
    after = pd.DataFrame({name: pd.DataFrame(scaled_features(scaler, df, columns), columns=columns).agg(["mean", "std"]).round(3).stack()
                          for name, df in parts.items()})
    sample = scaling_sample(parts, scaler, columns)
    (run_dir / "scaling_sample.md").write_text(
        f"# Before and after scaling (seed {SAMPLE_SEED}; scaler fitted on {len(parts['train'])} training agents)\n\n"
        f"{md_table(sample)}\n\n## Scaler statistics\n\n{md_table(stats.reset_index().rename(columns={'index': 'feature'}))}\n",
        encoding="utf-8")

    print("Scaler statistics (fitted on train only):")
    print(stats.to_string())
    print("\nScaled mean and std per split:")
    print(after.to_string())
    print("\nBefore and after scaling sample:")
    print(sample.to_string(index=False))
    print(f"\nRun folder {run_dir}")


if __name__ == "__main__":
    main()
