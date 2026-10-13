"""
Step 12a: 5-fold cross-validation on the training and validation agents only
(850 agents; test agents excluded, their labels never read). Informational: it
does not change the selection.

Folds are stratified by pattern (split.strata: legit, or the fraud pattern), at
agent level, seed CV_SEED. In each fold the scaler and the model are fitted on
the fold's training part only. Settings are fixed (no tuning):
- lof_v3_4f, the chosen model;
- Isolation Forest, 4 features, 100 trees, max_samples 64, max_features 0.8
  (sensitivity comparison: the pick had a LOF sorted after the forests);
- baselines: random scores (mean of 20 seeds), the volume rule (cap = P90 of
  the fold's training part), the best single feature from Step 7
  (collusion_score, higher = more suspicious) and duplicate_activation_rule.
Ranking methods are flagged at the ALERT_BUDGET (15%); the two rules use their
own flags. Recall by pattern is pooled over the out-of-fold flags.

Usage: python cross_validation.py [--data-dir DIR]
Output: ml/runs/<run_id>/ with cv_folds.csv, cv_summary.csv, cv_pattern_recall.csv
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

from baselines import DUPLICATE_RULE, RANDOM_SEEDS, RULE_FEATURE, RULE_PERCENTILE, duplicate_activation_counts
from data_generation import DEFAULT_OUT_DIR
from detectors import FITTERS
from feature_engineering import MODEL_FEATURES
from labels_guard import load_labelled
from metrics import FRAUD_PATTERNS, budget_flags, evaluate
from split import strata

CV_FOLDS = 5
CV_SEED = 42
MODEL_SEED = 42
MODELS = {
    "lof_v3_4f (chosen)": ("lof", {"n_neighbors": 50}),
    "isolation_forest 100/64/0.8 (sensitivity)": ("isolation_forest",
                                                  {"n_estimators": 100, "max_samples": 64, "max_features": 0.8}),
}
BEST_SINGLE_FEATURE = "collusion_score"


def fold_methods(train, test, duplicate_counts):
    """{method: (scores, flags)} for one fold's test part."""
    out = {}
    for name, (model, params) in MODELS.items():
        scores = FITTERS[model](train, MODEL_FEATURES, MODEL_SEED, **params).score(test)
        out[name] = (scores, budget_flags(scores))
    cap = float(train[RULE_FEATURE].quantile(RULE_PERCENTILE))
    volume = test[RULE_FEATURE].values.astype(float)
    out[f"rule: {RULE_FEATURE} > fold-train P{int(RULE_PERCENTILE * 100)}"] = (volume, volume > cap)
    single = test[BEST_SINGLE_FEATURE].values.astype(float)
    out[f"best single feature: {BEST_SINGLE_FEATURE} (+)"] = (single, budget_flags(single))
    dup = test["agent_id"].map(duplicate_counts).fillna(0).values.astype(float)
    out[f"rule: {DUPLICATE_RULE} (pairs > 0)"] = (dup, dup > 0)
    return out


def cross_validate(agents, duplicate_counts, folds=CV_FOLDS, seed=CV_SEED):
    agents = agents.reset_index(drop=True)
    stratum = strata(agents)
    rows, out_of_fold = [], []
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    for fold, (train_idx, test_idx) in enumerate(splitter.split(agents, stratum), start=1):
        train, test = agents.iloc[train_idx], agents.iloc[test_idx]
        y, profiles = test["is_fraud"].values, test["profile"].values
        base = {"fold": fold, "train_agents": len(train), "test_agents": len(test), "test_fraud": int(y.sum())}
        random_runs = pd.DataFrame([evaluate(y, np.random.default_rng(s).random(len(test)), profiles)
                                    for s in RANDOM_SEEDS])
        rows.append({**base, "method": f"random scores (mean of {len(RANDOM_SEEDS)} seeds)", **random_runs.mean().to_dict()})
        for method, (scores, flags) in fold_methods(train, test, duplicate_counts).items():
            rows.append({**base, "method": method, **evaluate(y, scores, profiles, flags=flags)})
            out_of_fold.append(pd.DataFrame({"method": method, "agent_id": test["agent_id"].values,
                                             "profile": profiles, "is_fraud": y, "flag": flags}))
    return pd.DataFrame(rows), pd.concat(out_of_fold, ignore_index=True)


def summarise(folds):
    summary = folds.groupby("method", sort=False)[["pr_auc", "roc_auc", "precision", "recall", "f1"]].agg(["mean", "std"])
    summary.columns = [f"{metric}_{stat}" for metric, stat in summary.columns]
    return summary.reset_index()


def pooled_pattern_recall(out_of_fold):
    fraud = out_of_fold[out_of_fold["is_fraud"]]
    table = fraud.pivot_table(index="method", columns="profile", values="flag", aggfunc="mean", sort=False)
    table = table.reindex(columns=FRAUD_PATTERNS)
    table["all_fraud"] = fraud.groupby("method", sort=False)["flag"].mean()
    honest = out_of_fold[~out_of_fold["is_fraud"]]
    table["honest_flag_rate"] = honest.groupby("method", sort=False)["flag"].mean()
    return table.reset_index()


def main(argv=None):
    from run_utils import start_run

    parser = argparse.ArgumentParser(description="Step 12a: 5-fold CV on training and validation agents.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    parts = load_labelled(args.data_dir, ["train", "validation"])
    agents = pd.concat([parts["train"], parts["validation"]], ignore_index=True)
    duplicate_counts = duplicate_activation_counts(pd.read_csv(args.data_dir / "activation_records_clean.csv"))
    inputs = [args.data_dir / f for f in ["feature_vectors.csv", "split.csv", "labels.csv", "activation_records_clean.csv"]]
    run_dir = start_run("cross_validation", CV_SEED, {
        "folds": CV_FOLDS, "agents": "train + validation", "stratified_by": "pattern", "models": MODELS,
        "features": MODEL_FEATURES, "best_single_feature": BEST_SINGLE_FEATURE, "alert_budget_for_ranking": 0.15,
        "informational": "does not change the selection"}, inputs)

    folds, out_of_fold = cross_validate(agents, duplicate_counts)
    summary, patterns = summarise(folds), pooled_pattern_recall(out_of_fold)
    folds.to_csv(run_dir / "cv_folds.csv", index=False)
    summary.to_csv(run_dir / "cv_summary.csv", index=False)
    patterns.to_csv(run_dir / "cv_pattern_recall.csv", index=False)

    pd.set_option("display.width", 250)
    print(f"{len(agents)} agents ({int(agents['is_fraud'].sum())} fraud), {CV_FOLDS} folds, seed {CV_SEED}. Informational only.\n")
    print(folds.pivot_table(index="method", columns="fold", values=["pr_auc", "roc_auc"], sort=False).round(3).to_string())
    print("\nMean and standard deviation over folds:")
    print(summary.round(3).to_string(index=False))
    print("\nRecall by pattern, pooled out-of-fold (ranking methods at the 15% budget; rules at their own flags):")
    print(patterns.round(2).to_string(index=False))
    print(f"Run folder {run_dir}")


if __name__ == "__main__":
    main()
