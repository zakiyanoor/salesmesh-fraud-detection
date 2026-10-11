"""
Writes ml/results/FREEZE.md: sha256 hashes (computed in Python, no git) of
everything fixed before Step 11. labels.csv is not re-read here (it holds test
labels); its hash recorded at generation time is quoted from run_info.json.
ml/tests/test_freeze.py checks the hashes still match.

Usage: python freeze.py
"""

import json
from datetime import datetime
from pathlib import Path

from run_utils import file_sha256

ML = Path(__file__).resolve().parent
DATA_RUN = "20261011-022249_datagen_s42"
SPLIT_RUN = "20261011-023607_split_s42"
SELECTION_RUN = "20261011-031206_selection_s42"
EXPLAIN_RUN = "20261011-032400_explain"
SYSTEM_CHECKS_RUN = "20261011-032454_system_checks_s101"
FREEZE_PATH = ML / "results" / "FREEZE.md"

FILES = [
    ("Data", "data/synthetic/activation_records.csv"),
    ("Data", "data/synthetic/agents.csv"),
    ("Data", "data/synthetic/clients.csv"),
    ("Features", "data/synthetic/feature_vectors.csv"),
    ("Split", "data/synthetic/split.csv"),
    ("Split", f"runs/{SPLIT_RUN}/split.csv"),
    ("Scaler (inside the model; fitted on 700 training agents, 4 features)", f"runs/{EXPLAIN_RUN}/scaler.joblib"),
    ("Chosen model (selection run)", f"runs/{SELECTION_RUN}/chosen_model.joblib"),
    ("Operating point", f"runs/{SELECTION_RUN}/operating_point.json"),
    ("Scoring bundle (model, scaler, cutoff, explanation reference)", f"runs/{EXPLAIN_RUN}/scoring_bundle.joblib"),
    ("Rules", "results/acceptance_criteria.md"),
    ("Rules", "results/selection_rule.md"),
]


def main():
    data_info = json.loads((ML / "runs" / DATA_RUN / "run_info.json").read_text())
    config = json.loads((ML / "runs" / SELECTION_RUN / "operating_point.json").read_text())
    rows = [(what, path, file_sha256(ML / path)) for what, path in FILES]
    generated = data_info["data_files"]
    for name in ["activation_records.csv", "agents.csv", "clients.csv"]:
        current = file_sha256(ML / "data" / "synthetic" / name)
        if current != generated[name]:
            raise SystemExit(f"{name} no longer matches the frozen generation run")
    table = "\n".join(f"| {what} | `{path}` | `{digest}` |" for what, path, digest in rows)
    text = f"""# Freeze record before Step 11

Written {datetime.now():%Y-%m-%d %H:%M:%S} by `ml/freeze.py`. The sha256 hashes were computed in Python; no git command was used. `ml/tests/test_freeze.py` fails if any file below changes.

**No test label has been loaded.** All label access after the split goes through `ml/labels_guard.py`. It refuses test labels until `final_evaluation.py` (Step 11) unlocks them, and that script does not exist yet. `labels.csv` was not re-read for this record. Its hash, recorded when the data was generated, is `{generated['labels.csv']}` (`runs/{DATA_RUN}/run_info.json`).

## Frozen runs

| What | Run |
|---|---|
| Data (generator frozen after label-aware change #4) | `{DATA_RUN}` |
| Split (70/15/15, seed 42) | `{SPLIT_RUN}` |
| Selection (amended rule) | `{SELECTION_RUN}` |
| Explanations and scoring bundle | `{EXPLAIN_RUN}` |
| System checks S1–S4 | `{SYSTEM_CHECKS_RUN}` |

The data files `activation_records.csv`, `agents.csv` and `clients.csv` match the hashes recorded by the generation run.

## Chosen model

| | |
|---|---|
| model_version | `{config['model_version']}` |
| Model | {config['model']}, settings `{json.dumps(config['params'])}`, contamination `{config['contamination']}` |
| Seed | {config['model_seed']} |
| Features | {", ".join(config['feature_columns'])} |
| Cutoff | score >= {config['threshold']:.6f} ({config['threshold_rule']}, chosen on validation) |

## Hashes

| What | File (relative to `ml/`) | sha256 |
|---|---|---|
{table}
"""
    FREEZE_PATH.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
