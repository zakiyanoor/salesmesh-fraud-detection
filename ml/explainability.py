"""
Explainability (Step 10), on VALIDATION only. Test labels are never loaded.

(a) permutation importance of the chosen model: PR AUC drop when one feature's
    validation values are shuffled, PERMUTATION_REPEATS repeats;
(b) feature ablation: the chosen configuration refitted on training with seeds
    1-5 for each feature set (drop one feature; volume_vs_peers in or out),
    mean validation PR AUC with a bootstrap 95% CI;
(c, d) top 3 features and a plain-language reason per flagged agent (explain.py);
(e) sanity check: top feature of every validation fraud agent against the
    feature expected for its pattern.
Also writes the scoring bundle and the validation scoring output.

Usage: python explainability.py [--data-dir DIR] [--selection-run DIR]
Output: ml/runs/<run_id>/ with permutation_importance.csv, ablation.csv, validation_scores.csv,
        pattern_sanity.csv, scoring_bundle.joblib, timing.json
"""

import argparse
import json
import statistics
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from data_generation import DEFAULT_OUT_DIR
from detectors import FITTERS
from explain import EXPLANATION_METHOD, reference_stats, top_feature_table
from feature_engineering import ALL_FEATURES, CANDIDATE_FEATURE
from labels_guard import load_labelled, load_unlabelled
from learning_curve import latest_selection_run
from metrics import FRAUD_PATTERNS
from scoring import score_agents
from selection import SELECTION_SEEDS, bootstrap_weights, weighted_average_precision

PERMUTATION_REPEATS = 20
EXPECTED_TOP_FEATURE = {"ring": "collusion_score", "sequential": "customer_similarity",
                        "duplicate": "customer_similarity", "weak_ring": "collusion_score"}
TIMING_REPEATS = 5


def permutation_importance(detector, val):
    base = average_precision_score(val["is_fraud"], detector.score(val))
    rows = []
    for feature in detector.columns:
        drops = []
        for repeat in range(PERMUTATION_REPEATS):
            shuffled = val.copy()
            shuffled[feature] = np.random.default_rng(repeat).permutation(shuffled[feature].values)
            drops.append(base - average_precision_score(val["is_fraud"], detector.score(shuffled)))
        rows.append({"feature": feature, "pr_auc_drop_mean": np.mean(drops), "pr_auc_drop_std": np.std(drops),
                     "pr_auc_drop_min": np.min(drops), "pr_auc_drop_max": np.max(drops)})
    return base, pd.DataFrame(rows).sort_values("pr_auc_drop_mean", ascending=False)


def ablation(train, val, model, params, base_columns):
    sets = {"chosen (4 features)": base_columns}
    for feature in base_columns:
        sets[f"without {feature}"] = [c for c in base_columns if c != feature]
    sets[f"with {CANDIDATE_FEATURE} (5 features)"] = list(ALL_FEATURES)
    weights = bootstrap_weights(val["is_fraud"].values)
    rows = []
    for name, columns in sets.items():
        pr, boot = [], []
        for seed in SELECTION_SEEDS:
            scores = FITTERS[model](train, columns, seed, **params).score(val)
            pr.append(average_precision_score(val["is_fraud"], scores))
            boot.append(weighted_average_precision(val["is_fraud"].values, scores, weights))
        boot_mean = np.mean(boot, axis=0)
        rows.append({"feature_set": name, "n_features": len(columns), "pr_auc_mean": np.mean(pr),
                     "pr_auc_std": np.std(pr), "ci_low": np.percentile(boot_mean, 2.5),
                     "ci_high": np.percentile(boot_mean, 97.5)})
    table = pd.DataFrame(rows)
    table["change_vs_chosen"] = table["pr_auc_mean"] - table.loc[0, "pr_auc_mean"]
    return table


def median_seconds(fn):
    times = []
    for _ in range(TIMING_REPEATS):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return statistics.median(times)


