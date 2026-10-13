"""
Writes ml/results/FREEZE.md: sha256 hashes (computed in Python, no git) of
everything fixed before Step 11. labels.csv is not re-read here (it holds test
labels); its hash recorded at generation time is quoted from run_info.json.
ml/tests/test_freeze.py checks the hashes still match.

--data RUN_ID writes the datagen freeze note instead (data files, generator
code, generation run outputs and the rules), for data change #5.

Usage: python freeze.py [--data RUN_ID]
"""

import json
from datetime import datetime
from pathlib import Path

from run_utils import file_sha256

ML = Path(__file__).resolve().parent
# Rerun on the change #5 data (the v3a freeze is archived as results/archive_v3a/FREEZE_v3a.md).
DATA_RUN = "20261013-091128_datagen_s42"
SPLIT_RUN = "20261013-092952_split_s42"
SELECTION_RUN = "20261013-093050_selection_s42"
EXPLAIN_RUN = "20261013-093225_explain"
SYSTEM_CHECKS_RUN = "20261013-093332_system_checks_s101"
FREEZE_PATH = ML / "results" / "FREEZE.md"

FILES = [
    ("Data", "data/synthetic/activation_records.csv"),
    ("Data", "data/synthetic/agents.csv"),
    ("Data", "data/synthetic/clients.csv"),
    ("Data", "data/synthetic/agent_identity.csv"),
    ("Data", "data/synthetic/agent_categories.csv"),
    ("Generator", "data_generation.py"),
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


DATA_FILES = ["activation_records.csv", "agents.csv", "agent_identity.csv", "agent_categories.csv", "clients.csv"]


def data_freeze(data_run):
    info = json.loads((ML / "runs" / data_run / "run_info.json").read_text())
    for name in DATA_FILES:
        if file_sha256(ML / "data" / "synthetic" / name) != info["data_files"][name]:
            raise SystemExit(f"{name} does not match generation run {data_run}")
    files = [("Data", f"data/synthetic/{name}") for name in DATA_FILES] + [
        ("Generator", "data_generation.py"),
        ("Generator checks", "data_checks.py"),
        ("Generation run", f"runs/{data_run}/run_info.json"),
        ("Generation run", f"runs/{data_run}/data_checks.json"),
        ("Rules (unchanged)", "results/acceptance_criteria.md"),
        ("Rules (unchanged)", "results/selection_rule.md"),
    ]
    table = "\n".join(f"| {what} | `{path}` | `{file_sha256(ML / path)}` |" for what, path in files)
    archived = ML / "data" / "archive_v3a" / "labels.csv"
    same = archived.exists() and file_sha256(archived) == info["data_files"]["labels.csv"]
    labels_note = "byte-identical to" if same else "different from"
    text = f"""# Freeze record: data (change #5)

Written {datetime.now():%Y-%m-%d %H:%M:%S} by `ml/freeze.py --data`. The sha256 hashes were computed in Python; no git command was used. `ml/tests/test_freeze.py` fails if any file below changes.

The data is final after change #5 (integrity rules R1 to R6 and context fields; see `CHANGES.md`). Generation run: `runs/{data_run}` (seed {info['seed']}). The model freeze written before Step 11 on the earlier data is archived as `results/archive_v3a/FREEZE_v3a.md`. The split, features, models and selection have not been re-run on this data; a new model freeze follows those re-runs.

**No test label has been loaded.** `labels.csv` and `rings.csv` were not re-read for this record. Their hashes, recorded when the data was generated, are `{info['data_files']['labels.csv']}` and `{info['data_files']['rings.csv']}` (`runs/{data_run}/run_info.json`). `labels.csv` is {labels_note} the archived v3a `labels.csv` (hashes compared, content not read).

## Hashes

| What | File (relative to `ml/`) | sha256 |
|---|---|---|
{table}
"""
    FREEZE_PATH.write_text(text, encoding="utf-8")
    print(text)


def main():
    data_info = json.loads((ML / "runs" / DATA_RUN / "run_info.json").read_text())
    config = json.loads((ML / "runs" / SELECTION_RUN / "operating_point.json").read_text())
    rows = [(what, path, file_sha256(ML / path)) for what, path in FILES]
    generated = data_info["data_files"]
    for name in DATA_FILES:
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
| Data (final after change #5) | `{DATA_RUN}` |
| Split (70/15/15, seed 42) | `{SPLIT_RUN}` |
| Selection (amended rule) | `{SELECTION_RUN}` |
| Explanations and scoring bundle | `{EXPLAIN_RUN}` |
| System checks S1–S4 | `{SYSTEM_CHECKS_RUN}` |

The data files {", ".join(f"`{n}`" for n in DATA_FILES)} match the hashes recorded by the generation run. The datagen freeze note written before this rerun is kept as `results/FREEZE_data_change5.md`; the v3a model freeze is archived as `results/archive_v3a/FREEZE_v3a.md`.

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
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "--data":
        data_freeze(sys.argv[2])
    else:
        main()
