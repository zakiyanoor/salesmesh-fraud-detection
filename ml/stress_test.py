"""
Stress test (issue #26), run once under stress_test_rule.md, which was committed
before this script was written. The frozen lof_v3_4f bundle (frozen cutoff),
duplicate_activation_rule and their union are scored on four seed 201 datasets:
control (unchanged generator), shifted (ring sizes 7-12, sequential gaps 1-3,
duplicate fraud spread over 60 days, doubled night share), Evasion A (fraud agents
skip rule-triggering activations) and Evasion B (ring agents draw their hours from
the pooled honest hour distribution). No refit, no tuning; the seed 42 data and
test set are not read. data_generation.py is not edited: shifted settings that are
module constants are set at run time and restored, the rest is post-processing.

Usage: python stress_test.py
Output: ml/runs/<run_id>_stress_test_s201/ (written only after every result exists)
"""

import json
from contextlib import contextmanager
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

import data_generation as dg
from baselines import duplicate_activation_counts
from clean_data import clean_data
from feature_engineering import MODEL_FEATURES, compute_feature_vectors
from metrics import FRAUD_PATTERNS
from run_utils import RUNS_DIR, file_sha256, start_run
from scoring import detector_from

ML_DIR = Path(__file__).resolve().parent
SEED = 201
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 0
BUNDLE = ML_DIR / "runs" / "20261013-100433_explain" / "scoring_bundle.joblib"
FROZEN_HASHES = {  # from results/FREEZE.md
    "data_generation.py": "7ad03d6e694ae5f0b54f58cfd3bba5111d1024bb46c87b40a31b2c85908f4521",
    "runs/20261013-100433_explain/scoring_bundle.joblib":
        "5cdd9d277c68a464b36ea7934d45276207f39ca03c95226cd6441919e695d67f",
}
FROZEN_CUTOFF = 1.444799

SHIFTED_CONSTANTS = {
    "RING_SIZE_RANGE": (7, 12),
    "LEGIT_PATTERN_SHARES": {"legit_night": 0.16, "legit_repeat": 0.08, "legit_busy": 0.06},
    "LEGIT_NIGHT_SHARE_RANGE": (0.20, 0.50),
}
SEQ_MAX_NEIGHBOUR_GAP = 50
SEQ_GAPS = (1, 2, 3)
DUP_MIN_USES = 3
DUP_SPREAD_DAYS = 60
NIGHT_HOURS = range(0, 5)
RING_PATTERNS = ["ring", "weak_ring"]
PAIR = ["customer_id", "client_id"]
SYSTEMS = ["model", "rule", "union"]
TESTS = ["shifted", "evasion_a", "evasion_b"]


def refuse_if_already_run(runs_dir=RUNS_DIR):
    done = sorted(Path(runs_dir).glob(f"*_stress_test_s{SEED}*"))
    if done:
        raise SystemExit(f"stress test already run ({done[0].name}); stress_test_rule.md allows one run")


def check_frozen_hashes():
    for rel, digest in FROZEN_HASHES.items():
        actual = file_sha256(ML_DIR / rel)
        if actual != digest:
            raise SystemExit(f"{rel} does not match results/FREEZE.md ({actual})")


@contextmanager
def shifted_constants(module=dg, settings=SHIFTED_CONSTANTS):
    """Sets generator module constants for the duration; the file is not edited."""
    saved = {name: getattr(module, name) for name in settings}
    try:
        for name, value in settings.items():
            setattr(module, name, value)
        yield
    finally:
        for name, value in saved.items():
            setattr(module, name, value)


def customer_number(ids):
    return ids.str[4:].astype(np.int64)


def sequential_gaps(acts, labels, rng):
    """Renumber each sequential agent's longest near-consecutive run with gaps of 1-3, in time order."""
    acts = acts.copy()
    used = set(acts["customer_id"])
    counts = {"agents": 0, "records_identified": 0, "records_renumbered": 0}
    for agent in labels.loc[labels["profile"] == "sequential", "agent_id"]:
        rows = acts[acts["agent_id"] == agent]
        numbers = customer_number(rows["customer_id"])
        unique = np.sort(numbers.unique())
        runs = np.split(unique, np.where(np.diff(unique) > SEQ_MAX_NEIGHBOUR_GAP)[0] + 1)
        run = max(runs, key=len)
        counts["agents"] += 1
        if len(run) < 2:
            continue
        index = rows[numbers.isin(run)].sort_values("timestamp", kind="mergesort").index
        old = set(acts.loc[index, "customer_id"])
        used -= old
        current, new_ids = int(run[0]), []
        for position in range(len(index)):
            if position:
                current += int(rng.choice(SEQ_GAPS))
            while f"CUST{current}" in used:
                current += 1
            if current > dg.CUSTOMER_ID_MAX:
                raise ValueError("renumbered customer id exceeds 8 digits")
            new_ids.append(f"CUST{current}")
            used.add(new_ids[-1])
        counts["records_identified"] += len(index)
        counts["records_renumbered"] += int((acts.loc[index, "customer_id"].values != np.array(new_ids)).sum())
        acts.loc[index, "customer_id"] = new_ids
    return acts, counts


