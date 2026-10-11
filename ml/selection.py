"""
Model selection and operating point (Step 9), on VALIDATION only.

Implements ml/results/selection_rule.md (with its post hoc amendment of the
tie rule, made on validation only before any test result; the original rule is
kept as choose_original) and the operating-point rule in
ml/results/acceptance_criteria.md.
Test labels are never loaded.

contamination stays "auto": it only sets the cutoff behind predict(); the
scores (score_samples) and so their ranking, ROC AUC and PR AUC do not depend
on it. The operating cutoff is chosen from validation scores directly.

Usage: python selection.py [--data-dir DIR]
Output: ml/runs/<run_id>/ with grid_per_seed.csv, grid.csv, tie_set.csv, operating_points.csv,
        pattern_recall.csv, chosen_model.joblib, operating_point.json, report.md
"""

import argparse
import io
import itertools
import json
import statistics
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from data_generation import DEFAULT_OUT_DIR
from detectors import FITTERS
from labels_guard import load_labelled
from metrics import ALERT_BUDGET, FRAUD_PATTERNS, budget_flags, evaluate
from train_models import FEATURE_SETS

SELECTION_SEEDS = [1, 2, 3, 4, 5]
FINAL_MODEL_SEED = 42
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 0
TIE_MARGIN = 0.02
HEAVY_OVERLAP = 0.75
IF_GRID = {"n_estimators": [100, 200, 500], "max_samples": [64, 128, 256], "max_features": [0.6, 0.8, 1.0]}
LOF_GRID = {"n_neighbors": [10, 20, 35, 50, 100]}
COST_MISSED_FRAUD, COST_FALSE_ALARM = 5, 1
SENSITIVITY_RATIOS = [2, 10]
TIMING_REPEATS = 5


def candidates():
    grids = {"isolation_forest": IF_GRID, "lof": LOF_GRID}
    for model, grid in grids.items():
        for values in itertools.product(*grid.values()):
            for feature_set in FEATURE_SETS:
                yield {"model": model, "features": feature_set, "params": dict(zip(grid, values))}


def bootstrap_weights(y, resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED):
    """(resamples x n) count matrix; resamples without a fraud agent are redrawn."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y, dtype=bool)
    rows = []
    while len(rows) < resamples:
        counts = np.bincount(rng.integers(0, len(y), len(y)), minlength=len(y))
        if (counts * y).sum() > 0:
            rows.append(counts)
    return np.array(rows)


def weighted_average_precision(y, scores, weights):
    """Average precision for each row of weights (agents with distinct scores); equals sklearn's per resample."""
    order = np.argsort(-np.asarray(scores, dtype=float), kind="stable")
    y = np.asarray(y, dtype=float)[order]
    w = np.atleast_2d(weights)[:, order]
    tp = np.cumsum(w * y, axis=1)
    seen = np.cumsum(w, axis=1)
    precision = np.divide(tp, seen, out=np.zeros_like(tp, dtype=float), where=seen > 0)
    return (w * y * precision).sum(axis=1) / (w * y).sum(axis=1)


def model_bytes(detector):
    buffer = io.BytesIO()
    joblib.dump(detector.artifact(), buffer)
    return buffer.getbuffer().nbytes


