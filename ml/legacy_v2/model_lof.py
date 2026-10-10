"""
Local Outlier Factor (LOF) model for the SalesMesh fraud detection system.

Trains LOF on the same standardised feature matrix used for Isolation Forest,
per Sections 3.2.3 and 3.5.6 of the proposal. LOF measures local density: an
agent whose neighbourhood is much sparser than its neighbours'
neighbourhoods is flagged as anomalous, which can catch agents unusual
relative to a sub-group even if they are not extreme outliers overall.

v2 changes: fitted on the TRAINING agents only (split.py), with a scaler
fitted on the training partition only and contamination =
preprocessing.CONTAMINATION (an assumption, not the known fraud share).
novelty=True is required so the fitted model can score agents it was not
trained on (the test set). With novelty=True, scikit-learn's
score_samples/predict are only valid on new data, so training-agent scores
come from negative_outlier_factor_ instead. LOF is deterministic: the seed
does not affect it. This script no longer reports metrics: test-set
evaluation happens only in evaluate.py.

Note: the live backend detector (backend/src/detector.py) still refits LOF
with novelty=False and contamination=0.13 on every detection cycle; it was not
changed by this redesign.

Usage: python model_lof.py [--data-dir DIR]
Input:  <data-dir>/feature_vectors.csv, agents.csv, train_test_split.csv
Output: <data-dir>/fraud_flags_lof.csv (one row per agent, with its split)
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

from data_generation import DEFAULT_OUT_DIR, DEFAULT_SEED
from preprocessing import CONTAMINATION, fit_scaler, flags_frame, load_partitions, scaled_features, write_flags

MODEL_VERSION = "lof_v2"
N_NEIGHBORS = 20


@dataclass
class FittedLOF:
    scaler: StandardScaler
    model: LocalOutlierFactor

    def score(self, df):
        """Anomaly score per agent NOT in the training set; higher = more anomalous."""
        return -self.model.score_samples(scaled_features(self.scaler, df))

    def flag(self, df):
        return self.model.predict(scaled_features(self.scaler, df)) == -1

    def train_scores(self):
        return -self.model.negative_outlier_factor_

    def train_flags(self):
        return self.model.negative_outlier_factor_ < self.model.offset_


def fit_detector(train_df, seed=DEFAULT_SEED, contamination=CONTAMINATION):
    """Fits the scaler and LOF (novelty mode) on the training partition only. `seed` is unused."""
    scaler = fit_scaler(train_df)
    model = LocalOutlierFactor(n_neighbors=N_NEIGHBORS, contamination=contamination, novelty=True)
    model.fit(scaled_features(scaler, train_df))
    return FittedLOF(scaler, model)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Train Local Outlier Factor on the training agents.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    train_df, test_df = load_partitions(args.data_dir)
    print(f"Training Local Outlier Factor on {len(train_df)} training agents (contamination {CONTAMINATION})...")
    detector = fit_detector(train_df)

    train_scores = detector.train_scores()
    train_flags = detector.train_flags()
    frame = write_flags(
        args.data_dir / "fraud_flags_lof.csv",
        flags_frame(train_df, train_scores, train_flags, train_scores, MODEL_VERSION),
        flags_frame(test_df, detector.score(test_df), detector.flag(test_df), train_scores, MODEL_VERSION),
    )

    print(f"Done. {int(train_flags.sum())} of {len(train_df)} training agents flagged; "
          f"{len(test_df)} test agents scored (not evaluated here, see evaluate.py).")
    print(f"Saved {len(frame)} flags to {args.data_dir / 'fraud_flags_lof.csv'}")


if __name__ == "__main__":
    main()
