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

## Step 5: split (done before Step 4)

| | v2 | v3 (run `20261011-023607_split_s42`) |
|---|---|---|
| Partitions | train/test 80/20 | train/validation/test 70/15/15 |
| Stratified by | `is_fraud` | pattern (legit plus 5 fraud patterns); every split has every pattern |
| Agents (fraud) | 92 (12) / 23 (3) | 700 (91) / 150 (20) / 150 (19) |
| Minimum fraud in an evaluation split | none | 15, enforced (fails otherwise) |

The split is saved as `split.csv` (`agent_id`, `split`) in the run folder and in `data/synthetic/`. The v2 `train_test_split.csv` is no longer used.

13 of 14 rings span more than one split. This is not label leakage, because no labels are used in training, and `collusion_score` uses platform-wide overlap, as in deployment (DATA_CARD.md, "Split").

## Step 4: features (labels used on training agents only)

| | v2 | v3 (run `20261011-023639_features`) |
|---|---|---|
| `submission_frequency` | total submissions in the period | busiest 24-hour sliding window |
| Time-of-day feature | `time_of_day_dist` (entropy) | `time_of_day_entropy` (the same formula, renamed) |
| `customer_similarity` | max(repetition, sequential score) | mean similarity of identifiers over all pairs of submissions (share of matching digit positions) |
| `collusion_score` | share of distinct customers shared with another agent | unchanged |
| `volume_vs_peers` | did not exist | candidate; kept (see below) |
| Period | derived `YYYY-MM` | explicit `period_start` / `period_end` arguments, with both carried on every row |

**Feature checks** (run `20261011-023802_feature_checks`, 700 training agents only):
- The decision rule for `volume_vs_peers` was written to `decision_rule.md` before the AUC table was computed.
- **Result: KEEP.** Training AUC 0.780 (rule: above 0.55); highest Spearman correlation 0.807, with `submission_frequency` (rule: at most 0.85).
- **Near-perfect single features (separation at least 0.95):**
  - ring: `collusion_score`, `time_of_day_entropy`;
  - weak_ring: `collusion_score`;
  - sequential: `customer_similarity`, `volume_vs_peers`, `submission_frequency`;
  - duplicate: `customer_similarity`.

  They are listed as limitations in DATA_CARD.md.

The id-column test now also runs against the real feature matrix (`test_real_feature_matrix_contains_no_id_columns`).

`data_checks.py` now imports `identifier_similarity` and `collusion_scores` from `feature_engineering.py`, so each has one implementation. The old v2 helpers, repetition and sequential score, moved to `data_checks.py`, because they are now generator checks only.

## Step 6: preprocessing

`StandardScaler` is fitted on the 700 training agents only, then applied to validation and test with transform only. It is saved as `scaler.joblib` in run `20261011-023846_preprocess_s0`, together with the feature list.

`scaler_stats.csv` shows that the scaler's means and standard deviations equal the training statistics exactly, and differ from the all-agents statistics. `scaling_sample.md` shows 5 training and 5 validation agents before and after scaling.

**Tests:** `test_scaler_statistics_come_from_training_only`, `test_changing_validation_or_test_does_not_change_the_scaler` and `test_validation_is_transformed_with_training_statistics`.

**Stale until Steps 7–12:** the command-line entry points of `model.py`, `model_lof.py`, `baseline.py`, `evaluate.py` and `run_experiments.py` still expect the v2 two-way split. Their fitting functions still work, and the tests use them, but their `main()` functions will be rewritten in Steps 7–12.

## Test-set guard (added at Step 7)

`ml/labels_guard.py` is the only way to load labels after the split.
- `load_labelled(data_dir, splits)` drops test rows as soon as `labels.csv` is read.
- It raises `TestLabelsLocked` if `"test"` is requested before `unlock_test_labels()`.
- Only the Step 11 script (`final_evaluation.py`) may call `unlock_test_labels()`.

`preprocessing.load_partitions` and `feature_analysis.py` now go through the guard.

The tests in `ml/tests/test_labels_guard.py` cover four things:
- the default lock;
- that only `final_evaluation.py` calls `unlock_test_labels`;
- a scan of the Step 7–10 modules for direct label reads or test requests;
- a runtime test that runs the Step 7 and 8 code with every test label deleted and records that `"test"` was never requested.

**v2 scripts moved, not deleted:** `model.py`, `model_lof.py`, `baseline.py`, `evaluate.py`, `run_experiments.py` and the old `metrics.py` are now in `ml/legacy_v2/`, with a README. They read the test split directly and expect the v2 two-way split. The deployed v2 artifact `ml/models/isolation_forest_v2.joblib` stays where the backend loads it.

## Step 7: baselines (fitted on train, evaluated on validation; run `20261011-024811_baselines`)

**Operating point for the Step 7 and 8 tables, fixed before any result was seen:** flag the top 15% of agents by score (`ALERT_BUDGET = 0.15`; k = ceil(0.15 × 150) = 23). This is not the final threshold. ROC AUC and PR AUC are the main comparison. Validation has 150 agents, 20 of them fraud, so the random PR AUC is 0.133.

| Baseline (validation) | ROC AUC | PR AUC | Precision | Recall | F1 |
|---|---|---|---|---|---|
| Random scores (mean of 20 seeds) | 0.516 | 0.157 | 0.133 | 0.152 | 0.142 |
| Rule: `submission_frequency` > training P90 (24), own cap, 13 flagged | 0.795 | 0.373 | 0.462 | 0.300 | 0.364 |
| `submission_frequency` (+) | 0.795 | 0.373 | 0.391 | 0.450 | 0.419 |
| `time_of_day_entropy` (−) | 0.614 | 0.482 | 0.391 | 0.450 | 0.419 |
| `customer_similarity` (+) | 0.813 | 0.512 | 0.391 | 0.450 | 0.419 |
| `collusion_score` (+) | 0.725 | 0.541 | 0.435 | 0.500 | 0.465 |
| `volume_vs_peers` (+) | 0.801 | 0.396 | 0.435 | 0.500 | 0.465 |

