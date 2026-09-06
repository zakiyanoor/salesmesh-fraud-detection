"""
Isolation Forest baseline model for the SalesMesh fraud detection system.

Trains an Isolation Forest on the standardised behavioural feature matrix
(submission_frequency, time_of_day_dist, customer_similarity) and assigns
each agent an anomaly score and a flagged/not-flagged prediction, per
Section 3.2.3 of the proposal.

Since this is synthetic data with a known is_fraud ground truth label, this
script also reports precision, recall, F1-score, and ROC-AUC per Section
3.2.4 -- purely for development validation. The model itself is trained
unsupervised, without using the is_fraud label at any point.

Input: data/synthetic/feature_vectors.csv, data/synthetic/agents.csv
Output: data/synthetic/fraud_flags.csv
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

FEATURE_COLUMNS = ["submission_frequency", "time_of_day_dist", "customer_similarity"]

CONTAMINATION = 0.13  # 15 fraud agents out of 115 total ≈ 0.13


def load_data():
    features_df = pd.read_csv("data/synthetic/feature_vectors.csv")
    agents_df = pd.read_csv("data/synthetic/agents.csv")
    merged = features_df.merge(agents_df[["agent_id", "is_fraud"]], on="agent_id", how="left")
    return merged


def train_isolation_forest(df):
    X = df[FEATURE_COLUMNS].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        contamination=CONTAMINATION,
        random_state=42,
        n_estimators=100,
    )
    model.fit(X_scaled)

    raw_scores = model.decision_function(X_scaled)
    suspicion_score = 1 - (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min())

    predictions = model.predict(X_scaled)
    flagged = (predictions == -1)

    return suspicion_score, flagged, model, scaler


def evaluate(df, suspicion_score, flagged):
    y_true = df["is_fraud"].astype(int).values
    y_pred = flagged.astype(int)

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_true, suspicion_score)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

    print("\n--- Model Evaluation (development validation only) ---")
    print(f"Precision: {precision:.3f}")
    print(f"Recall:    {recall:.3f}")
    print(f"F1-score:  {f1:.3f}")
    print(f"ROC-AUC:   {roc_auc:.3f}")
    print(f"\nConfusion matrix:")
    print(f"  True negatives  (legit, not flagged): {tn}")
    print(f"  False positives (legit, flagged):     {fp}")
    print(f"  False negatives (fraud, not flagged): {fn}")
    print(f"  True positives  (fraud, flagged):     {tp}")


def main():
    print("Loading feature vectors and agent labels...")
    df = load_data()

    print("Training Isolation Forest...")
    suspicion_score, flagged, model, scaler = train_isolation_forest(df)

    df["suspicion_score"] = suspicion_score
    df["flag_status"] = np.where(flagged, "flagged", "clear")
    df["model_version"] = "isolation_forest_v1"

    output_df = df[[
        "vector_id", "agent_id", "suspicion_score", "flag_status", "model_version"
    ]].copy()
    output_df.insert(0, "flag_id", [f"FL{i+1}" for i in range(len(output_df))])

    output_df.to_csv("data/synthetic/fraud_flags.csv", index=False)

    print(f"\nDone. {flagged.sum()} agents flagged out of {len(df)} total.")
    print("\nTop 10 most suspicious agents:")
    top10 = df.sort_values("suspicion_score", ascending=False).head(10)
    print(top10[["agent_id", "is_fraud", "suspicion_score", "flag_status"]].to_string(index=False))

    evaluate(df, suspicion_score, flagged)

    print("\nSaved to data/synthetic/fraud_flags.csv")


if __name__ == "__main__":
    main()