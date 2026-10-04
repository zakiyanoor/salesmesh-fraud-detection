"""
Rule-based baseline for the SalesMesh fraud detection models.

Flags any agent whose submission_frequency is above the 90th percentile of
the TRAINING agents' submission_frequency. It is the simplest rule a
platform operator might use ("review the busiest 10% of agents"), giving the
two learned models a comparison point. Its suspicion score (used for ROC-AUC)
is submission_frequency itself. The percentile is computed on the training
partition only; 90 matches the 10% contamination assumption in
preprocessing.py so all three detectors flag about the same share.

Usage: python baseline.py [--data-dir DIR]
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

from data_generation import DEFAULT_OUT_DIR, DEFAULT_SEED
from preprocessing import load_partitions

PERCENTILE = 0.90
FEATURE = "submission_frequency"


@dataclass
class FittedFrequencyRule:
    threshold: float

    def score(self, df):
        return df[FEATURE].values.astype(float)

    def flag(self, df):
        return df[FEATURE].values > self.threshold


def fit_detector(train_df, seed=DEFAULT_SEED):
    """Threshold = 90th percentile of training submission_frequency. `seed` is unused."""
    return FittedFrequencyRule(threshold=float(train_df[FEATURE].quantile(PERCENTILE)))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fit the submission-frequency baseline on the training agents.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    train_df, _ = load_partitions(args.data_dir)
    rule = fit_detector(train_df)
    print(f"Threshold: submission_frequency > {rule.threshold:.1f} "
          f"(training {PERCENTILE:.0%} percentile); flags {int(rule.flag(train_df).sum())} of {len(train_df)} training agents.")


if __name__ == "__main__":
    main()