def duplicate_spread(acts, labels, rng):
    """Move each duplicate agent's repeated-pair records to a random day of a 60-day period."""
    acts = acts.copy()
    window_end = dg.ANALYSIS_END + pd.Timedelta(days=1)
    counts = {"agents": 0, "pairs_used_3_plus": 0, "records_identified": 0, "records_moved": 0,
              "records_outside_window": 0}
    for agent in labels.loc[labels["profile"] == "duplicate", "agent_id"]:
        rows = acts[acts["agent_id"] == agent]
        uses = rows.groupby(PAIR).size()
        pairs = uses[uses >= DUP_MIN_USES].index
        index = rows[pd.MultiIndex.from_frame(rows[PAIR]).isin(pairs)].index
        timestamps = pd.to_datetime(acts.loc[index, "timestamp"])
        days = dg.ANALYSIS_START + pd.to_timedelta(rng.integers(0, DUP_SPREAD_DAYS, len(index)), unit="D")
        moved = days + (timestamps - timestamps.dt.normalize()).values
        counts["agents"] += 1
        counts["pairs_used_3_plus"] += len(pairs)
        counts["records_identified"] += len(index)
        counts["records_moved"] += int((moved.normalize() != timestamps.dt.normalize().values).sum())
        counts["records_outside_window"] += int((moved >= window_end).sum())
        acts.loc[index, "timestamp"] = moved.values
    return acts, counts


def evasion_a(acts, labels):
    """Fraud agents drop every record whose pair another agent already used, or they already completed."""
    fraud = set(labels.loc[labels["is_fraud"], "agent_id"])
    profile = labels.set_index("agent_id")["profile"]
    pair_agents, completed, drop = {}, set(), []
    for row in acts.sort_values("timestamp", kind="mergesort").itertuples():
        pair = (row.customer_id, row.client_id)
        owners = pair_agents.setdefault(pair, set())
        if row.agent_id in fraud and (owners - {row.agent_id} or (row.agent_id, pair) in completed):
            drop.append(row.Index)
            continue
        owners.add(row.agent_id)
        if row.activation_status == "completed":
            completed.add((row.agent_id, pair))
    dropped = acts.loc[drop, "agent_id"].map(profile).value_counts()
    counts = {"fraud_agents_by_pattern": labels[labels["is_fraud"]]["profile"].value_counts().to_dict(),
              "records_dropped": len(drop),
              "records_dropped_by_pattern": {p: int(dropped.get(p, 0)) for p in FRAUD_PATTERNS}}
    return acts.drop(index=drop), counts


def honest_hour_distribution(clean, labels):
    honest = set(labels.loc[~labels["is_fraud"], "agent_id"])
    hours = pd.to_datetime(clean.loc[clean["agent_id"].isin(honest), "timestamp"]).dt.hour
    return hours.value_counts(normalize=True).reindex(range(24), fill_value=0.0)


def evasion_b(acts, labels, hour_share, rng):
    """Ring and weak_ring agents draw each record's hour from the pooled honest distribution."""
    acts = acts.copy()
    agents = set(labels.loc[labels["profile"].isin(RING_PATTERNS), "agent_id"])
    index = acts.index[acts["agent_id"].isin(agents)]
    timestamps = pd.to_datetime(acts.loc[index, "timestamp"])
    hours = rng.choice(24, size=len(index), p=hour_share.values)
    new = (timestamps.dt.normalize().values + pd.to_timedelta(hours, unit="h").values
           + pd.to_timedelta(timestamps.dt.minute.values, unit="m").values
           + pd.to_timedelta(timestamps.dt.second.values, unit="s").values)
    counts = {"agents": len(agents), "records_given_new_hour": len(index),
              "records_hour_changed": int((hours != timestamps.dt.hour.values).sum())}
    acts.loc[index, "timestamp"] = new
    return acts, counts


def score_dataset(data, acts, bundle):
    clean, findings = clean_data(acts, data.agents, data.clients)[:2]
    table = compute_feature_vectors(clean, data.agents).merge(data.labels, on="agent_id")
    threshold = float(bundle["operating_point"]["threshold"])
    table["model_score"] = detector_from(bundle).score(table)
    table["model_flag"] = table["model_score"] >= threshold
    table["rule_pairs"] = table["agent_id"].map(duplicate_activation_counts(clean)).fillna(0).astype(float)
    table["rule_flag"] = table["rule_pairs"] > 0
    table["union_flag"] = table["model_flag"] | table["rule_flag"]
    return table, clean, findings