def run_candidate(candidate, train, val, weights):
    columns = FEATURE_SETS[candidate["features"]]
    fit = FITTERS[candidate["model"]]
    seeds = SELECTION_SEEDS if candidate["model"] == "isolation_forest" else SELECTION_SEEDS[:1]
    per_seed, boot = [], []
    for seed in seeds:
        start = time.perf_counter()
        detector = fit(train, columns, seed, **candidate["params"])
        fit_seconds = time.perf_counter() - start
        scores = detector.score(val)
        train_scores = detector.training_scores(train)
        per_seed.append({"seed": seed, "pr_auc": average_precision_score(val["is_fraud"], scores),
                         "roc_auc": roc_auc_score(val["is_fraud"], scores),
                         "train_pr_auc": average_precision_score(train["is_fraud"], train_scores),
                         "train_roc_auc": roc_auc_score(train["is_fraud"], train_scores),
                         "fit_seconds": fit_seconds})
        boot.append(weighted_average_precision(val["is_fraud"].values, scores, weights))
        if seed == seeds[0]:
            size = model_bytes(detector)
            times = []
            for _ in range(TIMING_REPEATS):
                start = time.perf_counter()
                detector.score(val)
                times.append(time.perf_counter() - start)
            score_ms = 1000 * statistics.median(times) / len(val)
    if len(seeds) == 1:
        per_seed = [{**per_seed[0], "seed": s} for s in SELECTION_SEEDS]
    boot_mean = np.mean(boot, axis=0)
    seeds_frame = pd.DataFrame(per_seed)
    summary = {
        "model": candidate["model"], "features": candidate["features"], "n_features": len(columns),
        **{k: candidate["params"].get(k, "") for k in [*IF_GRID, *LOF_GRID]},
        "pr_auc_mean": seeds_frame["pr_auc"].mean(), "pr_auc_std": seeds_frame["pr_auc"].std(ddof=0),
        "pr_auc_ci_low": float(np.percentile(boot_mean, 2.5)), "pr_auc_ci_high": float(np.percentile(boot_mean, 97.5)),
        "roc_auc_mean": seeds_frame["roc_auc"].mean(),
        "train_pr_auc_mean": seeds_frame["train_pr_auc"].mean(), "train_roc_auc_mean": seeds_frame["train_roc_auc"].mean(),
        "model_bytes": size, "fit_seconds_mean": seeds_frame["fit_seconds"].mean(), "score_ms_per_agent": score_ms,
    }
    return summary, seeds_frame.assign(model=candidate["model"], features=candidate["features"],
                                       params=json.dumps(candidate["params"]))


def ci_overlap_share(a_low, a_high, b_low, b_high):
    overlap = max(0.0, min(a_high, b_high) - max(a_low, b_low))
    shorter = min(a_high - a_low, b_high - b_low)
    return overlap / shorter if shorter > 0 else 0.0


def choose_original(grid):
    """ORIGINAL rule (superseded, kept for the record): margin OR heavy CI overlap, then size."""
    top = grid.sort_values("pr_auc_mean", ascending=False).iloc[0]
    overlap = grid.apply(lambda r: ci_overlap_share(top["pr_auc_ci_low"], top["pr_auc_ci_high"],
                                                    r["pr_auc_ci_low"], r["pr_auc_ci_high"]), axis=1)
    within = (top["pr_auc_mean"] - grid["pr_auc_mean"]) < TIE_MARGIN
    ties = grid.assign(ci_overlap_with_top=overlap, within_margin=within)
    ties = ties[within | (overlap >= HEAVY_OVERLAP)]
    chosen = ties.sort_values(["n_features", "model_bytes", "pr_auc_mean"], ascending=[True, True, False]).iloc[0]
    return chosen, ties, top


def choose(grid):
    """
    AMENDED rule (post hoc, on validation only, before any test result): tied =
    within TIE_MARGIN of the top mean PR AUC; simplest first = fewer features,
    fewer trees, smaller max_samples, then faster scoring.
    Returns (chosen row, tie-set frame, top row).
    """
    top = grid.sort_values("pr_auc_mean", ascending=False).iloc[0]
    ties = grid[(top["pr_auc_mean"] - grid["pr_auc_mean"]) < TIE_MARGIN].copy()
    ties["_trees"] = pd.to_numeric(ties["n_estimators"], errors="coerce").fillna(0)
    ties["_samples"] = pd.to_numeric(ties["max_samples"], errors="coerce").fillna(0)
    chosen = ties.sort_values(["n_features", "_trees", "_samples", "score_ms_per_agent"]).iloc[0]
    return chosen, ties.drop(columns=["_trees", "_samples"]), top


