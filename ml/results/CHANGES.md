# Changes: v2 to v3 ML pipeline

The v2 results and data are archived unchanged in `ml/results/archive_v2/` and `ml/data/archive_v2/`. The v3 rework is in progress. This file is filled in step by step, and each number in it comes from a real run.

## Known issues carried into v3

1. **The generator was adjusted after reviews that saw labels**, before any model was run.
   - **In v2:** the legitimate repeat-customer share was widened after a feature review showed that `customer_similarity` separated the classes perfectly.
   - **In v3 Step 1:** customer ids were widened from 6 to 8 digits after chance collisions gave legitimate agents a `collusion_score` up to 0.17.
   - **In v3 Step 1B (a realism change):** shared popular customers per county and weak rings were added after a per-pattern review showed that `collusion_score` alone separated rings from all legitimate agents.
   - **Effect:** none of these changes involved a model, a split or a test set, but all were informed by labels.
2. **`collusion_score` uses all agents, including test agents.** No labels are involved, but the partitions are not independent at the feature level.
3. **The earlier deployment choice was made after looking at test results.** v2 had only a train/test split (92 agents with 12 fraud, and 23 agents with 3 fraud). Switching the live detector to Isolation Forest v2 was decided from test-set results: the seed-42 test split, where LOF scored higher (F1 1.000 vs 0.800), and the seeds 1–5 test splits, where Isolation Forest scored higher. v3 adds a validation set so that model choice no longer touches the test set.

## Step 1 and 1B: data generation

| | v2 (archived) | v3 (seed 42) |
|---|---|---|
| Agents | 115 | 600 (`--n-agents`) |
| Fraud agents (rate) | 15 (0.130) | 78 (0.130, `--fraud-rate`) |
| Activation records | 16,341 | 80,773 |
| Rings | 3 (sizes 4/3/2) | 5 strong + 3 weak (sizes 3–6, varied pools and hour windows) |
| Strong ring / weak ring / sequential / duplicate / weak agents | 9 / 0 / 3 / 3 / 0 | 25 / 13 / 12 / 12 / 16 |
| Hard legit agents (night / repeat / busy) | 6 / 6 / 4 (16% of legit) | 42 / 42 / 31 (22% of legit) |
| Legit agents sharing customers | 0 | 188 of 522, through per-county popular-customer pools |
| Regions | 5 cities | 47 counties, weighted by population, independent of label |
| Agent ids | sequential, fraud agents last | random, no label information |
| Registration dates | fraud registered more recently | one distribution for all |
| Labels | columns in `agents.csv` | separate `labels.csv` and `rings.csv` |
| Ring customer pools | consecutive id blocks | random ids with no consecutive pairs |
| Ring agents' mean `sequential_score` | 0.394 | 0.000 |
| Customer id format | `CUST` + 6 digits | `CUST` + 8 digits |

**`collusion_score` by group, before and after Step 1B (seed 42)**

| Group | Before 1B, min / median / max | After 1B, min / median / max |
|---|---|---|
| Legitimate | 0.000 / – / 0.016 (mean 0.001) | 0.000 / 0.000 / 0.074 (188 of 522 non-zero) |
| Strong ring | 0.427 / – / 0.672 | 0.507 / 0.563 / 0.661 |
| Weak ring | (did not exist) | 0.043 / 0.095 / 0.173 (2 of 13 within the legitimate range) |

**Why regions changed from 5 cities to 47 counties.** This is a realism change. The v2 list mixed counties with a town (Eldoret), and five values cannot represent a national agent network. Agents are now spread over all 47 counties by rough 2019 census population, so Nairobi, Kiambu and Nakuru have the most agents. Counties also hold the popular-customer pools, because honest agents who share customers are usually local to each other.

The fraud rate is not tied to county: fraud is independent of province (chi-square p = 0.997), and region is not a model feature. At seed 42, agents per county are minimum 0, median 12 and maximum 43, and 6 counties have fewer than 5 agents.

**Interim script edits**
- `clean_data.py` builds its customer-id format check from `CUSTOMER_ID_DIGITS` in the generator.
- `split.py`, `preprocessing.py` and `run_experiments.py` now read labels from `labels.csv`.
- Steps 5–12 replace those scripts.
- `run_utils.py` writes `run_info.json`, which records Python, OS, CPU, RAM and the git commit (`git rev-parse HEAD`, read-only).

**One existing test was changed:** `backend/tests/test_pipeline.py::generate_ring_dataset` and `test_collusion_ring_agents_from_synthetic_data_score_above_every_legit_agent`.
- In Step 1, `generate_dataset` began returning a `SyntheticDataset` (agents, activations, labels, rings), and `RING_CONFIGS` was removed because rings are now drawn per seed. The helper now reads ring membership from `dataset.labels`.
- In Step 1B, the helper was narrowed to **strong** rings. Weak rings are designed to overlap legitimate agents, so the claim that every ring agent scores above every legitimate agent no longer holds for them, by design.
- The assertions themselves are unchanged, and they still pass for strong rings.

## Model results

Not yet re-run. This section will be filled in after Step 11, with old and new numbers side by side, and it will state whether the model choice changed.
