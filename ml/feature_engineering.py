"""
Feature engineering for the SalesMesh fraud detection system.

Computes four behavioural features per agent, per analysis period, matching
Section 3.2.2 and Section 2.6 of the proposal. The formulas mirror the live
backend pipeline (backend/src/pipeline.py), which works on ORM records rather
than DataFrames, so offline evaluation measures the same features the
deployed system computes.

Input is the cleaned activation records from clean_data.py, never the raw file.

Design decisions:
- The analysis period is derived from the data's own timestamps (one
  calendar month -> "YYYY-MM", matching the backend's ANALYSIS_PERIOD_FORMAT),
  not hard-coded.
- Features are computed over all agents' records for the period, before the
  train/test split. Every feature is label-free and per agent, except
  collusion_score, which by definition compares one agent's customers with
  every other agent's. In deployment the detector sees all platform activity
  for a period, so this mirrors production. The cost is that a test agent's
  collusion_score can reflect overlap with a training agent in the same ring
  (and vice versa); no labels cross the split, but the partitions are not
  fully independent at the feature level.
- Known limitation: time_of_day_dist measures how *spread out* submission
  hours are, not *when* they happen, so an agent concentrated at 03:00 and
  one concentrated at 14:00 look alike. Ring 3 in the v2 synthetic data
  (business-hours ring) is invisible to this feature by design.

Usage: python feature_engineering.py [--data-dir DIR]
Input:  <data-dir>/activation_records_clean.csv
Output: <data-dir>/feature_vectors.csv
"""

import argparse
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from data_generation import DEFAULT_OUT_DIR

FEATURE_COLUMNS = ["submission_frequency", "time_of_day_dist", "customer_similarity", "collusion_score"]


def derive_analysis_period(timestamps):
    """
    "YYYY-MM" for data that falls within one calendar month (the backend's
    period format); "YYYY-MM_to_YYYY-MM" if it spans several.
    """
    months = sorted(pd.to_datetime(timestamps).dt.to_period("M").unique())
    if not months:
        raise ValueError("no timestamps to derive an analysis period from")
    return str(months[0]) if len(months) == 1 else f"{months[0]}_to_{months[-1]}"


# submission_frequency: how many activations the agent submitted in the period
# (all statuses, see clean_data.py). Commission is paid per activation, so
# inflating volume with fake or duplicate customers is the most direct way to
# commit this fraud; an agent far above their peers' volume warrants review.
def compute_submission_frequency(agent_records):
    return len(agent_records)


# time_of_day_dist: Shannon entropy of the agent's submission hours, normalised
# to 0-1 (0 = every submission in one hour, 1 = evenly spread over 24 hours).
# Scripted or batch-submitted fraud tends to cluster in a narrow window (often
# off-hours), while genuine field activity spreads across the working day.
def compute_time_of_day_entropy(agent_records):
    hours = agent_records["timestamp"].dt.hour
    hour_counts = Counter(hours)
    total = sum(hour_counts.values())

    if total == 0:
        return 0.0

    probabilities = [count / total for count in hour_counts.values()]
    entropy = -sum(p * np.log2(p) for p in probabilities if p > 0)
    return entropy / np.log2(24)


def compute_repetition_score(customer_ids):
    """
    Signal (a): repetition / near-duplicate reuse.
    1 - (unique count / total). High = same customer id resubmitted often.
    """
    total = len(customer_ids)
    if total == 0:
        return 0.0
    return 1 - (customer_ids.nunique() / total)


def compute_sequential_score(customer_ids):
    """
    Signal (b): sequential identifier pattern.
    Fraction of consecutive pairs among the agent's sorted unique numeric ids
    that differ by exactly 1. CUST100052, CUST100053, CUST100054... scores ~1;
    randomly assigned ids score ~0.
    """
    numbers = sorted({
        int(match.group(1))
        for cid in customer_ids.unique()
        if (match := re.search(r"(\d+)", str(cid)))
    })
    if len(numbers) < 2:
        return 0.0
    consecutive_gaps = sum(1 for i in range(1, len(numbers)) if numbers[i] - numbers[i - 1] == 1)
    return consecutive_gaps / (len(numbers) - 1)


# customer_similarity: max of the repetition and sequential scores (0-1).
# Section 2.6 names two fake-customer patterns (Tabassum et al., 2021):
# resubmitting the same customer, and fabricating customers with incrementing
# ids. Each id in a sequential run is unique, so a repetition-only measure
# misses it. Taking the max (not the mean) means either pattern alone is
# enough to raise the score.
def compute_customer_similarity(agent_records):
    customer_ids = agent_records["customer_id"]
    return max(compute_repetition_score(customer_ids), compute_sequential_score(customer_ids))


# collusion_score: fraction of the agent's distinct customers that also appear
# in any OTHER agent's records (0 = none shared, 1 = all shared). Coordinated
# rings register the same customers across several agent accounts (Chang et
# al., 2024); independent agents rarely share customers. Counted per distinct
# customer so repeating one shared customer isn't weighted by repetition.
def compute_collusion_score(agent_id, agent_records, all_records):
    own = set(agent_records["customer_id"])
    if not own:
        return 0.0
    others = all_records[all_records["agent_id"] != agent_id]["customer_id"]
    return len(own & set(others)) / len(own)


def compute_feature_vectors(activations_df):
    activations_df = activations_df.assign(timestamp=pd.to_datetime(activations_df["timestamp"]))
    analysis_period = derive_analysis_period(activations_df["timestamp"])

    feature_rows = []
    for vector_number, (agent_id, agent_records) in enumerate(activations_df.groupby("agent_id"), start=1):
        feature_rows.append({
            "vector_id": f"FV{vector_number}",
            "agent_id": agent_id,
            "analysis_period": analysis_period,
            "submission_frequency": compute_submission_frequency(agent_records),
            "time_of_day_dist": compute_time_of_day_entropy(agent_records),
            "customer_similarity": compute_customer_similarity(agent_records),
            "collusion_score": compute_collusion_score(agent_id, agent_records, activations_df),
        })

    return pd.DataFrame(feature_rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compute per-agent feature vectors from cleaned records.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    activations_df = pd.read_csv(args.data_dir / "activation_records_clean.csv")
    features_df = compute_feature_vectors(activations_df)
    features_df.to_csv(args.data_dir / "feature_vectors.csv", index=False)

    print(f"Done. Computed feature vectors for {len(features_df)} agents, "
          f"analysis period {features_df['analysis_period'].iloc[0]}.")
    print(f"Saved to {args.data_dir / 'feature_vectors.csv'}")


if __name__ == "__main__":
    main()
