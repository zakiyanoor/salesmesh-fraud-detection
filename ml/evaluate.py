"""
Final evaluation for the SalesMesh fraud detection models.

Fits Isolation Forest, LOF and the frequency-rule baseline on the TRAINING
agents of the primary dataset (seed 42, data/synthetic/), then evaluates them
on that dataset's held-out TEST agents only. The test agents were not used for
fitting, scaling, cleaning decisions, contamination or thresholds. Alongside,
it reports the multi-seed variability from run_experiments.py (seeds 1-5,
each with its own test set).

Run the pipeline first:
  data_generation.py -> clean_data.py -> feature_engineering.py -> split.py
  -> run_experiments.py -> evaluate.py

Usage: python evaluate.py
Output: results/final_evaluation.csv and a printed side-by-side report.
"""

from pathlib import Path

import pandas as pd

from metrics import compute_metrics
from preprocessing import CONTAMINATION, load_partitions
from run_experiments import DETECTORS, METRICS, RESULTS_PATH as MULTI_SEED_PATH, summarise

RESULTS_PATH = Path(__file__).resolve().parent / "results" / "final_evaluation.csv"


def main():
    train_df, test_df = load_partitions()
    print(f"Primary dataset (seed 42): fitted on {len(train_df)} training agents "
          f"({int(train_df['is_fraud'].sum())} fraud); evaluated on {len(test_df)} held-out test agents "
          f"({int(test_df['is_fraud'].sum())} fraud). Contamination assumption: {CONTAMINATION}.\n")

    rows = []
    for name, fit in DETECTORS.items():
        detector = fit(train_df)
        rows.append({"detector": name, **compute_metrics(
            test_df["is_fraud"], detector.score(test_df), detector.flag(test_df)
        )})
    final = pd.DataFrame(rows)
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(RESULTS_PATH, index=False)

    print("Held-out test set:")
    print(final.set_index("detector")[METRICS].round(3).to_string())
    print("\nConfusion matrices (rows: actual, columns: predicted):")
    for row in rows:
        print(f"  {row['detector']}:  legit -> [clear {row['tn']:>2}, flagged {row['fp']:>2}]   "
              f"fraud -> [clear {row['fn']:>2}, flagged {row['tp']:>2}]")

    if MULTI_SEED_PATH.exists():
        summary, _ = summarise(pd.read_csv(MULTI_SEED_PATH))
        print("\nMulti-seed variability (seeds 1-5, each on its own test set), mean [min-max]:")
        for name in summary.index:
            cells = [f"{m} {summary.loc[name, (m, 'mean')]:.3f} "
                     f"[{summary.loc[name, (m, 'min')]:.2f}-{summary.loc[name, (m, 'max')]:.2f}]" for m in METRICS]
            print(f"  {name}: " + ", ".join(cells))
    else:
        print("\n(run_experiments.py has not been run; no multi-seed variability to report)")

    print(f"\nSaved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
