"""
Per-agent explanations (Step 10).

Method: robust deviation. For each feature, d = (value - training median) /
max(training IQR, IQR_FLOOR), with median and IQR computed on TRAINING agents
only, without labels. top_features = the TOP_K features with the largest |d|,
for every agent. The plain-language reason (flagged agents only) lists each of
those that is unusual on both scales: |d| >= MIN_ABS_DEVIATION and |value -
training median| >= MIN_RANGE_SHARE of the training P5-P95 range. The second
condition stops a tiny IQR (customer_similarity) from turning a difference of
0.002 into a reason. If no feature passes, the reason says the combination is
unusual. Each shown feature is described against the typical (median) value,
with the share of training agents it is higher (or lower) than.

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
MIN_RANGE_SHARE = 0.10
COMBINATION_REASON = "no single feature far from typical; flagged on the combination of features"
IQR_FLOOR = 1e-3
EXPLANATION_METHOD = ("robust deviation: (value - training median) / max(training IQR, 1e-3); reason shows a feature "
                      "if |deviation| >= 1 and |value - median| >= 10% of the training P5-P95 range; SHAP not installed")


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
    """Training-only median, IQR, P5, P95 and sorted values per feature (no labels)."""
    p5, q1, median, q3, p95 = (train_df[list(columns)].quantile(q) for q in (0.05, 0.25, 0.5, 0.75, 0.95))
    return {c: {"median": float(median[c]), "iqr": float(q3[c] - q1[c]), "p5": float(p5[c]), "p95": float(p95[c]),
                "values": sorted(float(v) for v in train_df[c])}
            for c in columns}


def percentile_phrase(stats, value):
    """Share of training agents strictly below (value at or above the median) or strictly above (below it)."""
    if "values" not in stats:
        return ""
    values = np.asarray(stats["values"])
    if value >= stats["median"]:
        share = np.searchsorted(values, value, side="left") / len(values)
        return f" (higher than {int(np.floor(100 * share))} percent of training agents)"
    share = (len(values) - np.searchsorted(values, value, side="right")) / len(values)
    return f" (lower than {int(np.floor(100 * share))} percent of training agents)"


def shown_in_reason(stats, value, d):
    """Display rule: unusual in IQR units and by at least MIN_RANGE_SHARE of the training P5-P95 range."""
    if abs(d) < MIN_ABS_DEVIATION:
        return False
    if "p5" not in stats:
        return True
    return abs(value - stats["median"]) >= MIN_RANGE_SHARE * (stats["p95"] - stats["p5"])


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
        shown = [f for f, d in contributions if shown_in_reason(reference[f], row[f], d)]
        out.append("; ".join(describe(f, row[f], reference[f]["median"]) + percentile_phrase(reference[f], row[f])
                             for f in shown) or COMBINATION_REASON)
    return out


def top_feature_table(reference, columns, df):
    contributions = top_contributions(reference, columns, df)
    return pd.DataFrame({"agent_id": df["agent_id"].values,
                         "top_feature": [c[0][0] for c in contributions],
                         "top_features": [";".join(f for f, _ in c) for c in contributions]})