ACCEPTANCE_BEST_SINGLE_FEATURE_PR_AUC = 0.541
ACCEPTANCE_MAX_GAP = 0.10
ACCEPTANCE_MIN_RECALL = 0.60
ACCEPTANCE_MAX_ALERT_RATE = 0.25
ACCEPTANCE_RANDOM_MULTIPLE = 3


def acceptance_on_validation(chosen, y, scores, train_roc_auc, cutoff):
    """Q1-Q6 of the draft acceptance criteria, measured on validation (the final check is Step 11 on test)."""
    y = np.asarray(y, dtype=bool)
    pr = average_precision_score(y, scores)
    ci = np.percentile(weighted_average_precision(y, scores, bootstrap_weights(y)), [2.5, 97.5])
    flags = scores >= cutoff
    recall = flags[y].mean()
    gap = train_roc_auc - roc_auc_score(y, scores)
    rows = [
        ("Q1", "mean validation PR AUC over seeds 1-5 > best single feature (0.541)", chosen["pr_auc_mean"],
         chosen["pr_auc_mean"] > ACCEPTANCE_BEST_SINGLE_FEATURE_PR_AUC),
        ("Q2", "PR AUC (seed 42 model) > best single feature (0.541)", pr, pr > ACCEPTANCE_BEST_SINGLE_FEATURE_PR_AUC),
        ("Q3", f"PR AUC >= {ACCEPTANCE_RANDOM_MULTIPLE} x fraud rate ({y.mean():.3f}) and CI low > fraud rate",
         f"{pr:.3f} (CI {ci[0]:.3f}-{ci[1]:.3f})", pr >= ACCEPTANCE_RANDOM_MULTIPLE * y.mean() and ci[0] > y.mean()),
        ("Q4", "train ROC AUC - validation ROC AUC <= 0.10", gap, gap <= ACCEPTANCE_MAX_GAP),
        ("Q5", "recall at the cutoff >= 0.60", recall, recall >= ACCEPTANCE_MIN_RECALL),
        ("Q6", "alert rate at the cutoff <= 25%", flags.mean(), flags.mean() <= ACCEPTANCE_MAX_ALERT_RATE),
    ]
    return pd.DataFrame([{"criterion": c, "condition": cond, "value": v, "result": "PASS" if ok else "FAIL",
                          "measured_on": "validation (final check: Step 11, test)"} for c, cond, v, ok in rows])


def cutoff_metrics(y, scores, profiles, cutoff):
    flags = scores >= cutoff
    result = evaluate(y, scores, profiles, flags=flags)
    result["alert_rate"] = flags.mean()
    return result


def midpoint_cutoff(scores, n_flagged):
    ordered = np.sort(scores)[::-1]
    if n_flagged <= 0:
        return float(ordered[0]) + 1e-9
    if n_flagged >= len(ordered):
        return float(ordered[-1])
    return float((ordered[n_flagged - 1] + ordered[n_flagged]) / 2)


def min_cost_count(y, scores, ratio):
    """Number of top-scored agents to flag that minimises ratio*FN + FP; ties -> fewer alerts."""
    y_sorted = np.asarray(y, dtype=bool)[np.argsort(-scores, kind="stable")]
    tp = np.concatenate([[0], np.cumsum(y_sorted)])
    k = np.arange(len(y_sorted) + 1)
    cost = ratio * (y_sorted.sum() - tp) + (k - tp)
    return int(np.argmin(cost)), cost


def operating_points(y, scores, profiles):
    y = np.asarray(y, dtype=bool)
    rows = []
    for ratio in [COST_MISSED_FRAUD, *SENSITIVITY_RATIOS]:
        k, _ = min_cost_count(y, scores, ratio)
        rows.append({"rule": f"min expected cost {ratio}:1", "ratio": ratio, "cutoff": midpoint_cutoff(scores, k)})
    order = np.argsort(-scores, kind="stable")
    tp = np.cumsum(y[order])
    k = np.arange(1, len(y) + 1)
    f1 = 2 * tp / (k + y.sum())
    rows.append({"rule": "max F1", "ratio": None, "cutoff": midpoint_cutoff(scores, int(np.argmax(f1)) + 1)})
    rows.append({"rule": f"alert budget {ALERT_BUDGET:.0%}", "ratio": None,
                 "cutoff": midpoint_cutoff(scores, int(budget_flags(scores).sum()))})
    table = []
    for row in rows:
        m = cutoff_metrics(y, scores, profiles, row["cutoff"])
        cost = {f"cost_per_agent_{r}to1": (r * m["fn"] + m["fp"]) / len(y) for r in [COST_MISSED_FRAUD, *SENSITIVITY_RATIOS]}
        table.append({**row, **m, **cost})
    return pd.DataFrame(table)