The direction of each single feature (+ or −) was chosen on training AUC. v2 had a 90th-percentile rule too, but on a different split and different data, so its numbers are not comparable.

## Step 8: default models (fitted on train, evaluated on validation; run `20261011-024834_models_default_s42`)

Isolation Forest: `n_estimators=200`, `contamination="auto"`, seed 42. LOF: `novelty=True`, `n_neighbors=20`. Each was run with 4 and with 5 features. There was no tuning.

| Model, features | Validation ROC AUC | Validation PR AUC | P / R / F1 at 15% | Training ROC AUC / PR AUC |
|---|---|---|---|---|
| Isolation Forest, 4 | 0.900 | 0.723 | 0.522 / 0.60 / 0.558 | 0.937 / 0.798 |
| Isolation Forest, 5 | 0.891 | 0.717 | 0.565 / 0.65 / 0.605 | 0.926 / 0.783 |
| LOF, 4 | 0.640 | 0.418 | 0.348 / 0.40 / 0.372 | 0.757 / 0.479 |
| LOF, 5 | 0.702 | 0.474 | 0.348 / 0.40 / 0.372 | 0.746 / 0.502 |

There is no final model choice yet; Step 9 makes it on validation, with a rule written in advance.

**v2 comparison:** v2 used test-set numbers on 23 agents with 3 fraud. These are validation numbers on 150 agents with 20 fraud, on different data, so they are not comparable.

## Step 9: selection on validation (run `20261011-025652_selection_s42`)

**Written before the grid ran (02:55):**
- `ml/results/acceptance_criteria.md` (DRAFT, to be agreed with the supervisor before Step 11). It says it was drafted after seeing default validation results and before any test result.
- `ml/results/selection_rule.md`.

**Grid:** 64 candidates (Isolation Forest 27 × 2 feature sets, LOF 5 × 2), each with 5 model seeds. `contamination` was left at `"auto"` and never set to the fraud rate. It does not change scores or rankings, so the cutoff is taken from validation scores. Every candidate is kept in `grid.csv` and `grid_per_seed.csv`.

| Candidate | Mean validation PR AUC (95% CI) |
|---|---|
| Top: IF, 4 features, 500 trees, `max_samples` 64, `max_features` 0.8 | 0.754 (0.580–0.910) |
| Best 5-feature: IF, 100 trees, `max_samples` 64, `max_features` 1.0 | 0.739 (0.572–0.891) |
| Best LOF: 5 features, `n_neighbors` 50 | 0.717 (0.539–0.875) |
| **Chosen by the rule as written: LOF, 4 features, `n_neighbors` 35** | **0.682 (0.495–0.854)** |

**The rule chose a weak candidate.** Validation has only 20 fraud agents, so every CI is about 0.33 wide, and 60 of 64 candidates count as ties through "heavy CI overlap". The size tie-break then picked the smallest 4-feature model. A margin-only tie set (within 0.02) would choose IF, 4 features, 100 trees, `max_samples` 64, `max_features` 1.0 (0.742). **The rule has not been changed.** The decision is the author's.

**4 vs 5 features:** the rule picks 4. The difference is within noise: 0.754 against 0.739, with CIs overlapping about 97%.

**Operating point** (chosen configuration, seed 42, validation): the minimum-cost cutoff at 5:1 is 1.695. It flags 17 agents (11.3%), with precision 0.765, recall 0.65 and F1 0.703. The 2:1 and max-F1 rules give the same cutoff. The 10:1 rule flags 73 agents (48.7%) with recall 0.95. The 15% budget gives recall 0.65 with precision 0.565.

The cutoff is saved in `operating_point.json` with `model_version` `lof_v3_4f`. This reconciles with the "no config files" rule as follows: settings stay as constants in the scripts, and the threshold is a model artifact value that the scoring code reads.

**Train vs validation (chosen):** ROC AUC 0.906 against 0.877, a gap of 0.029. PR AUC 0.711 against 0.682.

**Recall by pattern at the 5:1 cutoff (validation):**

| Pattern | Recall |
|---|---|
| ring | 1.00 |
| weak_ring | 0.50 |
| sequential | 1.00 |
| duplicate | 0.67 |
| weak | 0.00 |

## Step 9B: learning curve (validation)

Each curve uses 10, 25, 50, 75 and 100% of the training agents, stratified by pattern, with 5 repeats each.

| Training share | LOF k=35, 4 features (rule's choice), PR AUC / ROC AUC | IF 100 trees, `max_samples` 64, 4 features (margin-only alternative), PR AUC / ROC AUC |
|---|---|---|
| 10% (70 agents) | 0.685 / 0.851 | 0.721 / 0.888 |
| 25% | 0.700 / 0.873 | 0.741 / 0.904 |
| 50% | 0.720 / 0.883 | 0.742 / 0.903 |
| 75% | 0.720 / 0.880 | 0.737 / 0.905 |
| 100% (700 agents) | 0.682 / 0.877 | 0.742 / 0.904 |

The runs are `20261011-030156_learning_curve` (rule's choice) and `20261011-030202_learning_curve` (alternative), each with `learning_curve.png`.

**Both curves are flat from about 25–50% of the training agents onwards, so more training data of this kind would not help.** The limit is in the features and the patterns, not the sample size. LOF gets worse with all 700 agents, plausibly because more fraud neighbours make ring clusters look denser (masking).

## Model results

Not yet re-run. This section will be filled in after Step 11, with old and new numbers side by side, and it will state whether the model choice changed.
