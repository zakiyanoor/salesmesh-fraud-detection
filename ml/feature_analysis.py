"""
Feature checks (Step 4), on TRAINING agents only.

Validation and test labels are never read here. The decision rule for the
candidate volume_vs_peers is written to the run folder before any AUC is
computed.

AUC convention: a feature's value is the score, higher = more suspicious.
"Separation" = max(AUC, 1 - AUC), so a feature that is low for fraud also counts.
A pattern is a shortcut risk when one feature alone gives separation >= SHORTCUT_SEPARATION.

Usage: python feature_analysis.py [--data-dir DIR]
Output: ml/runs/<run_id>/ with decision_rule.md (written first), single_feature_auc.csv,
        feature_correlations_train.csv, decision.md
"""

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score

from data_generation import DEFAULT_OUT_DIR
from feature_engineering import ALL_FEATURES, BASE_FEATURES, CANDIDATE_FEATURE
from split import SPLIT_FILE

KEEP_MIN_AUC = 0.55
KEEP_MAX_ABS_CORRELATION = 0.85
SHORTCUT_SEPARATION = 0.95
FRAUD_PATTERNS = ["ring", "weak_ring", "sequential", "duplicate", "weak"]

DECISION_RULE = f"""# Decision rule for {CANDIDATE_FEATURE} (written before any AUC was computed)

Written: {{written}}

Keep `{CANDIDATE_FEATURE}` as a model feature only if both hold, on TRAINING agents only:
1. its single-feature ROC AUC against the fraud label (all fraud patterns vs legitimate, value = score,
   higher = more suspicious) is above {KEEP_MIN_AUC};
2. its absolute Spearman correlation with each of {", ".join(BASE_FEATURES)} is at most {KEEP_MAX_ABS_CORRELATION}.

Otherwise drop it. Validation and test labels are not used. Models with and without it are
still compared on validation at Step 9, and both results are reported.
"""


def training_frame(data_dir):
    features = pd.read_csv(data_dir / "feature_vectors.csv")
    split = pd.read_csv(data_dir / SPLIT_FILE)
    train_ids = split.loc[split["split"] == "train", "agent_id"]
    labels = pd.read_csv(data_dir / "labels.csv", keep_default_na=False)
    labels = labels[labels["agent_id"].isin(train_ids)]
    return features.merge(labels[["agent_id", "is_fraud", "profile"]], on="agent_id", how="inner")


def single_feature_auc(train):
    rows = []
    legit = train[~train["is_fraud"]]
    targets = {"all_fraud": train[train["is_fraud"]]}
    targets.update({p: train[train["profile"] == p] for p in FRAUD_PATTERNS})
    for feature in ALL_FEATURES:
        for name, positives in targets.items():
            y = [0] * len(legit) + [1] * len(positives)
            auc = roc_auc_score(y, pd.concat([legit[feature], positives[feature]]))
            rows.append({"feature": feature, "target": name, "legit_agents": len(legit),
                         "fraud_agents": len(positives), "auc": round(auc, 3),
                         "separation": round(max(auc, 1 - auc), 3),
                         "direction": "higher for fraud" if auc >= 0.5 else "lower for fraud"})
    return pd.DataFrame(rows)


def decide(auc_table, correlations):
    auc = float(auc_table.query("feature == @CANDIDATE_FEATURE and target == 'all_fraud'")["auc"].iloc[0])
    max_corr = float(correlations.loc[CANDIDATE_FEATURE, BASE_FEATURES].abs().max())
    keep = auc > KEEP_MIN_AUC and max_corr <= KEEP_MAX_ABS_CORRELATION
    return keep, auc, max_corr


def main(argv=None):
    from run_utils import start_run

    parser = argparse.ArgumentParser(description="Single-feature AUC and the volume_vs_peers decision (training only).")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    inputs = [args.data_dir / f for f in ["feature_vectors.csv", SPLIT_FILE, "labels.csv"]]
    run_dir = start_run("feature_checks", None, {"keep_min_auc": KEEP_MIN_AUC,
                                                 "keep_max_abs_correlation": KEEP_MAX_ABS_CORRELATION,
                                                 "shortcut_separation": SHORTCUT_SEPARATION,
                                                 "agents_used": "train only"}, inputs)
    (run_dir / "decision_rule.md").write_text(
        DECISION_RULE.format(written=datetime.now().isoformat(timespec="seconds")), encoding="utf-8")

    train = training_frame(args.data_dir)
    auc_table = single_feature_auc(train)
    auc_table.to_csv(run_dir / "single_feature_auc.csv", index=False)
    correlations = train[ALL_FEATURES].corr(method="spearman").round(3)
    correlations.to_csv(run_dir / "feature_correlations_train.csv")

    keep, auc, max_corr = decide(auc_table, correlations)
    shortcuts = auc_table[auc_table["separation"] >= SHORTCUT_SEPARATION]
    wide = auc_table.pivot(index="feature", columns="target", values="auc")[["all_fraud", *FRAUD_PATTERNS]]
    decision = (f"# Decision for {CANDIDATE_FEATURE}\n\nTraining agents: {len(train)} "
                f"({int(train['is_fraud'].sum())} fraud).\n\n"
                f"- Single-feature AUC (all fraud vs legitimate): {auc:.3f} (rule: > {KEEP_MIN_AUC})\n"
                f"- Max |Spearman| with a base feature: {max_corr:.3f} (rule: <= {KEEP_MAX_ABS_CORRELATION})\n\n"
                f"**Decision: {'KEEP' if keep else 'DROP'} {CANDIDATE_FEATURE}.**\n")
    (run_dir / "decision.md").write_text(decision, encoding="utf-8")

    print(f"Training agents only: {len(train)} ({int(train['is_fraud'].sum())} fraud)\n")
    print("Single-feature ROC AUC (value = score, higher = more suspicious):")
    print(wide.to_string())
    print(f"\nShortcut risk (separation >= {SHORTCUT_SEPARATION}):")
    print(shortcuts[["feature", "target", "auc", "separation", "direction"]].to_string(index=False))
    print("\nSpearman correlations (train):")
    print(correlations.to_string())
    print("\n" + decision)
    print(f"Run folder {run_dir}")


if __name__ == "__main__":
    main()
