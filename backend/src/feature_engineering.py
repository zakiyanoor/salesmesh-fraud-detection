# Superseded by pipeline.py and detector.py; kept for historical reference of the original model comparison.
"""
Feature engineering for the SalesMesh fraud detection system.

Computes four behavioural features per agent, per analysis period, matching
Section 3.2.2 and Section 2.6 of the proposal (the fourth, collusion_score,
matches the live pipeline.py).

customer_similarity combines two signals, since Section 2.6 names two distinct
fraud patterns (citing Tabassum et al., 2021):
  (a) repetition / near-duplicate reuse of the same customer_id
  (b) sequential identifier patterns, where every id is technically unique but
      follows a suspiciously incrementing numeric structure
A repetition-only measure cannot detect (b), since sequential ids are each
individually unique by construction. Both signals are combined into a single
0-1 similarity score.
"""

import pandas as pd
import numpy as np
import re
from collections import Counter


def compute_submission_frequency(agent_records):
    """Raw count of activations submitted by this agent in the period."""
    return len(agent_records)


def compute_time_of_day_entropy(agent_records):
    """
    Shannon entropy of the agent's submission hours (0-23), normalised to 0-1.
    Low entropy = submissions cluster around a few hours (suspicious).
    High entropy = submissions spread naturally across the day (normal).
    """
    hours = agent_records["timestamp"].dt.hour
    hour_counts = Counter(hours)
    total = sum(hour_counts.values())

    if total == 0:
        return 0.0

    probabilities = [count / total for count in hour_counts.values()]
    entropy = -sum(p * np.log2(p) for p in probabilities if p > 0)

    max_entropy = np.log2(24)
    return entropy / max_entropy if max_entropy > 0 else 0.0


def compute_repetition_score(customer_ids):
    """
    Signal (a): repetition / near-duplicate reuse.
    1 - (unique count / total). High = same or near-identical id reused often.
    """
    total = len(customer_ids)
    if total == 0:
        return 0.0
    unique_count = customer_ids.nunique()
    return 1 - (unique_count / total)


def compute_sequential_score(customer_ids):
    """
    Signal (b): sequential identifier pattern.
    Extracts the numeric portion of each customer_id, sorts the unique numeric
    values, and measures what fraction of consecutive pairs differ by exactly 1.
    A fully sequential set (e.g. CUST10052, CUST10053, CUST10054...) scores
    close to 1. Randomly assigned ids score close to 0.
    """
    numbers = []
    for cid in customer_ids.unique():
        match = re.search(r"(\d+)", str(cid))
        if match:
            numbers.append(int(match.group(1)))

    if len(numbers) < 2:
        return 0.0

    numbers = sorted(set(numbers))
    if len(numbers) < 2:
        return 0.0

    consecutive_gaps = sum(
        1 for i in range(1, len(numbers)) if numbers[i] - numbers[i - 1] == 1
    )
    return consecutive_gaps / (len(numbers) - 1)


def compute_customer_similarity(agent_records):
    """
    Combines the repetition score and the sequential score into a single
    customer_similarity feature, taking the maximum of the two signals so
    that an agent triggering either fraud pattern is flagged, rather than
    diluting one strong signal by averaging it with a weak one.
    """
    customer_ids = agent_records["customer_id"]
    repetition = compute_repetition_score(customer_ids)
    sequential = compute_sequential_score(customer_ids)
    return max(repetition, sequential)


def compute_collusion_score(agent_id, agent_records, all_records):
    """
    Fraction of this agent's distinct customers that also appear in any OTHER
    agent's records: 0 = no overlap, 1 = every customer is shared.
    Mirrors compute_collusion_score in pipeline.py (not imported: pipeline.py
    pulls in the database layer and works on ORM records, not DataFrames).
    """
    own = set(agent_records["customer_id"])
    if not own:
        return 0.0
    others = all_records[all_records["agent_id"] != agent_id]["customer_id"]
    shared = own & set(others)
    return len(shared) / len(own)


def compute_feature_vectors(activations_df, analysis_period_label="2026-08"):
    activations_df["timestamp"] = pd.to_datetime(activations_df["timestamp"])

    feature_rows = []
    vector_id = 1

    for agent_id, agent_records in activations_df.groupby("agent_id"):
        submission_frequency = compute_submission_frequency(agent_records)
        time_of_day_dist = compute_time_of_day_entropy(agent_records)
        customer_similarity = compute_customer_similarity(agent_records)
        collusion_score = compute_collusion_score(agent_id, agent_records, activations_df)

        feature_rows.append({
            "vector_id": f"FV{vector_id}",
            "agent_id": agent_id,
            "analysis_period": analysis_period_label,
            "submission_frequency": submission_frequency,
            "time_of_day_dist": time_of_day_dist,
            "customer_similarity": customer_similarity,
            "collusion_score": collusion_score,
        })
        vector_id += 1

    return pd.DataFrame(feature_rows)


def main():
    print("Loading activation records...")
    activations_df = pd.read_csv("data/synthetic/activation_records.csv")

    print("Computing feature vectors...")
    features_df = compute_feature_vectors(activations_df)

    features_df.to_csv("data/synthetic/feature_vectors.csv", index=False)

    print(f"Done. Computed feature vectors for {len(features_df)} agents.")
    print("\nSample output:")
    print(features_df.head(10).to_string(index=False))
    print(f"\nSaved to data/synthetic/feature_vectors.csv")


if __name__ == "__main__":
    main()