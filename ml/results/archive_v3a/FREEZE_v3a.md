# Freeze record before Step 11

Written 2026-10-11 03:28:21 by `ml/freeze.py`. The sha256 hashes were computed in Python; no git command was used. `ml/tests/test_freeze.py` fails if any file below changes.

**No test label has been loaded.** All label access after the split goes through `ml/labels_guard.py`. It refuses test labels until `final_evaluation.py` (Step 11) unlocks them, and that script does not exist yet. `labels.csv` was not re-read for this record. Its hash, recorded when the data was generated, is `102db7224eaecf0cad54aaf721e7e94a18ba580ea383ec0db1b52e33b491b34c` (`runs/20261011-022249_datagen_s42/run_info.json`).

## Frozen runs

| What | Run |
|---|---|
| Data (generator frozen after label-aware change #4) | `20261011-022249_datagen_s42` |
| Split (70/15/15, seed 42) | `20261011-023607_split_s42` |
| Selection (amended rule) | `20261011-031206_selection_s42` |
| Explanations and scoring bundle | `20261011-032400_explain` |
| System checks S1–S4 | `20261011-032454_system_checks_s101` |

The data files `activation_records.csv`, `agents.csv` and `clients.csv` match the hashes recorded by the generation run.

## Chosen model

| | |
|---|---|
| model_version | `if_v3_4f` |
| Model | isolation_forest, settings `{"n_estimators": 100, "max_samples": 64, "max_features": 1.0}`, contamination `auto` |
| Seed | 42 |
| Features | submission_frequency, time_of_day_entropy, customer_similarity, collusion_score |
| Cutoff | score >= 0.536394 (min expected cost 5:1, chosen on validation) |

## Hashes

| What | File (relative to `ml/`) | sha256 |
|---|---|---|
| Data | `data/synthetic/activation_records.csv` | `d2ac60f88eedc5899970f1cc6e16a674c7981ff4c42c083fcd868529546dacab` |
| Data | `data/synthetic/agents.csv` | `af76abfe830ee449c7e9ce87bf90694233ce2482da710129170e5274480d40b8` |
| Data | `data/synthetic/clients.csv` | `9b2e5fd7c1b3f881e828e7ec405935b7810b915bea9b9f2a8881bbdea2827e87` |
| Features | `data/synthetic/feature_vectors.csv` | `dc3e96e582526450f9732da667c78d7f9bc63ba00c030b6d8efeb0571a769ac7` |
| Split | `data/synthetic/split.csv` | `d58aef9124317b8228c8db816bc694729132333fbb7a6df73efa5684c17ffc10` |
| Split | `runs/20261011-023607_split_s42/split.csv` | `d58aef9124317b8228c8db816bc694729132333fbb7a6df73efa5684c17ffc10` |
| Scaler (inside the model; fitted on 700 training agents, 4 features) | `runs/20261011-032400_explain/scaler.joblib` | `671ced086504a5cb5cfce1b128d02e601a9e3ae5057f3a09ae3062406d228fff` |
| Chosen model (selection run) | `runs/20261011-031206_selection_s42/chosen_model.joblib` | `5a3da1e0cd635682687ec93853877b8f7f6481d1507e0d4bef90d105a40b2334` |
| Operating point | `runs/20261011-031206_selection_s42/operating_point.json` | `6f3fce535cee5925c5b64220d39027b8a1fc2eea35c16dda77dcbb58c162ab25` |
| Scoring bundle (model, scaler, cutoff, explanation reference) | `runs/20261011-032400_explain/scoring_bundle.joblib` | `be95050906624df2776f7655d515f3ba664395ccb8faab870867a736be308df1` |
| Rules | `results/acceptance_criteria.md` | `c6b9c035bfcbd1df19547fec1f2cccc4e2a65e71cf55487e0001a9df75d47158` |
| Rules | `results/selection_rule.md` | `e3aa8afd1324388dc5a9a51644b945ddc7aeb3f5fea061bc7a8ba3aff38fe8af` |
