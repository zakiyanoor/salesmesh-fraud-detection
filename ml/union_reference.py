"""
Reference table on VALIDATION (informational; REPORTED ONLY, not a selection
candidate, and not used for any decision): recall by fraud pattern for the
chosen model at its saved cutoff, for duplicate_activation_rule (pairs > 0),
and for either of them flagging (union). Test labels are never loaded.

Usage: python union_reference.py [--data-dir DIR] [--explain-run DIR]
Output: ml/runs/<run_id>/ with union_reference.csv and note.md
"""

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from baselines import DUPLICATE_RULE, duplicate_activation_counts
from data_generation import DEFAULT_OUT_DIR
from labels_guard import load_labelled
from metrics import FRAUD_PATTERNS
from scoring import detector_from
from system_checks import latest_explain_run

NOTE = ("Reported only. This table was produced after the model was chosen and frozen. It is not a selection "
        "candidate, and no setting, cutoff or decision was based on it.")


def flag_summary(name, flags, val):
    y, profiles = val["is_fraud"].values, val["profile"].values
    tp = int((flags & y).sum())
    row = {"method": name, "flagged": int(flags.sum()), "true_positives": tp, "false_positives": int((flags & ~y).sum()),
           "precision": tp / flags.sum() if flags.sum() else 0.0, "recall": tp / y.sum()}
    for pattern in FRAUD_PATTERNS:
        mask = profiles == pattern
        row[f"recall_{pattern}"] = flags[mask].mean()
        row[f"agents_{pattern}"] = int(mask.sum())
    return row


def union_table(bundle, val, duplicate_counts):
    model = detector_from(bundle).score(val) >= float(bundle["operating_point"]["threshold"])
    dup = val["agent_id"].map(duplicate_counts).fillna(0).values > 0
    return pd.DataFrame([flag_summary(f"{bundle['model_version']} (cutoff {bundle['operating_point']['threshold']:.3f})", model, val),
                         flag_summary(f"{DUPLICATE_RULE} (pairs > 0)", dup, val),
                         flag_summary("union (either flags)", np.asarray(model | dup), val)])


def main(argv=None):
    from run_utils import start_run

    parser = argparse.ArgumentParser(description="Reference table: model, duplicate rule and their union (validation).")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--explain-run", type=Path, default=None)
    args = parser.parse_args(argv)

    explain_run = args.explain_run or latest_explain_run()
    bundle = joblib.load(explain_run / "scoring_bundle.joblib")
    val = load_labelled(args.data_dir, ["validation"])["validation"]
    duplicate_counts = duplicate_activation_counts(pd.read_csv(args.data_dir / "activation_records_clean.csv"))
    run_dir = start_run("union_reference", None, {"explain_run": explain_run.name, "evaluated_on": "validation",
                                                  "note": NOTE},
                        [args.data_dir / f for f in ["feature_vectors.csv", "split.csv", "labels.csv",
                                                     "activation_records_clean.csv"]] + [explain_run / "scoring_bundle.joblib"])
    table = union_table(bundle, val, duplicate_counts)
    table.to_csv(run_dir / "union_reference.csv", index=False)
    (run_dir / "note.md").write_text(f"# Union reference table (validation)\n\n{NOTE}\n", encoding="utf-8")
    pd.set_option("display.width", 250)
    print(NOTE + "\n")
    print(table.round(3).to_string(index=False))
    print(f"Run folder {run_dir}")


if __name__ == "__main__":
    main()
