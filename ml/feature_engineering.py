"""
Feature engineering (Step 4). Label-free: reads cleaned records and agents only.

One row per agent per analysis period [period_start, period_end). Exact
definitions are in ml/DATA_CARD.md ("Feature definitions"):
- submission_frequency: submissions in the agent's busiest SUBMISSION_WINDOW_HOURS sliding window
- time_of_day_entropy: Shannon entropy of submission hours / log2(24), 0-1
- customer_similarity: mean similarity of identifiers over all pairs of submissions
- collusion_score: share of the agent's distinct customers also used by another agent
  in the period (platform-wide overlap, as in deployment)
- volume_vs_peers (candidate): submissions / leave-one-out median submissions of peers
  (same primary category and former region, widened if fewer than PEER_MIN_GROUP agents)

Usage: python feature_engineering.py [--data-dir DIR]
Output: <data-dir>/feature_vectors.csv and ml/runs/<run_id>/ (run_info.json, feature_vectors.csv)
"""

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

from data_generation import ANALYSIS_END, ANALYSIS_START, COUNTY_TO_FORMER_PROVINCE, DEFAULT_OUT_DIR

SUBMISSION_WINDOW_HOURS = 24
PEER_MIN_GROUP = 15
BASE_FEATURES = ["submission_frequency", "time_of_day_entropy", "customer_similarity", "collusion_score"]
CANDIDATE_FEATURE = "volume_vs_peers"
ALL_FEATURES = BASE_FEATURES + [CANDIDATE_FEATURE]
# Features the models use. Step 4 decision (run 20261013-093024_feature_checks): KEEP volume_vs_peers
# (training AUC 0.760 > 0.55; max |Spearman| 0.803 <= 0.85).
FEATURE_COLUMNS = ALL_FEATURES
# Inputs of the chosen model lof_v3_4f (Step 9, amended rule; run 20261013-093050_selection_s42).
MODEL_FEATURES = list(BASE_FEATURES)
DEFAULT_PERIOD = (ANALYSIS_START, ANALYSIS_END + pd.Timedelta(days=1))


def submission_frequency(timestamps, window_hours=SUBMISSION_WINDOW_HOURS):
    """Max submissions in any window [t, t + window); the max is reached by a window starting at a submission."""
    times = np.sort(pd.to_datetime(timestamps).values)
    if len(times) == 0:
        return 0
    ends = np.searchsorted(times, times + np.timedelta64(window_hours, "h"), side="left")
    return int((ends - np.arange(len(times))).max())


def time_of_day_entropy(timestamps):
    hours = pd.to_datetime(timestamps).dt.hour
    if hours.empty:
        return 0.0
    p = hours.value_counts(normalize=True).values
    return float(-(p * np.log2(p)).sum() / np.log2(24))


_ID_PREFIX = re.compile(r"^\D+(?=\d)")


