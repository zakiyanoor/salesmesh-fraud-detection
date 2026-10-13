"""Evaluation metrics shared by run_experiments.py and evaluate.py."""

from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score


def compute_metrics(y_true, scores, flags):
    """
    Precision/recall/F1 from the detector's own flags (its threshold), and
    ROC-AUC from its continuous scores (threshold-free).
    """
    y_true = [int(y) for y in y_true]
    y_pred = [int(f) for f in flags]
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, scores),
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
    }
