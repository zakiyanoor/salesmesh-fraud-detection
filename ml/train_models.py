"""
Models with default settings (Step 8): fit on TRAINING, score VALIDATION.

Isolation Forest (n_estimators 200, contamination "auto", seeded) and LOF
(novelty=True, n_neighbors 20), each with the four base features and with all
five (adding volume_vs_peers). No tuning here; Step 9 tunes and chooses on
validation with a rule written in advance. Test labels are never loaded.

Reported per model: ROC AUC, PR AUC (with the random baseline), precision,
recall and F1 at the ALERT_BUDGET operating point, recall by fraud pattern,
the same threshold-free metrics on the training agents (overfitting check),
training time, scoring time per agent and model file size.

Usage: python train_models.py [--data-dir DIR]
Output: ml/runs/<run_id>/ with run_info.json, model_metrics.csv and one <model>.joblib per model
"""

import argparse
import statistics
import time
from pathlib import Path

import joblib

from data_generation import DEFAULT_OUT_DIR
from detectors import FITTERS, IF_DEFAULTS, LOF_DEFAULTS, MODEL_SEED
from feature_engineering import ALL_FEATURES, BASE_FEATURES
from labels_guard import load_labelled
from metrics import ALERT_BUDGET, FRAUD_PATTERNS, evaluate

FEATURE_SETS = {"4 features": BASE_FEATURES, "5 features": ALL_FEATURES}
TIMING_REPEATS = 5


def timed(fn, repeats=TIMING_REPEATS):
    times, result = [], None
    for _ in range(repeats):
        start = time.perf_counter()
        result = fn()
        times.append(time.perf_counter() - start)
    return result, statistics.median(times)


def run_models(data_dir=DEFAULT_OUT_DIR, out_dir=None):
    parts = load_labelled(data_dir, ["train", "validation"])
    train, val = parts["train"], parts["validation"]
    rows = []
    for model_name, fit in FITTERS.items():
        for set_name, columns in FEATURE_SETS.items():
            detector, fit_seconds = timed(lambda: fit(train, columns, MODEL_SEED))
            val_scores, score_seconds = timed(lambda: detector.score(val))
            train_metrics = evaluate(train["is_fraud"], detector.training_scores(train), train["profile"])
            val_metrics = evaluate(val["is_fraud"], val_scores, val["profile"])
            size = None
            if out_dir is not None:
                path = Path(out_dir) / f"{model_name}_{set_name.split()[0]}f.joblib"
                joblib.dump(detector.artifact(), path)
                size = path.stat().st_size
            rows.append({"model": model_name, "features": set_name, **val_metrics,
                         "train_roc_auc": train_metrics["roc_auc"], "train_pr_auc": train_metrics["pr_auc"],
                         "train_pr_auc_random": train_metrics["pr_auc_random"],
                         "fit_seconds": fit_seconds, "score_ms_per_agent": 1000 * score_seconds / len(val),
                         "model_file_bytes": size})
    import pandas as pd

    return pd.DataFrame(rows), len(train), len(val), int(val["is_fraud"].sum())


def main(argv=None):
    from run_utils import start_run

    parser = argparse.ArgumentParser(description="Step 8: default Isolation Forest and LOF on validation.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    inputs = [args.data_dir / f for f in ["feature_vectors.csv", "split.csv", "labels.csv"]]
    run_dir = start_run("models_default", MODEL_SEED, {"isolation_forest": IF_DEFAULTS, "lof": {**LOF_DEFAULTS, "novelty": True},
                                                       "feature_sets": FEATURE_SETS, "alert_budget": ALERT_BUDGET,
                                                       "fitted_on": "train", "evaluated_on": "validation",
                                                       "timing_repeats": TIMING_REPEATS}, inputs)
    table, n_train, n_val, n_val_fraud = run_models(args.data_dir, run_dir)
    table.to_csv(run_dir / "model_metrics.csv", index=False)

    view = table.set_index(["model", "features"])
    print(f"Fitted on {n_train} training agents; evaluated on {n_val} validation agents ({n_val_fraud} fraud). "
          f"Alert budget: top {ALERT_BUDGET:.0%}.\n")
    print("Validation:")
    print(view[["roc_auc", "pr_auc", "pr_auc_random", "flagged", "precision", "recall", "f1"]].round(3).to_string())
    print("\nRecall by fraud pattern (validation, at the alert budget):")
    print(view[[f"recall_{p}" for p in FRAUD_PATTERNS]].round(2).to_string())
    print("\nTraining vs validation (threshold-free):")
    print(view[["train_roc_auc", "roc_auc", "train_pr_auc", "train_pr_auc_random", "pr_auc"]].round(3).to_string())
    print("\nCost:")
    print(view[["fit_seconds", "score_ms_per_agent", "model_file_bytes"]].round(4).to_string())
    print(f"\nRun folder {run_dir}")


if __name__ == "__main__":
    main()
