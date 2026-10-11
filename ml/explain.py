"""
Per-agent explanations (Step 10).

Method: largest scaled deviations. For an agent, each feature's contribution is
|z|, its distance from the TRAINING mean in training standard deviations (the
model's own StandardScaler). The top TOP_K features by |z| are reported, with
the agent's value against the typical value (TRAINING median). Features
beyond the first are listed only if |z| >= MIN_ABS_Z, so reasons do not
pad with features that are not unusual. SHAP
TreeExplainer was the first choice for Isolation Forest, but shap is not
installed in this environment, so this model-agnostic fallback is used. It
describes how unusual an agent is on each feature, not the forest's exact
internal attribution.
"""

import numpy as np
import pandas as pd

TOP_K = 3
# A top-K feature is shown only if it deviates by at least this many training SDs (the first is always shown).
MIN_ABS_Z = 1.0
EXPLANATION_METHOD = "largest scaled deviation (|z| from the training mean, model scaler); SHAP not installed"


def describe(feature, value, typical):
    if feature == "submission_frequency":
        return f"busiest 24 hours: {value:.0f} submissions vs typical {typical:.0f}"
    if feature == "time_of_day_entropy":
        shape = "concentrated in few hours" if value < typical else "spread over unusual hours"
        return f"submission times {shape}: entropy {value:.2f} vs typical {typical:.2f}"
    if feature == "customer_similarity":
        return f"customer IDs look alike: similarity {value:.2f} vs typical {typical:.2f}"
    if feature == "collusion_score":
        return f"{value:.0%} of customers also used by other agents vs typical {typical:.0%}"
    if feature == "volume_vs_peers":
        return f"volume {value:.1f}x the peer median vs typical {typical:.1f}x"
    return f"{feature} {value:.3g} vs typical {typical:.3g}"


def top_contributions(scaler, columns, df, k=TOP_K):
    """List of [(feature, z), ...] per row, largest |z| first."""
    z = scaler.transform(df[list(columns)].values)
    order = np.argsort(-np.abs(z), axis=1, kind="stable")[:, :k]
    return [[(columns[j], float(z[i, j])) for j in order[i]] for i in range(len(df))]


def explain_rows(scaler, columns, reference, df, k=TOP_K):
    """(top_features strings, reason strings) for the given rows."""
    tops, reasons = [], []
    for (_, row), contributions in zip(df.iterrows(), top_contributions(scaler, columns, df, k)):
        contributions = [c for i, c in enumerate(contributions) if i == 0 or abs(c[1]) >= MIN_ABS_Z]
        tops.append(";".join(f for f, _ in contributions))
        reasons.append("; ".join(describe(f, row[f], reference[f]) for f, _ in contributions))
    return tops, reasons


def reference_medians(train_df, columns):
    return {c: float(train_df[c].median()) for c in columns}


def top_feature_table(scaler, columns, df):
    contributions = top_contributions(scaler, columns, df)
    return pd.DataFrame({"agent_id": df["agent_id"].values,
                         "top_feature": [c[0][0] for c in contributions],
                         "top_features": [";".join(f for f, _ in c) for c in contributions]})
