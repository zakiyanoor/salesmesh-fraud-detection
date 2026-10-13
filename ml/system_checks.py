"""
SRS system checks S1-S4 from ml/results/acceptance_criteria.md (draft).

Uses features only, never labels:
S1 scoring time per agent and for the whole 1000-agent table (features precomputed),
   with feature computation timed separately;
S2 model replaceable and threshold read from the bundle: a LOF bundle fitted on
   training features is scored through the same entry point;
S3 every output row has all schema fields, non-empty;
S4 timing at 500, 1000, 5000 and 10000 synthetic agents (generation, features,
   scoring); timing only, no accuracy claim. S4 generates the behaviour part only
   (agents and activations, the inputs of features and scoring): the context
   fields are not needed, and the fictional name lists give at most 4900 unique
   full names.

Usage: python system_checks.py [--data-dir DIR] [--explain-run DIR]
Output: ml/runs/<run_id>/ with system_checks.json and scaling.csv
"""

import argparse
import json
import statistics
import time
from pathlib import Path

import joblib
import pandas as pd

import data_generation as dg
from data_generation import DEFAULT_OUT_DIR
from detectors import fit_lof
from feature_engineering import compute_feature_vectors
from labels_guard import load_unlabelled
from run_utils import RUNS_DIR
from scoring import OUTPUT_COLUMNS, score_agents

S1_MAX_MS_PER_AGENT = 10.0
S1_MAX_TABLE_SECONDS = 5.0
S4_SIZES = [500, 1000, 5000, 10000]
S4_SEED = 101
S4_MAX_SCORING_SECONDS_10000 = 60.0
S4_MAX_END_TO_END_SECONDS_10000 = 600.0
TIMING_REPEATS = 5


def median_seconds(fn, repeats=TIMING_REPEATS):
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return statistics.median(times)


def behaviour_dataset(seed, n_agents):
    """Agents and activations exactly as generate_dataset draws them, without the context fields."""
    dg.seed_everything(seed)
    num_fraud = int(round(n_agents * dg.DEFAULT_FRAUD_RATE))
    agents = dg.generate_agents(n_agents - num_fraud, num_fraud)
    profiles, rings = dg.assign_profiles(agents)
    return agents[["agent_id", "registration_timestamp", "region"]], dg.generate_activation_records(agents, profiles, rings)


def schema_problems(output):
    problems = [c for c in OUTPUT_COLUMNS if c not in output.columns]
    for column in OUTPUT_COLUMNS:
        if column in output.columns:
            values = output[column]
            empty = values.isna() | (values.astype(str).str.strip() == "")
            if empty.any():
                problems.append(f"{column}: {int(empty.sum())} empty")
    return problems


def latest_explain_run():
    return sorted(RUNS_DIR.glob("*_explain"))[-1]


def main(argv=None):
    from run_utils import start_run

    parser = argparse.ArgumentParser(description="SRS system checks S1-S4.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--explain-run", type=Path, default=None)
    args = parser.parse_args(argv)

    explain_run = args.explain_run or latest_explain_run()
    bundle = joblib.load(explain_run / "scoring_bundle.joblib")
    features = pd.read_csv(args.data_dir / "feature_vectors.csv")
    clean = pd.read_csv(args.data_dir / "activation_records_clean.csv")
    agents = pd.read_csv(args.data_dir / "agents.csv")
    run_dir = start_run("system_checks", S4_SEED, {"bundle": str(explain_run / "scoring_bundle.joblib"),
                                                   "s4_sizes": S4_SIZES, "timing_repeats": TIMING_REPEATS},
                        [args.data_dir / "feature_vectors.csv", explain_run / "scoring_bundle.joblib"])

    table_seconds = median_seconds(lambda: score_agents(bundle, features))
    feature_seconds = median_seconds(lambda: compute_feature_vectors(clean, agents), repeats=3)
    s1 = {"agents": len(features), "score_table_seconds": table_seconds,
          "score_ms_per_agent": 1000 * table_seconds / len(features), "feature_computation_seconds": feature_seconds,
          "pass": 1000 * table_seconds / len(features) <= S1_MAX_MS_PER_AGENT and table_seconds <= S1_MAX_TABLE_SECONDS}

    train_features = load_unlabelled(args.data_dir, "train")
    lof = fit_lof(train_features, bundle["feature_columns"], n_neighbors=20)
    lof_bundle = {**bundle, **lof.artifact(), "model_version": "lof_swap_check",
                  "operating_point": {**bundle["operating_point"], "threshold": 1.5}}
    swapped = score_agents(lof_bundle, features.head(50))
    s2 = {"swapped_model_version": swapped["model_version"].iloc[0], "rows": len(swapped),
          "threshold_from_bundle": float(swapped["threshold"].iloc[0]),
          "pass": len(swapped) == 50 and swapped["threshold"].eq(1.5).all()}

    output = score_agents(bundle, features)
    problems = schema_problems(output)
    s3 = {"rows": len(output), "columns": OUTPUT_COLUMNS, "problems": problems, "pass": not problems}

    rows = []
    for n in S4_SIZES:
        start = time.perf_counter()
        agents, activations = behaviour_dataset(S4_SEED, n)
        generation = time.perf_counter() - start
        start = time.perf_counter()
        table = compute_feature_vectors(activations, agents)
        feature_time = time.perf_counter() - start
        scoring_time = median_seconds(lambda: score_agents(bundle, table), repeats=3)
        rows.append({"agents": n, "records": len(activations), "generation_seconds": generation,
                     "feature_seconds": feature_time, "scoring_seconds": scoring_time,
                     "scoring_ms_per_agent": 1000 * scoring_time / n, "end_to_end_seconds": feature_time + scoring_time})
    scaling = pd.DataFrame(rows)
    scaling.to_csv(run_dir / "scaling.csv", index=False)
    largest = scaling.iloc[-1]
    s4 = {"pass": bool(largest["scoring_seconds"] <= S4_MAX_SCORING_SECONDS_10000
                       and largest["end_to_end_seconds"] <= S4_MAX_END_TO_END_SECONDS_10000),
          "note": "timing only, no accuracy claim"}

    results = {"S1": s1, "S2": s2, "S3": s3, "S4": s4, "measured_on": "features only; no labels"}
    (run_dir / "system_checks.json").write_text(json.dumps(results, indent=2, default=float), encoding="utf-8")
    for name, result in [("S1", s1), ("S2", s2), ("S3", s3), ("S4", s4)]:
        print(f"{name}: {'PASS' if result['pass'] else 'FAIL'}  {json.dumps({k: v for k, v in result.items() if k != 'pass'}, default=float)}")
    print("\nS4 scaling (timing only):")
    print(scaling.round(3).to_string(index=False))
    print(f"Run folder {run_dir}")


if __name__ == "__main__":
    main()
