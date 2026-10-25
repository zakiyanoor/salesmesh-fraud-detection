"""
The model's figures for the "How the model works" page (issue #28), read from the frozen results files on
every request. Nothing is retyped here: the cutoff comes from the frozen operating point, and the test
results from the final evaluation run, measured once on the 150 held-out test agents.

Files (relative to ml/):
- runs/<FROZEN_SELECTION_RUN>/operating_point.json: model version, cutoff and how it was chosen;
- runs/<FINAL_EVALUATION_RUN>/summary.json: number of test agents and fraud agents among them;
- runs/<FINAL_EVALUATION_RUN>/test_metrics.csv: precision, recall, PR AUC and ROC AUC with 95% intervals.

Read only; nothing is written.
"""

import csv
import json

from src import ml_bridge
from src.scheduler import interval_minutes

FINAL_EVALUATION_RUN = "20261013-103859_final_evaluation_s42"
FINAL_DIR = ml_bridge.ML_DIR / "runs" / FINAL_EVALUATION_RUN
SUMMARY_PATH = FINAL_DIR / "summary.json"
TEST_METRICS_PATH = FINAL_DIR / "test_metrics.csv"
# test_metrics.csv rows, by the start of their "method" column, and what each is called on the page.
SYSTEMS = (("model", "lof_v3_4f"), ("rule", "duplicate_activation_rule"), ("model_or_rule", "SECONDARY: union"))
METRICS = ("precision", "recall", "pr_auc", "roc_auc")
COUNTS = ("flagged", "tp", "fp", "fn", "tn")


def relative(path):
    return path.relative_to(ml_bridge.ML_DIR.parent).as_posix()


def test_results():
    with open(TEST_METRICS_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    results = {}
    for key, prefix in SYSTEMS:
        row = next(r for r in rows if r["method"].startswith(prefix))
        results[key] = {
            "method": row["method"],
            **{m: float(row[m]) for m in METRICS},
            **{f"{m}_ci": [float(row[f"{m}_ci_low"]), float(row[f"{m}_ci_high"])] for m in METRICS},
            **{c: int(float(row[c])) for c in COUNTS},
        }
    return results


def model_info():
    operating_point = json.loads(ml_bridge.OPERATING_POINT_PATH.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    return {
        "model_version": operating_point["model_version"],
        "features": operating_point["feature_columns"],
        "cutoff": operating_point["threshold"],
        "cutoff_rule": operating_point["threshold_rule"],
        "cutoff_chosen_on": operating_point["chosen_on"],
        "test_agents": summary["test_agents"],
        "test_fraud_agents": summary["test_fraud"],
        "results": test_results(),
        "measured_on": (f"the {summary['test_agents']} held-out test agents, scored once with the frozen model; "
                        "not a promise for other data"),
        "detection_interval_minutes": interval_minutes(),
        "sources": [relative(ml_bridge.OPERATING_POINT_PATH), relative(SUMMARY_PATH), relative(TEST_METRICS_PATH)],
    }
