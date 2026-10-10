# Changes: v2 to v3 ML pipeline

The v2 results and data are archived unchanged in `ml/results/archive_v2/` and `ml/data/archive_v2/`. The v3 rework is in progress. This file is filled in step by step, and each number in it comes from a real run.

## Known issues carried into v3

1. **The generator was adjusted after reviews that saw labels.**
   - **In v2:** the legitimate repeat-customer share was widened after a feature review showed that `customer_similarity` separated the classes perfectly.
   - **In v3 Step 1:** customer ids were widened from 6 to 8 digits. A per-pattern review of the first v3 dataset showed chance collisions giving legitimate agents a `collusion_score` up to 0.17.
   - **Effect:** neither change involved a model, a split or a test set, but both were informed by labels.
2. **`collusion_score` uses all agents, including test agents.** No labels are involved, but the partitions are not independent at the feature level.
3. **The earlier deployment choice was made after looking at test results.** v2 had only a train/test split (92 agents with 12 fraud, and 23 agents with 3 fraud). Switching the live detector to Isolation Forest v2 was decided from test-set results: the seed-42 test split, where LOF scored higher (F1 1.000 vs 0.800), and the seeds 1–5 test splits, where Isolation Forest scored higher. v3 adds a validation set so that model choice no longer touches the test set.

## Step 1: data generation

| | v2 (archived) | v3 (seed 42) |
|---|---|---|
| Agents | 115 | 600 (`--n-agents`) |
| Fraud agents (rate) | 15 (0.130) | 78 (0.130, `--fraud-rate`) |
| Activation records | 16,341 | 83,588 |
| Collusion rings | 3 (sizes 4/3/2) | 10 (sizes 2–5, varied pools and hour windows) |
| Ring / sequential / duplicate / weak agents | 9 / 3 / 3 / 0 | 37 / 13 / 12 / 16 |
| Hard legit agents (night / repeat / busy) | 6 / 6 / 4 (16% of legit) | 42 / 42 / 31 (22% of legit) |
| Agent ids | sequential, fraud agents last | random, no label information |
| Registration dates | fraud registered more recently | one distribution for all |
| Labels | columns in `agents.csv` | separate `labels.csv` and `rings.csv` |
| Ring customer pools | consecutive id blocks | random ids with no consecutive pairs |
| Ring agents' mean `sequential_score` | 0.394 | 0.000 |
| Customer id format | `CUST` + 6 digits | `CUST` + 8 digits |

`clean_data.py` builds its customer-id format check from `CUSTOMER_ID_DIGITS` in the generator. `split.py`, `preprocessing.py` and `run_experiments.py` now read labels from `labels.csv`. These are interim edits; Steps 5–12 replace those scripts.

**One existing test was changed:** `backend/tests/test_pipeline.py::generate_ring_dataset` and the ring test that uses it. `generate_dataset` now returns a `SyntheticDataset` (agents, activations, labels, rings), and `RING_CONFIGS` no longer exists because rings are drawn per seed. The helper now reads ring membership from `dataset.labels`, and the ring count from `dataset.rings`. The assertions themselves are unchanged and still pass.

## Model results

Not yet re-run. This section will be filled in after Step 11, with old and new numbers side by side, and it will state whether the model choice changed.
