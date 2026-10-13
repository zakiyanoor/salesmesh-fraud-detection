"""
Evaluation metrics for Steps 7-11.

Operating point for the Step 7 and 8 tables, fixed before any result was seen:
flag the top ALERT_BUDGET share of agents by score (k = ceil(budget * n), ties
broken by row order). It is not the final threshold; Step 9 chooses that on
validation. ROC AUC and PR AUC are threshold-free and are the main comparison.
The PR AUC of a random score equals the fraud rate of the evaluated agents.
"""

import math

import numpy as np
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score

ALERT_BUDGET = 0.15
FRAUD_PATTERNS = ["ring", "weak_ring", "sequential", "duplicate", "weak"]


def budget_flags(scores, budget=ALERT_BUDGET):
    scores = np.asarray(scores, dtype=float)
    k = math.ceil(budget * len(scores))
    flags = np.zeros(len(scores), dtype=bool)
    flags[np.argsort(-scores, kind="stable")[:k]] = True
    return flags


def direction_free(auc):
    return max(auc, 1 - auc)


def evaluate(y_true, scores, profiles, flags=None, budget=ALERT_BUDGET):
    """Threshold-free metrics plus precision/recall/F1 and recall per fraud pattern at the flags (default: budget)."""
    y = np.asarray(y_true, dtype=bool)
    scores = np.asarray(scores, dtype=float)
    profiles = np.asarray(profiles)
    flags = budget_flags(scores, budget) if flags is None else np.asarray(flags, dtype=bool)
    tn, fp, fn, tp = confusion_matrix(y, flags, labels=[False, True]).ravel()
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    result = {
        "roc_auc": roc_auc_score(y, scores),
        "pr_auc": average_precision_score(y, scores),
        "pr_auc_random": y.mean(),
        "flagged": int(flags.sum()),
        "precision": precision, "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
    }
    for pattern in FRAUD_PATTERNS:
        mask = profiles == pattern
        result[f"recall_{pattern}"] = flags[mask].mean() if mask.any() else float("nan")
    return result
