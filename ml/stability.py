"""
Step 12: stability across data seeds. For each of SEEDS (separate synthetic
datasets; the seed 42 test set is not touched again): generate, clean, compute
features, split 70/15/15 stratified by pattern (split.split_agents, seed 42
design), fit the scaler and lof_v3_4f (frozen settings) on training agents only,
and set the cutoff without labels as the validation-score quantile that flags
the validated alert rate (13.3%, from the seed 42 selection run). Each seed is
evaluated on its own test split: the model, duplicate_activation_rule and their
union (AUCs of the union are on its 0/1 flag). No tuning.

Usage: python stability.py
Output: ml/runs/<run_id>/ with stability_per_seed.csv, stability_summary.csv
"""

import json
import time

import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from baselines import duplicate_activation_counts
from clean_data import clean_data
from data_generation import generate_dataset
from detectors import fit_lof
from feature_engineering import MODEL_FEATURES, compute_feature_vectors
from retrain import quantile_cutoff
from split import split_agents

SEEDS = list(range(101, 111))
LOF_PARAMS = {"n_neighbors": 50}
VALIDATED_ALERT_RATE = 20 / 150
METRICS = ["pr_auc", "roc_auc", "precision", "recall", "f1"]


def scores_metrics(y, scores, flags):
    tp, fp, fn = int((flags & y).sum()), int((flags & ~y).sum()), int((~flags & y).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"pr_auc": average_precision_score(y, scores), "roc_auc": roc_auc_score(y, scores), "precision": precision,
            "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "flagged": int(flags.sum())}


def run_seed(seed):
    data = generate_dataset(seed)
    clean = clean_data(data.activations, data.agents, data.clients)[0]
    split = split_agents(data.labels)
    table = compute_feature_vectors(clean, data.agents).merge(split, on="agent_id").merge(data.labels, on="agent_id")
    train, val, test = (table[table["split"] == s] for s in ["train", "validation", "test"])
    detector = fit_lof(train, MODEL_FEATURES, **LOF_PARAMS)
    cutoff = quantile_cutoff(detector.score(val), VALIDATED_ALERT_RATE)
    y = test["is_fraud"].values.astype(bool)
    model_scores = detector.score(test)
    model_flags = model_scores >= cutoff
    dup = test["agent_id"].map(duplicate_activation_counts(clean)).fillna(0).values.astype(float)
    union = model_flags | (dup > 0)
    base = {"seed": seed, "test_agents": len(test), "test_fraud": int(y.sum()), "cutoff": cutoff}
    return [{**base, "method": "lof_v3_4f", **scores_metrics(y, model_scores, model_flags)},
            {**base, "method": "duplicate_activation_rule", **scores_metrics(y, dup, dup > 0)},
            {**base, "method": "union (secondary)", **scores_metrics(y, union.astype(float), union)}]


def main():
    from run_utils import start_run

    run_dir = start_run("stability", None, {"seeds": SEEDS, "model": "lof", "params": LOF_PARAMS, "features": MODEL_FEATURES,
                                            "validated_alert_rate": VALIDATED_ALERT_RATE, "split": "70/15/15 by pattern",
                                            "cutoff": "validation-score quantile, no labels"}, [])
    rows = []
    for seed in SEEDS:
        start = time.perf_counter()
        rows.extend(run_seed(seed))
        print(f"seed {seed} done in {time.perf_counter() - start:.0f} s", flush=True)
    per_seed = pd.DataFrame(rows)
    per_seed.to_csv(run_dir / "stability_per_seed.csv", index=False)
    summary = per_seed.groupby("method", sort=False)[METRICS].agg(["mean", "std", "min", "max"])
    summary.columns = [f"{m}_{s}" for m, s in summary.columns]
    summary.reset_index().to_csv(run_dir / "stability_summary.csv", index=False)
    (run_dir / "note.json").write_text(json.dumps({"seed_42_test_set": "not used; it was read once at Step 11"}), encoding="utf-8")
    pd.set_option("display.width", 250)
    print(per_seed.round(3).to_string(index=False))
    print(summary.round(3).to_string())
    print(f"Run folder {run_dir}")


if __name__ == "__main__":
    main()
