# Superseded by pipeline.py and detector.py; kept for historical reference of the original model comparison.
"""
Local Outlier Factor (LOF) model for the SalesMesh fraud detection system.

Trains LOF on the same standardised feature matrix used for Isolation Forest
(submission_frequency, time_of_day_dist, customer_similarity), per Section
3.2.3 and 3.5.6 of the proposal. LOF measures local density: an agent whose
neighbourhood is much sparser than its neighbours' neighbourhoods is flagged
as anomalous, which can catch agents unusual relative to a sub-group even
if they are not extreme outliers overall.

Input: data/synthetic/feature_vectors.csv, data/synthetic/agents.csv
Output: data/synthetic/fraud_flags_lof.csv
"""

import pandas as pd
import numpy as np
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

FEATURE_COLUMNS = ["submission_frequency", "time_of_day_dist", "customer_similarity"]

CONTAMINATION = 0.13
N_NEIGHBORS = 20


def load_data():
    features_df = pd.read_csv("data/synthetic/feature_vectors.csv")
    agents_df = pd.read_csv("data/synthetic/agents.csv")
    merged = features_df.merge(agents_df[["agent_id", "is_fraud"]], on="agent_id", how="left")
    return merged


def train_lof(df):
    X = df[FEATURE_COLUMNS].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LocalOutlierFactor(
        n_neighbors=N_NEIGHBORS,
        contamination=CONTAMINATION,
        novelty=False,
    )

    predictions = model.fit_predict(X_scaled)
    flagged = (predictions == -1)

    raw_scores = model.negative_outlier_factor_
    suspicion_score = 1 - (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min())

    return suspicion_score, flagged


def evaluate(df, suspicion_score, flagged, label):
    y_true = df["is_fraud"].astype(int).values
    y_pred = flagged.astype(int)

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_true, suspicion_score)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

    print(f"\n--- {label} Evaluation (development validation only) ---")
    print(f"Precision: {precision:.3f}")
    print(f"Recall:    {recall:.3f}")
    print(f"F1-score:  {f1:.3f}")
    print(f"ROC-AUC:   {roc_auc:.3f}")
    print(f"\nConfusion matrix:")
    print(f"  True negatives  (legit, not flagged): {tn}")
    print(f"  False positives (legit, flagged):     {fp}")
    print(f"  False negatives (fraud, not flagged): {fn}")
    print(f"  True positives  (fraud, flagged):     {tp}")

    return {"precision": precision, "recall": recall, "f1": f1, "roc_auc": roc_auc}


def main():
    print("Loading feature vectors and agent labels...")
    df = load_data()

    print("Training Local Outlier Factor...")
    suspicion_score, flagged = train_lof(df)

    df["suspicion_score"] = suspicion_score
    df["flag_status"] = np.where(flagged, "flagged", "clear")
    df["model_version"] = "lof_v1"

    output_df = df[[
        "vector_id", "agent_id", "suspicion_score", "flag_status", "model_version"
    ]].copy()
    output_df.insert(0, "flag_id", [f"FL{i+1}" for i in range(len(output_df))])

    output_df.to_csv("data/synthetic/fraud_flags_lof.csv", index=False)

    print(f"\nDone. {flagged.sum()} agents flagged out of {len(df)} total.")
    print("\nTop 10 most suspicious agents (LOF):")
    top10 = df.sort_values("suspicion_score", ascending=False).head(10)
    print(top10[["agent_id", "is_fraud", "suspicion_score", "flag_status"]].to_string(index=False))

    evaluate(df, suspicion_score, flagged, "Local Outlier Factor")

    print("\nSaved to data/synthetic/fraud_flags_lof.csv")


if __name__ == "__main__":
    main()