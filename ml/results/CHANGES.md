# Changes: v2 to v3 ML pipeline

The v2 results and data are archived unchanged in `ml/results/archive_v2/` and `ml/data/archive_v2/`. The v3 rework is in progress. This file is filled in step by step, and each number in it comes from a real run.

**Scope:** U-CS 56, AI Fraud Detection only. Other SalesMesh modules are out of scope (see DATA_CARD.md, Scope).

## Known issues carried into v3

1. **The generator was changed after reviews that saw labels**, before any model was run. The changes are listed in order in DATA_CARD.md, "Label-aware changes":
   - v2: the repeat-customer share was widened;
   - v3 Step 1: customer ids were widened to 8 digits;
   - v3 Step 1B, first pass: per-county popular customers and weak rings were added.
2. **`collusion_score` uses all agents, including test agents.** No labels are involved, but the partitions are not independent at the feature level.
3. **The earlier deployment choice was made after looking at test results.** v2 had only a train/test split (92 agents with 12 fraud, and 23 agents with 3 fraud). Switching the live detector to Isolation Forest v2 was decided from test-set results: the seed-42 test split, where LOF scored higher (F1 1.000 vs 0.800), and the seeds 1–5 test splits, where Isolation Forest scored higher. v3 adds a validation set so that model choice no longer touches the test set.

## Steps 1 and 1B: data generation (generator now FROZEN)

| | v2 (archived) | v3 (seed 42, frozen run `20261011-015537_datagen_s42`) |
|---|---|---|
| Agents | 115 | 1000 (`DEFAULT_N_AGENTS`) |
| Fraud agents (rate) | 15 (0.130) | 130 (0.130) |
| Activation records | 16,341 | 138,756 |
| Rings | 3 (sizes 4/3/2) | 9 strong + 5 weak (sizes 2–6) |
| Strong ring / weak ring / sequential / duplicate / weak agents | 9 / 0 / 3 / 3 / 0 | 41 / 21 / 21 / 21 / 26 |
| Hard legit agents (night / repeat / busy) | 6 / 6 / 4 (16% of legit) | 70 / 69 / 52 (22% of legit) |
| Legit agents sharing customers | 0 | 359 of 870, through per-county popular-customer pools |
| Regions | 5 cities | 47 counties, at least 2 agents each (min 5, median 20, max 89) |
| Clients and categories | 8 brand-like client names and 7 categories, drawn at random per record | 20 clients (`Client 01`–`Client 20`) in 12 categories; 1–3 clients per agent; category comes from the client |
| Duplicate pattern | same customer resubmitted | same customer for the same client |
| Agent ids | sequential, fraud agents last | random, no label information |
| Registration dates | fraud registered more recently | one distribution for all |
| Labels | columns in `agents.csv` | separate `labels.csv` and `rings.csv` |
| Ring customer pools | consecutive id blocks | random ids with no consecutive pairs |
| Ring agents' mean `sequential_score` | 0.394 | 0.000 |
| Customer id format | `CUST` + 6 digits | `CUST` + 8 digits |
| Time zone | not stated | Africa/Nairobi, naive local times |

**Fraud independence:** chi-square p values for fraud vs county, former region, primary category and primary client are 0.649, 0.403, 0.547 and 0.702.

**`collusion_score` by group (seed 42)**

| Group | Step 1 (600 agents), min / median / max | Step 1B frozen (1000 agents), min / median / max |
|---|---|---|
| Legitimate | 0.000 / – / 0.016 | 0.000 / 0.000 / 0.074 (359 of 870 non-zero) |
| Strong ring | 0.427 / – / 0.672 | 0.387 / 0.590 / 0.674 |
| Weak ring | (did not exist) | 0.056 / 0.094 / 0.125 (4 of 21 within the legitimate range) |

**Why regions changed from 5 cities to 47 counties.** This is a realism change. The v2 list mixed counties with a town (Eldoret), and five values cannot represent a national agent network. Agents are now spread over all 47 counties by rough 2019 census population, with a floor of 2 per county. Counties also hold the popular-customer pools, because honest agents who share customers are usually local to each other. Fraud is drawn independently of county, and region is not a model feature.

**Why 1000 agents.** Validation and test must each hold at least 15 fraud agents. At 600 agents there would be about 11–12 per split; at 1000 there are about 19–20. More records per agent would add no independent evidence. See DATA_CARD.md, "Why 1000 agents".

**Interim script edits**
- `clean_data.py` builds its customer-id format check from `CUSTOMER_ID_DIGITS`.
- `split.py`, `preprocessing.py` and `run_experiments.py` read labels from `labels.csv`.
- `run_utils.py` writes `run_info.json` with Python, OS, CPU, RAM and the git commit (read-only `git rev-parse HEAD`).
- The new `data_checks.py` computes the generator checks and writes `data_checks.json` into the run folder.

**Backend tests changed (2), with reasons**
1. **`test_pipeline.py::generate_ring_dataset`** and **`test_collusion_ring_agents_from_synthetic_data_score_above_every_legit_agent`**.
   - `generate_dataset` now returns a `SyntheticDataset`, and `RING_CONFIGS` was removed because rings are drawn per seed.
   - The helper now uses strong rings only. Weak rings are designed to overlap legitimate agents.
   - The assertions are unchanged, and they pass.
2. **`test_pipeline.py::test_client_id_and_category_are_not_correlated_with_fraud_status`**.
   - The old test required fraud and legitimate agents to touch nearly all clients (at least 19 of 20). That was only true while every record drew any client at random.
   - Agents now work with 1–3 clients, so 10 fraud agents reach only about 10 clients, even with independent assignment.
   - The test now checks independence directly, with agent-level chi-square tests on primary client and primary category (p > 0.05).

**Backend test now failing, not changed:** `test_api_integration.py::test_agent_detail_context_lists_only_known_clients_and_categories`. It compares the live database, which still holds v2 client names, with the new reference list. This is a real mismatch, and it disappears when the database is reloaded with v3 data. The API tests also hard-code agent `A1104`, which does not exist in v3. Both are to be resolved at Step 13.

## Step 2: cleaning

`clean_data.py` adds:
- format checks for record, agent, customer and client ids;
- `client_id` checked against `clients.csv`, and the category checked against the client's category;
- removal of activations before the agent's registration;
- checks on the `agents.csv` and `clients.csv` tables;
- a near-duplicate check (flagged, kept).

Flags are written to the run folder, never into the cleaned data. Results: 138,756 rows in and 138,756 rows out, with 0 invalid rows. Near duplicates: 65 same-customer records (38 agents) and 529 one-digit-away records (21 agents). In v2, cleaning ran on 16,341 rows and also removed none.

## Step 3: exploratory analysis

The new `eda.py` writes run `20261011-021303_eda_s0`, which holds 4 figures, a raw sample table, distributions by group and findings. Run `20261011-021228_eda_s0` is kept as superseded: its correlation figure clipped its axis labels.

**Two generator shortcuts were found after the freeze.** No legitimate agent ever submits at 05:00–06:59 or 20:00–23:59, while 80 of 130 fraud agents do. Non-busy legitimate agents never exceed 8 records per day, while every weak fraud agent's busiest day is exactly 9. The generator is unchanged pending the author's decision.

## Model results

Not yet re-run. This section will be filled in after Step 11, with old and new numbers side by side, and it will state whether the model choice changed.
