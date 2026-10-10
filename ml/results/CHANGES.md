# Changes: v2 to v3 ML pipeline

The v2 results and data are archived unchanged in `ml/results/archive_v2/` and `ml/data/archive_v2/`. The v3 rework is in progress. This file is filled in step by step, and each number in it comes from a real run.

**Scope:** U-CS 56, AI Fraud Detection only. Other SalesMesh modules are out of scope (see DATA_CARD.md, Scope).

## Known issues carried into v3

1. **The generator was changed four times after reviews that saw labels**, all before any model was run. The changes are listed in order in DATA_CARD.md, "Label-aware changes":
   - v2: the repeat-customer share was widened;
   - v3 Step 1: customer ids were widened to 8 digits;
   - v3 Step 1B: per-county popular customers and weak rings were added;
   - v3 Step 1C: hard-limit shortcuts were removed, and the overlap audit was added. This was the last change.
2. **`collusion_score` uses all agents, including test agents.** No labels are involved, but the partitions are not independent at the feature level.
3. **The earlier deployment choice was made after looking at test results.** v2 had only a train/test split (92 agents with 12 fraud, and 23 agents with 3 fraud). Switching the live detector to Isolation Forest v2 was decided from test-set results: the seed-42 test split, where LOF scored higher (F1 1.000 vs 0.800), and the seeds 1–5 test splits, where Isolation Forest scored higher. v3 adds a validation set so that model choice no longer touches the test set.
4. **Accepted separations remain as limitations.** Strong rings separate on `collusion_score`, and sequential agents on customer similarity and on night share. See DATA_CARD.md, "Accepted separations".

## Steps 1, 1B and 1C: data generation (generator FROZEN for good)

| | v2 (archived) | v3 (seed 42, frozen run `20261011-022249_datagen_s42`) |
|---|---|---|
| Agents | 115 | 1000 (`DEFAULT_N_AGENTS`) |
| Fraud agents (rate) | 15 (0.130) | 130 (0.130) |
| Activation records | 16,341 | 135,509 |
| Rings | 3 (sizes 4/3/2) | 9 strong + 5 weak (sizes 2–6) |
| Strong ring / weak ring / sequential / duplicate / weak agents | 9 / 0 / 3 / 3 / 0 | 41 / 21 / 21 / 21 / 26 |
| Hard legit agents (night / repeat / busy) | 6 / 6 / 4 (16% of legit) | 70 / 69 / 52 (22% of legit) |
| Legit agents sharing customers | 0 | 353 of 870, through per-county popular-customer pools |
| Regions | 5 cities | 47 counties, at least 2 agents each (min 5, median 20, max 89) |
| Clients and categories | 8 brand-like client names and 7 categories, drawn at random per record | 20 clients (`Client 01`–`Client 20`) in 12 categories; 1–3 clients per agent; category comes from the client |
| Duplicate pattern | same customer resubmitted | same customer for the same client |
| Legitimate hours | 07:00–19:59 only (clipped) | every hour; 1–6% off-hours share per agent; no clipping |
| Daily volume | uniform ranges with hard caps | negative binomial around an agent rate (heavy tail, no cap), for every group |
| Agent ids | sequential, fraud agents last | random, no label information |
| Registration dates | fraud registered more recently | one distribution for all |
| Labels | columns in `agents.csv` | separate `labels.csv` and `rings.csv` |
| Ring customer pools | consecutive id blocks | random ids with no consecutive pairs |
| Ring agents' mean `sequential_score` | 0.394 | 0.000 |
| Customer id format | `CUST` + 6 digits | `CUST` + 8 digits |
| Time zone | not stated | Africa/Nairobi, naive local times |

**Fraud independence (frozen run):** chi-square p values for fraud vs county, former region, primary category and primary client are 0.649, 0.403, 0.946 and 0.821.

**`collusion_score` by group (seed 42)**

| Group | Step 1 (600 agents) | Step 1B (1000 agents) | Step 1C frozen (1000 agents) |
|---|---|---|---|
| Legitimate | 0.000 / – / 0.016 | 0.000 / 0.000 / 0.074 | 0.000 / 0.000 / 0.110 (353 non-zero) |
| Strong ring | 0.427 / – / 0.672 | 0.387 / 0.590 / 0.674 | 0.340 / 0.611 / 0.760 |
| Weak ring | (did not exist) | 0.056 / 0.094 / 0.125 (4 of 21 in the legitimate range) | 0.032 / 0.074 / 0.149 (15 of 21 in the legitimate range) |

Values are min / median / max.

### Label-aware change #4 (Step 1C), and why

The Step 3 EDA found two shortcuts caused by hard limits in the generator, not by fraud behaviour:
1. No legitimate agent ever submitted at 05:00–06:59 or 20:00–23:59, while 80 of 130 fraud agents did. A one-line rule gave 80 true positives and 0 false positives.
2. Non-busy legitimate agents never exceeded 8 records per day. Every weak fraud agent's busiest day was exactly 9.

