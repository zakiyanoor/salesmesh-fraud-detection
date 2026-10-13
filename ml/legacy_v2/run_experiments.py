"""
Multi-seed variability experiment for the SalesMesh fraud detection models.

For each seed, the WHOLE pipeline is rerun from scratch: generate a new
synthetic dataset (data_generation), clean it (clean_data), compute features
(feature_engineering), make a new stratified agent split (split), fit each
detector on that seed's training agents only, and score that seed's test
agents. The seed drives both data generation and model randomness (Isolation
Forest's random_state; LOF is deterministic).

Seeds 1-5 are used, deliberately NOT 42: seed 42 is the primary dataset whose
test set is held out for the final evaluation (evaluate.py), so this
experiment never touches it. Nothing (contamination, features, thresholds) is
changed in response to these results.

Usage: python run_experiments.py
Output: results/multi_seed_results.csv (one row per seed x detector) and a
        printed mean / std / min / max summary.
"""

import tempfile
from pathlib import Path

import pandas as pd

import baseline
import model
import model_lof
from clean_data import clean_data
from data_generation import generate_dataset
from feature_engineering import compute_feature_vectors
from metrics import compute_metrics
from preprocessing import load_partitions
from split import SPLIT_FILE, split_agents

SEEDS = [1, 2, 3, 4, 5]
RESULTS_PATH = Path(__file__).resolve().parent / "results" / "multi_seed_results.csv"
METRICS = ["precision", "recall", "f1", "roc_auc"]

# name -> fit_detector(train_df, seed); each returns an object with score(df) and flag(df).
DETECTORS = {
    "Isolation Forest": model.fit_detector,
    "LOF": model_lof.fit_detector,
    "Frequency rule (baseline)": baseline.fit_detector,
}


def build_dataset(seed, data_dir):
    """Runs generation -> cleaning -> features -> split for one seed into data_dir."""
    dataset = generate_dataset(seed)
    clean_df = clean_data(dataset.activations, dataset.agents, dataset.clients)[0]
    dataset.labels.to_csv(data_dir / "labels.csv", index=False)
    compute_feature_vectors(clean_df).to_csv(data_dir / "feature_vectors.csv", index=False)
    split_agents(dataset.labels, seed).to_csv(data_dir / SPLIT_FILE, index=False)


def run_seed(seed):
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        build_dataset(seed, data_dir)
        train_df, test_df = load_partitions(data_dir)
        for name, fit in DETECTORS.items():
            detector = fit(train_df, seed)
            metrics = compute_metrics(test_df["is_fraud"], detector.score(test_df), detector.flag(test_df))
            rows.append({"seed": seed, "detector": name, "test_agents": len(test_df),
                         "test_fraud": int(test_df["is_fraud"].sum()), **metrics})
    return rows


def summarise(results):
    summary = results.groupby("detector", sort=False)[METRICS].agg(["mean", "std", "min", "max"])
    pooled = results.groupby("detector", sort=False)[["tp", "fp", "fn", "tn"]].sum()
    return summary, pooled


def main():
    results = pd.DataFrame([row for seed in SEEDS for row in run_seed(seed)])
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(RESULTS_PATH, index=False)

    summary, pooled = summarise(results)
    print(f"Seeds {SEEDS}; each test set: {results['test_agents'].iloc[0]} agents, "
          f"{results['test_fraud'].iloc[0]} fraud.\n")
    print(results[["seed", "detector", *METRICS, "tp", "fp", "fn", "tn"]].round(3).to_string(index=False))
    print("\nMean / std / min / max across seeds:")
    print(summary.round(3).to_string())
    print("\nConfusion counts pooled over all seeds' test sets:")
    print(pooled.to_string())
    print(f"\nSaved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
