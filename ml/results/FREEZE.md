# Freeze record before Step 11

Written 2026-10-13 09:35:23 by `ml/freeze.py`. The sha256 hashes were computed in Python; no git command was used. `ml/tests/test_freeze.py` fails if any file below changes.

**No test label has been loaded.** All label access after the split goes through `ml/labels_guard.py`. It refuses test labels until `final_evaluation.py` (Step 11) unlocks them, and that script does not exist yet. `labels.csv` was not re-read for this record. Its hash, recorded when the data was generated, is `102db7224eaecf0cad54aaf721e7e94a18ba580ea383ec0db1b52e33b491b34c` (`runs/20261013-091128_datagen_s42/run_info.json`).

## Frozen runs

| What | Run |
|---|---|
| Data (final after change #5) | `20261013-091128_datagen_s42` |
| Split (70/15/15, seed 42) | `20261013-092952_split_s42` |
| Selection (amended rule) | `20261013-093050_selection_s42` |
| Explanations and scoring bundle | `20261013-093225_explain` |
| System checks S1–S4 | `20261013-093332_system_checks_s101` |

The data files `activation_records.csv`, `agents.csv`, `agent_identity.csv`, `agent_categories.csv`, `clients.csv` match the hashes recorded by the generation run. The datagen freeze note written before this rerun is kept as `results/FREEZE_data_change5.md`; the v3a model freeze is archived as `results/archive_v3a/FREEZE_v3a.md`.

## Chosen model

| | |
|---|---|
| model_version | `lof_v3_4f` |
| Model | lof, settings `{"n_neighbors": 50}`, contamination `auto` |
| Seed | 42 |
| Features | submission_frequency, time_of_day_entropy, customer_similarity, collusion_score |
| Cutoff | score >= 1.444799 (min expected cost 5:1, chosen on validation) |

## Hashes

| What | File (relative to `ml/`) | sha256 |
|---|---|---|
| Data | `data/synthetic/activation_records.csv` | `efcc0131a21c75718f79802a721aca845f95aba04b1790f38225bf00713bf0aa` |
| Data | `data/synthetic/agents.csv` | `f10364e58a046a9df0cb878aae0a37c1a43e0fbfde05ca176de90d1704a94b0e` |
| Data | `data/synthetic/clients.csv` | `2530e16542870a7c5652bd44c1ba23b2cc93a0997bc2217283e85512980a418a` |
| Data | `data/synthetic/agent_identity.csv` | `1783bb27b493e768aee5db98ec47fa4c00b3759b4753525c6d1eceeb68b4adaa` |
| Data | `data/synthetic/agent_categories.csv` | `59e6f99976b32350efbb1fa45d5d23ad3eeee2388fd191b14b3128b71e876d5c` |
| Generator | `data_generation.py` | `7ad03d6e694ae5f0b54f58cfd3bba5111d1024bb46c87b40a31b2c85908f4521` |
| Features | `data/synthetic/feature_vectors.csv` | `7d7afa399d0f56c2d0961ed731bb39c8426a958914c92df3e8565263ef40714d` |
| Split | `data/synthetic/split.csv` | `d58aef9124317b8228c8db816bc694729132333fbb7a6df73efa5684c17ffc10` |
| Split | `runs/20261013-092952_split_s42/split.csv` | `d58aef9124317b8228c8db816bc694729132333fbb7a6df73efa5684c17ffc10` |
| Scaler (inside the model; fitted on 700 training agents, 4 features) | `runs/20261013-093225_explain/scaler.joblib` | `70cbb1453f270e43a02ad05ad3deca70c350eaeea11f9f9a107fb4e43e52a756` |
| Chosen model (selection run) | `runs/20261013-093050_selection_s42/chosen_model.joblib` | `1e97fffafba4b7905e916c376216195740b9795d0b08968a7b3334c80d4a4a2e` |
| Operating point | `runs/20261013-093050_selection_s42/operating_point.json` | `855ac0ed29baca79534de50f7930be125c57165cb361095f65c18a552f6e6d44` |
| Scoring bundle (model, scaler, cutoff, explanation reference) | `runs/20261013-093225_explain/scoring_bundle.joblib` | `53f485ad6c1c0d304798c428a1b08d442c9f37e37530a219e8f182638faedc48` |
| Rules | `results/acceptance_criteria.md` | `c6b9c035bfcbd1df19547fec1f2cccc4e2a65e71cf55487e0001a9df75d47158` |
| Rules | `results/selection_rule.md` | `e3aa8afd1324388dc5a9a51644b945ddc7aeb3f5fea061bc7a8ba3aff38fe8af` |
