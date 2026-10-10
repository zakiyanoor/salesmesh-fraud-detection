"""
Shared preprocessing for the SalesMesh fraud detection models.

Partitions: load_partitions joins the feature vectors to the saved
train/test split (split.py). Only the training partition may be used to fit
anything.

Scaling (Step 5): fit_scaler fits StandardScaler on the TRAINING features
only. The test partition is only ever passed to scaler.transform, so test
agents never influence the scaling means and standard deviations.

Contamination (Step 6): CONTAMINATION = 0.10 is an ASSUMPTION, not a measured
value. v1 used 0.13, which was exactly the generator's known fraud share
(15/115), so both models were told the true fraud rate and flagged exactly 15
agents by construction. A real deployment does not know its fraud rate.
0.10 was chosen as a round-number prior, without looking at any model output
or test data, for these reasons:
- it is a common tooling default, not a number derived from this dataset:
  PyOD uses contamination=0.1 for its detectors, and scikit-learn's
  IsolationForest and LocalOutlierFactor defaulted to 0.1 before v0.22;
- at the platform level it reads as "the review team can inspect roughly 1 in
  10 agents per cycle", a workload assumption rather than a fraud-rate claim;
- the alternative, estimating contamination from the training features with
  an outlier heuristic, was rejected: with 92 training agents such an
  estimate is itself very noisy, and a heuristic tuned on the same feature
  distribution partly re-learns the fraud share it is meant not to know.
It is deliberately not equal to the true share (13%): the results show what
happens when the assumed rate is wrong, as it will be in production. The
value only sets the flag threshold, so it changes precision/recall/F1 but
not ROC-AUC, which is threshold-free.
"""

from pathlib import Path

import pandas as pd
from sklearn.preprocessing import StandardScaler

from data_generation import DEFAULT_OUT_DIR
from feature_engineering import FEATURE_COLUMNS
from split import load_split

CONTAMINATION = 0.10


def load_partitions(data_dir=DEFAULT_OUT_DIR):
    """
    Returns (train_df, test_df): feature vectors joined with is_fraud and the
    split. is_fraud is carried along for evaluation only; models must use
    FEATURE_COLUMNS alone.
    """
    data_dir = Path(data_dir)
    features = pd.read_csv(data_dir / "feature_vectors.csv")
    labels = pd.read_csv(data_dir / "labels.csv")[["agent_id", "is_fraud"]]
    df = features.merge(labels, on="agent_id").merge(load_split(data_dir), on="agent_id")
    train_df = df[df["split"] == "train"].reset_index(drop=True)
    test_df = df[df["split"] == "test"].reset_index(drop=True)
    return train_df, test_df


def fit_scaler(train_df):
    """StandardScaler fitted on the training partition's features only."""
    return StandardScaler().fit(train_df[FEATURE_COLUMNS].values)


def scaled_features(scaler, df):
    """Applies an already-fitted scaler (transform only, never fit)."""
    return scaler.transform(df[FEATURE_COLUMNS].values)


# --- Model outputs ---

def to_suspicion_score(raw_scores, train_raw_scores):
    """
    Maps raw anomaly scores (higher = more anomalous) to 0-1 using the
    TRAINING score range, clipped, so test scores never rescale the output.
    """
    low, high = train_raw_scores.min(), train_raw_scores.max()
    if high == low:
        return raw_scores * 0.0
    return ((raw_scores - low) / (high - low)).clip(0.0, 1.0)


def flags_frame(df, raw_scores, flagged, train_raw_scores, model_version):
    """One fraud-flag row per agent, in the columns backend/src/load_data.py reads, plus `split`."""
    return pd.DataFrame({
        "vector_id": df["vector_id"].values,
        "agent_id": df["agent_id"].values,
        "suspicion_score": to_suspicion_score(raw_scores, train_raw_scores),
        "flag_status": ["flagged" if f else "clear" for f in flagged],
        "model_version": model_version,
        "split": df["split"].values,
    })


def write_flags(path, train_frame, test_frame):
    frame = pd.concat([train_frame, test_frame]).sort_values("agent_id").reset_index(drop=True)
    frame.insert(0, "flag_id", [f"FL{i + 1}" for i in range(len(frame))])
    frame.to_csv(path, index=False)
    return frame