def main(argv=None):
    from run_utils import start_run

    parser = argparse.ArgumentParser(description="Step 10 explainability on validation.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--selection-run", type=Path, default=None)
    args = parser.parse_args(argv)

    selection_run = args.selection_run or latest_selection_run()
    chosen = joblib.load(selection_run / "chosen_model.joblib")
    config = chosen["operating_point"]
    parts = load_labelled(args.data_dir, ["train", "validation"])
    train, val = parts["train"], parts["validation"]
    inputs = [*(args.data_dir / f for f in ["feature_vectors.csv", "split.csv", "labels.csv"]),
              selection_run / "chosen_model.joblib"]
    run_dir = start_run("explain", None, {"selection_run": selection_run.name, "model_version": config["model_version"],
                                          "permutation_repeats": PERMUTATION_REPEATS, "ablation_seeds": SELECTION_SEEDS,
                                          "explanation_method": EXPLANATION_METHOD,
                                          "expected_top_feature": EXPECTED_TOP_FEATURE}, inputs)

    bundle = {**chosen, "reference_stats": reference_stats(train, chosen["feature_columns"]),
              "explanation_method": EXPLANATION_METHOD}
    joblib.dump(bundle, run_dir / "scoring_bundle.joblib")
    joblib.dump(chosen["scaler"], run_dir / "scaler.joblib")
    from scoring import detector_from

    detector = detector_from(bundle)

    base, importance = permutation_importance(detector, val)
    importance.to_csv(run_dir / "permutation_importance.csv", index=False)
    ablation_table = ablation(train, val, config["model"], config["params"], list(chosen["feature_columns"]))
    ablation_table.to_csv(run_dir / "ablation.csv", index=False)

    val_features = load_unlabelled(args.data_dir, "validation")
    output = score_agents(bundle, val_features)
    output.to_csv(run_dir / "validation_scores.csv", index=False)
    timing = {"score_only_ms_per_agent": 1000 * median_seconds(lambda: detector.score(val_features)) / len(val_features),
              "score_and_explain_all_rows_ms_per_agent": 1000 * median_seconds(lambda: score_agents(bundle, val_features)) / len(val_features),
              "agents": len(val_features), "flagged": int(output["flag"].sum())}
    (run_dir / "timing.json").write_text(json.dumps(timing, indent=2), encoding="utf-8")

    fraud = val[val["is_fraud"]]
    sanity = top_feature_table(bundle["reference_stats"], detector.columns, fraud).merge(
        fraud[["agent_id", "profile"]], on="agent_id").merge(output[["agent_id", "flag", "score"]], on="agent_id")
    sanity["expected"] = sanity["profile"].map(EXPECTED_TOP_FEATURE).fillna("(no expectation)")
    sanity["match"] = np.where(sanity["profile"].isin(EXPECTED_TOP_FEATURE), sanity["top_feature"] == sanity["expected"], np.nan)
    sanity = sanity.sort_values(["profile", "agent_id"])
    sanity.to_csv(run_dir / "pattern_sanity.csv", index=False)
    summary = sanity.groupby("profile").agg(agents=("agent_id", "size"), flagged=("flag", "sum"),
                                            expected=("expected", "first"),
                                            matches=("match", lambda m: int(np.nansum(m.astype(float)))))
    summary = summary.reindex([p for p in FRAUD_PATTERNS if p in summary.index])

    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 200)
    print(f"Model {config['model_version']} {config['params']}; threshold {config['threshold']:.3f}; "
          f"validation PR AUC {base:.3f}. Explanations: {EXPLANATION_METHOD}.\n")
    print(f"(a) Permutation importance on validation ({PERMUTATION_REPEATS} repeats), PR AUC drop:")
    print(importance.round(3).to_string(index=False))
    print("\n(b) Ablation (refit on train, seeds 1-5), mean validation PR AUC with bootstrap 95% CI:")
    print(ablation_table.round(3).to_string(index=False))
    print(f"\n(c, d) Flagged validation agents: {timing['flagged']} of {timing['agents']}:")
    print(output[output["flag"]][["agent_id", "score", "top_features", "reason"]].round(3).to_string(index=False))
    print("\nReference statistics (training median, IQR):", json.dumps(bundle["reference_stats"]))
    print("\n(e) Top feature of validation fraud agents vs the expected feature for their pattern:")
    print(summary.to_string())
    print("\nMismatches and patterns without an expectation:")
    print(sanity[sanity["match"] != 1][["agent_id", "profile", "flag", "top_features", "expected"]].to_string(index=False))
    print(f"\nTiming: {timing}")
    print(f"Run folder {run_dir}")


if __name__ == "__main__":
    main()