**Fixes** (realism; no model had been run):
- every agent's normal hours come from Normal(13, 3) resampled inside 0–23, plus a per-agent 1–6% share of submissions at any hour;
- every group's daily count is negative binomial (dispersion 3) around an agent rate of `group median × lognormal(0, 0.25)`;
- weak fraud's rate is the legitimate median × 1.15–1.6, random per agent;
- the active-day probability is 0.75–0.95 per agent for everyone (before: 0.85 for legit and 0.90 for fraud);
- the fraud pattern share is 0.55–0.85 per agent (before: fixed at 0.70);
- the pool sizes are random per agent (before: duplicate 25, weak 10, `legit_repeat` 8).

**After the change:** the hour rule flags 120 fraud agents and 846 of 870 legitimate agents. 711 of 818 non-busy legitimate agents have a day above 8. Weak fraud busiest days range from 10 to 25, across 12 distinct values.

**Overlap audit.** 13 raw descriptors were compared between legitimate agents and each fraud pattern (the full table is in DATA_CARD.md). Only three rows show zero overlap, and all three are fraud signatures by definition:
- strong rings on collusion score;
- sequential agents on customer similarity;
- sequential agents on night share.

These are accepted and documented. The test `test_only_accepted_signatures_have_zero_overlap_with_legit` fails if any other zero-overlap row appears.

**Why regions changed from 5 cities to 47 counties.** This is a realism change. The v2 list mixed counties with a town (Eldoret), and five values cannot represent a national agent network. Agents are spread over all 47 counties by rough 2019 census population, with a floor of 2 per county. Counties also hold the popular-customer pools. Fraud is drawn independently of county, and region is not a model feature.

**Why 1000 agents.** Validation and test must each hold at least 15 fraud agents. At 600 agents there would be about 11–12 per split; at 1000 there are about 19–20.

**Superseded generation runs (kept):**
- `20261011-004903_datagen_s42`
- `20261011-005051_datagen_s42`
- `20261011-010944_datagen_s42`
- `20261011-015537_datagen_s42` (Step 1B, before change #4)
- `20261011-022151_datagen_s42` (change #4, first pass)

**Interim script edits**
- `clean_data.py` builds its customer-id format check from `CUSTOMER_ID_DIGITS`.
- `split.py`, `preprocessing.py` and `run_experiments.py` read labels from `labels.csv`.
- `run_utils.py` writes `run_info.json` with Python, OS, CPU, RAM and the git commit (read-only `git rev-parse HEAD`).
- `data_checks.py` computes the generator checks and the overlap audit, and writes them into the generation run folder.

**Backend tests changed (3), with reasons**
1. **`test_pipeline.py::generate_ring_dataset`**, together with the ring test that uses it.
   - `generate_dataset` now returns a `SyntheticDataset`, and `RING_CONFIGS` was removed because rings are drawn per seed.
   - The helper now uses strong rings only, because weak rings are designed to overlap legitimate agents.
2. **`test_pipeline.py::test_client_id_and_category_are_not_correlated_with_fraud_status`**.
   - The old test required fraud agents to touch at least 19 of 20 clients. That cannot hold now that agents work with 1–3 clients.
   - It now runs agent-level chi-square tests on primary client and primary category (p > 0.05).
3. **`test_pipeline.py::test_collusion_ring_agents_from_synthetic_data_score_above_every_legit_agent`** (changed in Step 1C).
   - It asserted that every legitimate agent has `collusion_score` < 0.1. After change #4, honest sharing of county popular customers reaches 0.110, so that fixed ceiling no longer describes the data.
   - The assertion was removed. The test's actual claims still hold and still pass: every strong-ring agent is above 0.3, and the lowest strong-ring score (0.340) is above the highest legitimate score (0.110).

**Backend test failing, not changed:** `test_api_integration.py::test_agent_detail_context_lists_only_known_clients_and_categories`. The live database still holds v2 client names. This stays as it is until the database reload at Step 13. The API tests also hard-code agent `A1104`, which does not exist in v3.

## Step 2: cleaning

`clean_data.py` adds:
- format checks for record, agent, customer and client ids;
- `client_id` checked against `clients.csv`, and the category checked against the client's category;
- removal of activations before the agent's registration;
- checks on the `agents.csv` and `clients.csv` tables;
- a near-duplicate check (flagged, kept).

Flags are written to the run folder, never into the cleaned data.

**Current run `20261011-022427_clean`** (on the frozen data):
- 135,509 rows in and 135,509 rows out, with 0 invalid rows.
- Near duplicates: 93 same-customer records (47 agents) and 541 one-digit-away records (21 agents).
- Volume outliers flagged: 63 agents by the IQR rule.

**Superseded:** run `20261011-020933_clean`, on the pre-change-#4 data (138,756 rows). In v2, cleaning ran on 16,341 rows and also removed none.

## Step 3: exploratory analysis

`eda.py` writes 4 figures, a raw sample table, distributions by group and findings.

**Current run `20261011-022430_eda_s0`** (on the frozen data). Its `findings.md` confirms that both shortcuts are gone.

**Superseded:**
- `20261011-021228_eda_s0`: its correlation figure clipped its axis labels.
- `20261011-021303_eda_s0`: on the pre-change-#4 data; it is where the two shortcuts were found.

## Model results

Not yet re-run. This section will be filled in after Step 11, with old and new numbers side by side, and it will state whether the model choice changed.