def main(argv=None):
    from run_utils import start_run

    parser = argparse.ArgumentParser(description="Step 9: grid selection and operating point on validation.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    parts = load_labelled(args.data_dir, ["train", "validation"])
    train, val = parts["train"], parts["validation"]
    inputs = [args.data_dir / f for f in ["feature_vectors.csv", "split.csv", "labels.csv"]]
    run_dir = start_run("selection", FINAL_MODEL_SEED, {
        "selection_seeds": SELECTION_SEEDS, "bootstrap_resamples": BOOTSTRAP_RESAMPLES, "bootstrap_seed": BOOTSTRAP_SEED,
        "tie_margin": TIE_MARGIN, "heavy_overlap": HEAVY_OVERLAP, "if_grid": IF_GRID, "lof_grid": LOF_GRID,
        "contamination": "auto", "cost_missed_fraud": COST_MISSED_FRAUD, "cost_false_alarm": COST_FALSE_ALARM,
        "sensitivity_ratios": SENSITIVITY_RATIOS, "fitted_on": "train", "evaluated_on": "validation"}, inputs)

    weights = bootstrap_weights(val["is_fraud"].values)
    summaries, seed_rows = [], []
    for candidate in candidates():
        summary, seeds = run_candidate(candidate, train, val, weights)
        summaries.append(summary)
        seed_rows.append(seeds)
    grid = pd.DataFrame(summaries).sort_values("pr_auc_mean", ascending=False).reset_index(drop=True)
    grid.to_csv(run_dir / "grid.csv", index=False)
    pd.concat(seed_rows).to_csv(run_dir / "grid_per_seed.csv", index=False)

    chosen, ties, top = choose(grid)
    ties.to_csv(run_dir / "tie_set.csv", index=False)
    original_pick, original_ties, _ = choose_original(grid)
    original_ties.to_csv(run_dir / "tie_set_original_rule.csv", index=False)
    params = {k: chosen[k] for k in (IF_GRID if chosen["model"] == "isolation_forest" else LOF_GRID)}
    params = {k: (int(v) if float(v).is_integer() and k != "max_features" else float(v)) for k, v in params.items()}
    columns = FEATURE_SETS[chosen["features"]]
    detector = FITTERS[chosen["model"]](train, columns, FINAL_MODEL_SEED, **params)
    val_scores = detector.score(val)
    train_scores = detector.training_scores(train)
    points = operating_points(val["is_fraud"].values, val_scores, val["profile"].values)
    points.to_csv(run_dir / "operating_points.csv", index=False)
    operating = points.iloc[0]

    model_version = f"{'if' if chosen['model'] == 'isolation_forest' else 'lof'}_v3_{int(chosen['n_features'])}f"
    config = {"model_version": model_version, "model": chosen["model"], "params": params,
              "feature_columns": columns, "model_seed": FINAL_MODEL_SEED, "contamination": "auto",
              "threshold": float(operating["cutoff"]), "threshold_rule": operating["rule"],
              "score_direction": "higher = more anomalous", "flag_if": "score >= threshold",
              "chosen_on": "validation", "selection_run": run_dir.name}
    (run_dir / "operating_point.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    joblib.dump({**detector.artifact(), "model_version": model_version, "operating_point": config},
                run_dir / "chosen_model.joblib")

    train_eval = evaluate(train["is_fraud"], train_scores, train["profile"], flags=train_scores >= operating["cutoff"])
    val_eval = evaluate(val["is_fraud"], val_scores, val["profile"], flags=val_scores >= operating["cutoff"])
    gap = pd.DataFrame({"train": train_eval, "validation": val_eval}).loc[
        ["roc_auc", "pr_auc", "pr_auc_random", "precision", "recall", "f1", "flagged"]]
    pattern = points.set_index("rule")[[f"recall_{p}" for p in FRAUD_PATTERNS]]
    pattern.to_csv(run_dir / "pattern_recall.csv")
    acceptance = acceptance_on_validation(chosen, val["is_fraud"].values, val_scores, train_eval["roc_auc"],
                                          float(operating["cutoff"]))
    acceptance.to_csv(run_dir / "acceptance_validation.csv", index=False)

    best_other = grid[grid["features"] != chosen["features"]].iloc[0]
    same_family_other = grid[(grid["model"] == chosen["model"]) & (grid["features"] != chosen["features"])].iloc[0]
    overlap = ci_overlap_share(chosen["pr_auc_ci_low"], chosen["pr_auc_ci_high"],
                               same_family_other["pr_auc_ci_low"], same_family_other["pr_auc_ci_high"])
    cols = ["model", "features", "n_estimators", "max_samples", "max_features", "n_neighbors", "pr_auc_mean",
            "pr_auc_std", "pr_auc_ci_low", "pr_auc_ci_high", "roc_auc_mean", "train_roc_auc_mean", "model_bytes"]
    report = {
        "top": top[cols].to_dict(), "chosen": chosen[cols].to_dict(), "tie_set_size": len(ties),
        "original_rule_pick": original_pick[cols].to_dict(), "original_rule_tie_set_size": len(original_ties),
        "best_other_feature_set": best_other[cols].to_dict(), "four_vs_five_ci_overlap": overlap,
    }
    (run_dir / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    pd.set_option("display.width", 250)
    print(f"Train {len(train)} agents; validation {len(val)} agents ({int(val['is_fraud'].sum())} fraud); "
          f"{len(grid)} candidates x {len(SELECTION_SEEDS)} seeds.\n")
    print("Top 12 by mean validation PR AUC:")
    print(grid[cols].head(12).round(3).to_string(index=False))
    print("\nBest per model and feature set:")
    print(grid.groupby(["model", "features"]).head(1)[cols].round(3).to_string(index=False))
    print(f"\nOriginal rule (superseded): tie set {len(original_ties)}, pick {original_pick['model']} "
          f"{original_pick['features']} n_neighbors={original_pick['n_neighbors']} PR AUC {original_pick['pr_auc_mean']:.3f}")
    print(f"\nAmended rule: tie set = within {TIE_MARGIN} of top: {len(ties)} candidates.")
    print(ties[cols + ["score_ms_per_agent"]].round(4).to_string(index=False))
    print(f"\nCHOSEN: {model_version} {params}")
    print(f"Same-family best with the other feature set: {same_family_other['features']} "
          f"PR AUC {same_family_other['pr_auc_mean']:.3f} [{same_family_other['pr_auc_ci_low']:.3f}, "
          f"{same_family_other['pr_auc_ci_high']:.3f}]; CI overlap with chosen {overlap:.0%}.")
    print("\nOperating points on validation (final model, seed 42):")
    print(points[["rule", "cutoff", "flagged", "alert_rate", "precision", "recall", "f1",
                  "cost_per_agent_5to1", "cost_per_agent_2to1", "cost_per_agent_10to1"]].round(3).to_string(index=False))
    print("\nRecall by pattern at each operating point:")
    print(pattern.round(2).to_string())
    print("\nTrain vs validation (chosen model, at the 5:1 cutoff):")
    print(gap.round(3).to_string())
    print("\nAcceptance criteria Q1-Q6 on validation:")
    print(acceptance.to_string(index=False))
    print(f"\nRun folder {run_dir}")


if __name__ == "__main__":
    main()
