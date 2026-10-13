# SalesMesh fraud detection: ML pipeline (U-CS 56)

This folder holds the synthetic data generator, the ML pipeline and its results. All data is synthetic. Details: `DATA_CARD.md` (data), `MODEL_CARD.md` (model), `results/CHANGES.md` (history), `PLAN_CHECKLIST.md` (progress).

## Setup

Use the project virtual environment (Python 3.14 on the reference machine). From the repository root:

```
venv\Scripts\activate
cd ml
```

Every command below is run from `ml/`. Each one writes a new folder `runs/<timestamp>_<step>/` with `run_info.json` (settings, input hashes, versions, machine). Nothing is overwritten except the working copies in `data/synthetic/`.

## Reproduce everything (Steps 1 to 10, validation only)

One command runs Steps 1 to 10 in order:

```
python run_pipeline.py
```

| Option | Effect |
|---|---|
| `--seed N` | data generation seed (default 42); the later steps keep their own fixed seeds |
| `--skip-generation` | start at cleaning, using the data already in `data/synthetic/` |
| `--dry-run` | print the steps without running them |

Every seed is fixed, so the numbers match `results/CHANGES.md`. It never reads test labels, and it does not run Step 11. After it, run `python freeze.py` to write `results/FREEZE.md`, and optionally the informational steps 15 and 16 below.

The steps it runs, and the extra commands, are:

| # | Command | What it does |
|---|---|---|
| 1 | `python data_generation.py` | Generates the data (seed 42, 1000 agents) and runs the data checks |
| 2 | `python clean_data.py` | Cleans and flags records; writes `activation_records_clean.csv` |
| 3 | `python split.py` | 70/15/15 agent split, stratified by pattern (seed 42) |
| 4 | `python eda.py --without-test` | Exploratory analysis on training and validation agents |
| 5 | `python feature_engineering.py` | The feature vectors, one row per agent |
| 6 | `python feature_analysis.py` | Single-feature AUC on training agents; the `volume_vs_peers` decision |
| 7 | `python preprocessing.py` | Scaler fitted on training agents only |
| 8 | `python baselines.py` | Step 7 baselines on validation |
| 9 | `python train_models.py` | Step 8 default models on validation |
| 10 | `python selection.py` | Step 9 grid selection and operating point (writes `chosen_model.joblib`) |
| 11 | `python learning_curve.py` | Step 9B learning curve |
| 12 | `python explainability.py` | Step 10 explanations; writes the scoring bundle |
| 13 | `python system_checks.py` | SRS checks S1 to S4 |
| 14 | `python freeze.py` | Writes `results/FREEZE.md` (sha256 of everything fixed before Step 11) |
| 15 | `python cross_validation.py` | Step 12a: 5-fold CV on training and validation agents (informational) |
| 16 | `python union_reference.py` | Reference table: model, duplicate rule and their union (informational) |

Then run the tests:

```
python -m pytest -q tests
```

`tests/test_freeze.py` fails if any frozen file has changed since `freeze.py` ran.

**Test labels are locked.** Every step loads labels through `labels_guard.py`, which refuses test labels until Step 11 (`final_evaluation.py`, not written yet).

## Score agents with the saved model

The scoring bundle (model, scaler, cutoff, explanation reference) is `runs/<explain run>/scoring_bundle.joblib`; `results/FREEZE.md` names the current one.

```python
import pandas as pd
from scoring import load_bundle, score_agents

bundle = load_bundle("runs/20261013-100433_explain/scoring_bundle.joblib")
features = pd.read_csv("data/synthetic/feature_vectors.csv")
scores = score_agents(bundle, features)
```

Each output row has `agent_id`, `analysis_period_start`, `analysis_period_end`, `score`, `flag`, `threshold`, `model_version`, `top_features` and `reason`. A higher score is more anomalous; `flag` is `score >= threshold`. Scores are not probabilities.

To compute features for new records: `feature_engineering.compute_feature_vectors(activations, agents, period_start, period_end)`.

## Retrain on new agents

```
python retrain.py --features path/to/feature_vectors.csv
```

Or, on the agents of named splits:

```
python retrain.py --splits train,validation
```

The command:
1. loads the current scoring bundle (or `--bundle PATH`);
2. refits the scaler and the same model (same settings, seed and 4 features) on the given agents;
3. recomputes the explanation reference (median, IQR, P5, P95) on the same agents;
4. sets the cutoff as the score quantile that flags the validated alert rate (13.3%, from the chosen operating point), or `--alert-rate R`;
5. writes `runs/<timestamp>_retrain_s42/` with a new `scoring_bundle.joblib`, `operating_point.json`, `retrain_report.json` and `scores.csv`.

It reads **no label**. The new bundle has its own `model_version` (for example `lof_v3_4f_r20261013-095135`), and every score row carries it.

## Limits

The data is synthetic. Results show how the method behaves under the generator's assumptions, not on real SalesMesh agents. See `MODEL_CARD.md`, "Limitations".