def system_scores(table, system):
    """(score used for PR AUC and ROC AUC, flag) for a system, as in stability.py."""
    if system == "model":
        return table["model_score"].values, table["model_flag"].values
    if system == "rule":
        return table["rule_pairs"].values, table["rule_flag"].values
    return table["union_flag"].values.astype(float), table["union_flag"].values


def metrics_row(table, system):
    y = table["is_fraud"].values.astype(bool)
    scores, flags = system_scores(table, system)
    tp, fp = int((flags & y).sum()), int((flags & ~y).sum())
    row = {"pr_auc": average_precision_score(y, scores), "roc_auc": roc_auc_score(y, scores),
           "fraud_rate": y.mean(), "flagged": int(flags.sum()),
           "precision": tp / (tp + fp) if tp + fp else 0.0, "recall": tp / y.sum()}
    for pattern in FRAUD_PATTERNS:
        mask = table["profile"].values == pattern
        row[f"recall_{pattern}"] = flags[mask].mean() if mask.any() else float("nan")
        row[f"agents_{pattern}"] = int(mask.sum())
    return row


def bootstrap_indices(sizes, draws=BOOTSTRAP_DRAWS, seed=BOOTSTRAP_SEED):
    """One (draws x n) index array per dataset, drawn in order from a single default_rng(seed)."""
    rng = np.random.default_rng(seed)
    return {name: rng.integers(0, n, size=(draws, n)) for name, n in sizes.items()}


def bootstrap_pr_auc(table, system, indices):
    y = table["is_fraud"].values.astype(bool)
    scores = system_scores(table, system)[0]
    return np.array([average_precision_score(y[i], scores[i]) if y[i].any() else np.nan for i in indices])


def verdict(delta, low, high):
    if low > 0:
        return "model degrades more gracefully than the rule"
    if high < 0:
        return "rule degrades more gracefully than the model"
    return "no clear difference"


def verdict_rows(tables, boots):
    rows = []
    for test in TESTS:
        drop = {s: metrics_row(tables["control"], s)["pr_auc"] - metrics_row(tables[test], s)["pr_auc"]
                for s in ["model", "rule"]}
        boot_drop = {s: boots[("control", s)] - boots[(test, s)] for s in ["model", "rule"]}
        delta_boot = boot_drop["rule"] - boot_drop["model"]
        low, high = np.nanpercentile(delta_boot, [2.5, 97.5])
        delta = drop["rule"] - drop["model"]
        rows.append({"test": test, "drop_model": drop["model"], "drop_rule": drop["rule"], "delta": delta,
                     "delta_ci_low": low, "delta_ci_high": high,
                     "pr_auc_model_after": metrics_row(tables[test], "model")["pr_auc"],
                     "pr_auc_rule_after": metrics_row(tables[test], "rule")["pr_auc"],
                     "pr_auc_union_after": metrics_row(tables[test], "union")["pr_auc"],
                     "drop_union": metrics_row(tables["control"], "union")["pr_auc"]
                     - metrics_row(tables[test], "union")["pr_auc"],
                     "verdict": verdict(delta, low, high)})
    return pd.DataFrame(rows)


def feature_check(control, evaded):
    groups = []
    for name, table, mask in [
        ("ring + weak_ring, control", control, control["profile"].isin(RING_PATTERNS)),
        ("ring + weak_ring, Evasion B", evaded, evaded["profile"].isin(RING_PATTERNS)),
        ("honest agents, control", control, ~control["is_fraud"].astype(bool)),
    ]:
        groups.append({"group": name, "agents": int(mask.sum()), **table.loc[mask, MODEL_FEATURES].mean().to_dict()})
    return pd.DataFrame(groups)


def night_records(acts, labels):
    night_agents = set(labels.loc[labels["profile"] == "legit_night", "agent_id"])
    hours = pd.to_datetime(acts["timestamp"]).dt.hour
    return {"honest_night_profile_agents": len(night_agents),
            "their_records": int(acts["agent_id"].isin(night_agents).sum()),
            "their_night_hour_records": int((acts["agent_id"].isin(night_agents) & hours.isin(NIGHT_HOURS)).sum())}