def identifier_similarity(customer_ids):
    """
    Mean over all unordered pairs of submissions of the share of matching character positions.

    Each id loses its leading run of non-digit characters (CUST, C, ACC-) when a digit follows;
    an id with no digit is kept whole. Ids are aligned on the right, so numbers of different
    lengths line up on their last digits, and a shorter id is padded on the left with a filler
    that never matches. The denominator is the longest length times the number of pairs. For
    CUST plus 8 digits (all v3 data) this is the same arithmetic as before (issue #26).
    """
    ids = [_ID_PREFIX.sub("", str(c)) for c in customer_ids]
    n = len(ids)
    width = max((len(i) for i in ids), default=0)
    if n < 2 or width == 0:
        return 0.0
    chars = np.array([[None] * (width - len(i)) + list(i) for i in ids], dtype=object)
    matches = 0
    for pos in range(width):
        column = [c for c in chars[:, pos] if c is not None]
        counts = np.unique(np.array(column, dtype=str), return_counts=True)[1] if column else np.array([], dtype=int)
        matches += int((counts * (counts - 1) // 2).sum())
    return matches / (width * n * (n - 1) / 2)


def collusion_scores(records):
    """Per agent: share of its distinct customers that at least one other agent also used."""
    pairs = records[["agent_id", "customer_id"]].drop_duplicates()
    owners = pairs.groupby("customer_id")["agent_id"].nunique()
    return pairs.assign(shared=pairs["customer_id"].map(owners) > 1).groupby("agent_id")["shared"].mean()


def primary_category(records):
    counts = records.groupby(["agent_id", "category"]).size().rename("n").reset_index()
    counts = counts.sort_values(["agent_id", "n", "category"], ascending=[True, False, True])
    return counts.drop_duplicates("agent_id").set_index("agent_id")["category"]


def volume_vs_peers(volume, category, region, min_group=PEER_MIN_GROUP):
    """
    volume / leave-one-out median volume of peers. Peers: same primary category and
    former region; if that group (agent included) is smaller than min_group, same
    category in all regions; if still smaller, all agents. Returns (ratio, peer_level).
    """
    frame = pd.DataFrame({"volume": volume, "category": category, "region": region})
    levels = [["category", "region"], ["category"], []]
    ratio, level_used = pd.Series(np.nan, index=frame.index), pd.Series("", index=frame.index)
    for keys in levels:
        groups = frame.groupby(keys) if keys else [((), frame)]
        for _, group in groups:
            todo = group.index[ratio[group.index].isna()]
            if len(todo) == 0 or (keys and len(group) < min_group):
                continue
            for agent in todo:
                peers = group["volume"].drop(agent)
                ratio[agent] = frame.at[agent, "volume"] / max(float(peers.median()), 1.0)
                level_used[agent] = "+".join(keys) or "all"
    return ratio, level_used


def compute_feature_vectors(activations_df, agents_df, period_start=DEFAULT_PERIOD[0], period_end=DEFAULT_PERIOD[1]):
    """Feature rows for every agent in agents_df, over records with period_start <= timestamp < period_end."""
    period_start, period_end = pd.Timestamp(period_start), pd.Timestamp(period_end)
    records = activations_df.assign(timestamp=pd.to_datetime(activations_df["timestamp"]))
    records = records[(records["timestamp"] >= period_start) & (records["timestamp"] < period_end)]
    agents = agents_df.set_index("agent_id")
    grouped = records.groupby("agent_id")

    table = pd.DataFrame(index=agents.index)
    table["volume"] = grouped.size().reindex(agents.index, fill_value=0)
    table["submission_frequency"] = grouped["timestamp"].apply(submission_frequency).reindex(agents.index, fill_value=0)
    table["time_of_day_entropy"] = grouped["timestamp"].apply(time_of_day_entropy).reindex(agents.index, fill_value=0.0)
    table["customer_similarity"] = grouped["customer_id"].apply(identifier_similarity).reindex(agents.index, fill_value=0.0)
    table["collusion_score"] = collusion_scores(records).reindex(agents.index, fill_value=0.0).astype(float)
    category = primary_category(records).reindex(agents.index, fill_value="none")
    region = agents["region"].map(COUNTY_TO_FORMER_PROVINCE)
    table["volume_vs_peers"], table["peer_group"] = volume_vs_peers(table["volume"], category, region)

    table = table.reset_index()
    table.insert(0, "vector_id", [f"FV{i + 1}" for i in range(len(table))])
    table.insert(2, "analysis_period_start", period_start)
    table.insert(3, "analysis_period_end", period_end)
    return table[["vector_id", "agent_id", "analysis_period_start", "analysis_period_end", *ALL_FEATURES,
                  "volume", "peer_group"]]


def main(argv=None):
    from run_utils import start_run

    parser = argparse.ArgumentParser(description="Compute per-agent feature vectors (label-free).")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    inputs = [args.data_dir / "activation_records_clean.csv", args.data_dir / "agents.csv"]
    features = compute_feature_vectors(pd.read_csv(inputs[0]), pd.read_csv(inputs[1]))
    run_dir = start_run("features", None, {"submission_window_hours": SUBMISSION_WINDOW_HOURS,
                                           "peer_min_group": PEER_MIN_GROUP, "period": [str(p) for p in DEFAULT_PERIOD],
                                           "features": ALL_FEATURES}, inputs)
    features.to_csv(run_dir / "feature_vectors.csv", index=False)
    features.to_csv(args.data_dir / "feature_vectors.csv", index=False)
    print(features[ALL_FEATURES].describe().round(3).to_string())
    print("Peer group level used:", features["peer_group"].value_counts().to_dict())
    print(f"Saved {len(features)} rows to {run_dir / 'feature_vectors.csv'} and {args.data_dir / 'feature_vectors.csv'}")


if __name__ == "__main__":
    main()
