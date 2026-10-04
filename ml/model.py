"""
Isolation Forest model for the SalesMesh fraud detection system.

Trains an Isolation Forest on the standardised behavioural feature matrix
(submission_frequency, time_of_day_dist, customer_similarity,
collusion_score), per Section 3.2.3 of the proposal.

v2 changes: fitted on the TRAINING agents only (split.py), with a scaler fitted
on the training partition only and contamination = preprocessing.CONTAMINATION
(an assumption, not the known fraud share). The model is trained unsupervised;
is_fraud is never used. This script no longer reports metrics: test-set
evaluation happens only in evaluate.py.

Usage: python model.py [--data-dir DIR] [--seed N]
Input:  <data-dir>/feature_vectors.csv, agents.csv, train_test_split.csv
Output: <data-dir>/fraud_flags.csv (one row per agent, with its split) and the
        deployable artifact models/isolation_forest_v2.joblib, which the live
        backend (backend/src/detector.py) loads for inference.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

import joblib
import sklearn
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from data_generation import DEFAULT_OUT_DIR, DEFAULT_SEED
from feature_engineering import FEATURE_COLUMNS
from preprocessing import CONTAMINATION, fit_scaler, flags_frame, load_partitions, scaled_features, write_flags

MODEL_VERSION = "isolation_forest_v2"
N_ESTIMATORS = 100
ARTIFACT_PATH = Path(__file__).resolve().parent / "models" / f"{MODEL_VERSION}.joblib"


@dataclass
class FittedIsolationForest:
    scaler: StandardScaler
    model: IsolationForest

    def score(self, df):
        """Anomaly score per agent; higher = more anomalous."""
        return -self.model.score_samples(scaled_features(self.scaler, df))

    def flag(self, df):
        return self.model.predict(scaled_features(self.scaler, df)) == -1


def fit_detector(train_df, seed=DEFAULT_SEED, contamination=CONTAMINATION):
    """Fits the scaler and the Isolation Forest on the training partition only."""
    scaler = fit_scaler(train_df)
    model = IsolationForest(contamination=contamination, n_estimators=N_ESTIMATORS, random_state=seed)
    model.fit(scaled_features(scaler, train_df))
    return FittedIsolationForest(scaler, model)


def save_artifact(detector, train_scores, train_agents, seed, path=ARTIFACT_PATH):
    """
    Saves everything inference needs, so the backend never refits: the
    training-fitted scaler and forest, the feature order, and the training
    score range that maps raw scores to 0-1 suspicion scores.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "model_version": MODEL_VERSION,
        "feature_columns": FEATURE_COLUMNS,
        "scaler": detector.scaler,
        "model": detector.model,
        "train_score_min": float(train_scores.min()),
        "train_score_max": float(train_scores.max()),
        "contamination": CONTAMINATION,
        "seed": seed,
        "trained_on_agents": int(train_agents),
        "sklearn_version": sklearn.__version__,
    }, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Train Isolation Forest on the training agents.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)

    train_df, test_df = load_partitions(args.data_dir)
    print(f"Training Isolation Forest on {len(train_df)} training agents (contamination {CONTAMINATION})...")
    detector = fit_detector(train_df, args.seed)

    train_scores = detector.score(train_df)
    train_flags = detector.flag(train_df)
    frame = write_flags(
        args.data_dir / "fraud_flags.csv",
        flags_frame(train_df, train_scores, train_flags, train_scores, MODEL_VERSION),
        flags_frame(test_df, detector.score(test_df), detector.flag(test_df), train_scores, MODEL_VERSION),
    )

    print(f"Done. {int(train_flags.sum())} of {len(train_df)} training agents flagged; "
          f"{len(test_df)} test agents scored (not evaluated here, see evaluate.py).")
    print(f"Saved {len(frame)} flags to {args.data_dir / 'fraud_flags.csv'}")

    save_artifact(detector, train_scores, len(train_df), args.seed)
    print(f"Saved model artifact to {ARTIFACT_PATH}")


if __name__ == "__main__":
    main()
