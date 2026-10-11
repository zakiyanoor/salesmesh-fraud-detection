"""
Per-agent explanations (Step 10).

Method: robust deviation. For each feature, d = (value - training median) /
max(training IQR, IQR_FLOOR), with median and IQR computed on TRAINING agents
only, without labels. top_features = the TOP_K features with the largest |d|,
for every agent. The plain-language reason (flagged agents only) lists the
first of those and any other with |d| >= MIN_ABS_DEVIATION, each against the
typical (training median) value.

Robust statistics are used because a few extreme agents (e.g. sequential
agents' customer_similarity) inflate the standard deviation and hide moderate
deviations. SHAP TreeExplainer was the first choice for Isolation Forest, but
shap is not installed, so this model-agnostic method is used. It describes how
unusual an agent is on each feature, not the forest's internal attribution.
Explanations never change scores, flags or the cutoff.
"""

import numpy as np
import pandas as pd

TOP_K = 3
MIN_ABS_DEVIATION = 1.0
IQR_FLOOR = 1e-3
EXPLANATION_METHOD = "robust deviation: (value - training median) / max(training IQR, 1e-3); SHAP not installed"


def describe(feature, value, typical):
    if feature == "submission_frequency":
        return f"busiest 24 hours: {value:.0f} submissions vs typical {typical:.0f}"
    if feature == "time_of_day_entropy":
        shape = "concentrated in few hours" if value < typical else "spread over unusual hours"
        return f"submission times {shape}: entropy {value:.2f} vs typical {typical:.2f}"
    if feature == "customer_similarity":
        shape = "look alike" if value >= typical else "are less alike than usual"
        return f"customer IDs {shape}: similarity {value:.3f} vs typical {typical:.3f}"
    if feature == "collusion_score":
        return f"{value:.0%} of customers also used by other agents vs typical {typical:.0%}"
    if feature == "volume_vs_peers":
        return f"volume {value:.1f}x the peer median vs typical {typical:.1f}x"
    return f"{feature} {value:.3g} vs typical {typical:.3g}"


def reference_stats(train_df, columns):
    """Training-only median and IQR per feature (no labels)."""
    q1, median, q3 = (train_df[list(columns)].quantile(q) for q in (0.25, 0.5, 0.75))
    return {c: {"median": float(median[c]), "iqr": float(q3[c] - q1[c])} for c in columns}


def deviations(reference, columns, df):
    medians = np.array([reference[c]["median"] for c in columns])
    scales = np.array([max(reference[c]["iqr"], IQR_FLOOR) for c in columns])
    return (df[list(columns)].values - medians) / scales


def top_contributions(reference, columns, df, k=TOP_K):
    """List of [(feature, d), ...] per row, largest |d| first."""
    d = deviations(reference, columns, df)
    order = np.argsort(-np.abs(d), axis=1, kind="stable")[:, :k]
    return [[(columns[j], float(d[i, j])) for j in order[i]] for i in range(len(df))]


def top_features(reference, columns, df, k=TOP_K):
    return [";".join(f for f, _ in c) for c in top_contributions(reference, columns, df, k)]


def reasons(reference, columns, df, k=TOP_K):
    out = []
    for (_, row), contributions in zip(df.iterrows(), top_contributions(reference, columns, df, k)):
        shown = [c for i, c in enumerate(contributions) if i == 0 or abs(c[1]) >= MIN_ABS_DEVIATION]
        out.append("; ".join(describe(f, row[f], reference[f]["median"]) for f, _ in shown))
    return out


def top_feature_table(reference, columns, df):
    contributions = top_contributions(reference, columns, df)
    return pd.DataFrame({"agent_id": df["agent_id"].values,
                         "top_feature": [c[0][0] for c in contributions],
                         "top_features": [";".join(f for f, _ in c) for c in contributions]})