def main():
    refuse_if_already_run()
    check_frozen_hashes()
    bundle = joblib.load(BUNDLE)
    if abs(float(bundle["operating_point"]["threshold"]) - FROZEN_CUTOFF) > 1e-6:
        raise SystemExit("bundle cutoff is not the frozen 1.444799")

    control = dg.generate_dataset(SEED)
    with shifted_constants():
        shifted = dg.generate_dataset(SEED)
    if dg.RING_SIZE_RANGE != (2, 6) or dg.LEGIT_NIGHT_SHARE_RANGE != (0.10, 0.25):
        raise RuntimeError("generator constants were not restored")

    counts = {"rings_and_night_share": {
        "control": {"rings": dg_rings(control), **night_records(control.activations, control.labels)},
        "shifted": {"rings": dg_rings(shifted), **night_records(shifted.activations, shifted.labels)}}}
    shifted_acts, counts["sequential_gaps"] = sequential_gaps(shifted.activations, shifted.labels,
                                                              np.random.default_rng(SEED))
    shifted_acts, counts["duplicate_spread"] = duplicate_spread(shifted_acts, shifted.labels,
                                                                np.random.default_rng(SEED))

    tables, cleaning = {}, {}
    tables["control"], control_clean, cleaning["control"] = score_dataset(control, control.activations, bundle)
    tables["shifted"], _, cleaning["shifted"] = score_dataset(shifted, shifted_acts, bundle)
    counts["duplicate_spread"]["cleaning_removed_outside_window"] = \
        cleaning["shifted"]["invalid"]["timestamp_outside_window"]
    evaded_a, counts["evasion_a"] = evasion_a(control.activations, control.labels)
    tables["evasion_a"], _, cleaning["evasion_a"] = score_dataset(control, evaded_a, bundle)
    hour_share = honest_hour_distribution(control_clean, control.labels)
    evaded_b, counts["evasion_b"] = evasion_b(control.activations, control.labels, hour_share,
                                              np.random.default_rng(SEED))
    tables["evasion_b"], _, cleaning["evasion_b"] = score_dataset(control, evaded_b, bundle)

    metrics = pd.DataFrame([{"dataset": d, "system": s, **metrics_row(t, s)} for d, t in tables.items()
                            for s in SYSTEMS])
    indices = bootstrap_indices({d: len(t) for d, t in tables.items()})
    boots = {(d, s): bootstrap_pr_auc(t, s, indices[d]) for d, t in tables.items() for s in SYSTEMS}
    metrics["pr_auc_ci_low"] = [np.nanpercentile(boots[(d, s)], 2.5) for d, s in zip(metrics["dataset"], metrics["system"])]
    metrics["pr_auc_ci_high"] = [np.nanpercentile(boots[(d, s)], 97.5) for d, s in zip(metrics["dataset"], metrics["system"])]
    verdicts = verdict_rows(tables, boots)
    check = feature_check(tables["control"], tables["evasion_b"])
    check_frozen_hashes()

    run_dir = start_run("stress_test", SEED, {
        "rule_file": "stress_test_rule.md", "bundle": str(BUNDLE.relative_to(ML_DIR)), "cutoff": FROZEN_CUTOFF,
        "shifted_constants": SHIFTED_CONSTANTS, "sequential_gaps": SEQ_GAPS,
        "sequential_max_neighbour_gap": SEQ_MAX_NEIGHBOUR_GAP, "duplicate_min_uses": DUP_MIN_USES,
        "duplicate_spread_days": DUP_SPREAD_DAYS, "bootstrap_draws": BOOTSTRAP_DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED}, [ML_DIR / "stress_test_rule.md", Path(__file__), ML_DIR / "data_generation.py",
                                            BUNDLE])
    keep = ["agent_id", "profile", "is_fraud", *MODEL_FEATURES, "model_score", "model_flag", "rule_pairs", "rule_flag",
            "union_flag"]
    pd.concat([t[keep].assign(dataset=d) for d, t in tables.items()]).to_csv(run_dir / "per_agent_scores.csv", index=False)
    metrics.to_csv(run_dir / "metrics.csv", index=False)
    verdicts.to_csv(run_dir / "verdicts.csv", index=False)
    check.to_csv(run_dir / "evasion_b_feature_check.csv", index=False)
    hour_share.rename("share").rename_axis("hour").to_csv(run_dir / "honest_hour_distribution.csv")
    (run_dir / "transform_counts.json").write_text(json.dumps({"transforms": counts, "cleaning": cleaning},
                                                              indent=2, default=str))

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(json.dumps(counts, indent=2, default=str))
    print(metrics[["dataset", "system", "pr_auc", "pr_auc_ci_low", "pr_auc_ci_high", "roc_auc", "fraud_rate", "flagged",
                   "precision", "recall"]].round(3).to_string(index=False))
    print(metrics[["dataset", "system", *[f"recall_{p}" for p in FRAUD_PATTERNS]]].round(3).to_string(index=False))
    print(metrics[["dataset", *[f"agents_{p}" for p in FRAUD_PATTERNS]]].drop_duplicates().to_string(index=False))
    print(verdicts.round(3).to_string(index=False))
    print(check.round(3).to_string(index=False))
    print(f"Run folder {run_dir}")


def dg_rings(data):
    return {"count": len(data.rings), "sizes": data.rings["size"].tolist(), "strength": data.rings["strength"].tolist()}


if __name__ == "__main__":
    main()
