# Changes: v2 to v3 ML pipeline

The v2 results and data are archived unchanged in `ml/results/archive_v2/` and `ml/data/archive_v2/`. The v3 rework is in progress. This file is filled in step by step, and each number in it comes from a real run.

**Scope:** U-CS 56, AI Fraud Detection only. Other SalesMesh modules are out of scope (see DATA_CARD.md, Scope).

## Known issues carried into v3

1. **The generator was changed after reviews that saw labels: four label-aware changes, all before any model was run, plus the integrity fix (change 5).** They are listed in order in DATA_CARD.md:
   - v2: the repeat-customer share was widened;
   - v3 Step 1: customer ids were widened to 8 digits;
   - v3 Step 1B: per-county popular customers and weak rings were added;
   - v3 Step 1C: hard-limit shortcuts were removed, and the overlap audit was added.
   - plus the integrity fix, change 5 (2026-10-13): a validity fix found by review, made after validation results had been seen. See "Data change 5" below. This is the last change.
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

## Step 9 amendment: post hoc change to the tie rule (2026-10-11 03:11, on validation only, before any test result)

**This is a post hoc change.** The original tie rule in `selection_rule.md` treated candidates as tied if they were within 0.02 PR AUC of the top **or** if their bootstrap CI overlapped heavily (75% or more) with the top's. It chose **LOF, 4 features, `n_neighbors` 35** (mean validation PR AUC **0.682**, CI 0.495–0.854, 61st of 64). That result is kept in run `20261011-025652_selection_s42`.

**Why it failed:** validation has 20 fraud agents, so every bootstrap 95% CI of PR AUC is about 0.33 wide. Nearly every candidate overlapped the top CI by at least 75% (a tie set of 60 of 64), so the overlap condition could not discriminate, and the size tie-break decided.

**Amended rule (decided by the author):**
- tied = within 0.02 of the top mean validation PR AUC;
- simplest first = 4 features before 5, then fewer trees, then smaller `max_samples`, then faster scoring.

The CI-overlap condition was dropped. Nothing else changed: the grid, seeds, metric, cost rule and acceptance criteria are the same. The re-run (`20261011-031206_selection_s42`) reproduces the original grid exactly (largest PR AUC difference over all 320 seed rows: 0.0). The original rule is kept in code as `selection.choose_original`, and it is still tested.

**Amended pick: `if_v3_4f`**, an Isolation Forest with 4 features, 100 trees, `max_samples` 64 and `max_features` 1.0.
- Mean validation PR AUC 0.742 (CI 0.567–0.898), against the top candidate's 0.754.
- Three candidates tied up to `max_samples` (`max_features` 0.6, 0.8 and 1.0). Scoring speed decided between them: 0.065 ms per agent against 0.077 and 0.086. That last tie-break rests on timing differences of a few hundredths of a millisecond.

**Operating point** (seed 42, validation; cutoff 0.536, saved in `operating_point.json`):

| Rule | Flagged (alert rate) | Precision | Recall | F1 |
|---|---|---|---|---|
| Min cost 5:1 (chosen) | 13 (8.7%) | 0.923 | 0.60 | 0.727 |
| Min cost 2:1 | 13 (8.7%) | 0.923 | 0.60 | 0.727 |
| Max F1 | 13 (8.7%) | 0.923 | 0.60 | 0.727 |
| Min cost 10:1 | 66 (44.0%) | 0.288 | 0.95 | 0.442 |
| 15% alert budget | 23 (15.3%) | 0.565 | 0.65 | 0.605 |

**Recall by pattern at 5:1 (validation):**

| Pattern | Recall |
|---|---|
| ring | 1.00 |
| weak_ring | 0.25 |
| sequential | 1.00 |
| duplicate | 0.67 |
| weak | 0.00 |

**Train vs validation:** ROC AUC 0.933 against 0.904 (gap 0.029); PR AUC 0.805 against 0.751.

**Acceptance checks Q1–Q6 on validation** (the final check is Step 11, on test): **all PASS**.

| Check | Value | Result |
|---|---|---|
| Q1: mean PR AUC above the best single feature (0.541) | 0.742 | PASS |
| Q2: seed-42 PR AUC above 0.541 | 0.751 | PASS |
| Q3: PR AUC at least 3 × the fraud rate, CI low above the fraud rate | 0.751 (CI 0.579–0.907) | PASS |
| Q4: train–validation ROC AUC gap at most 0.10 | 0.029 | PASS |
| Q5: recall at least 0.60 | 0.60 | PASS, **exactly at the limit** (12 of 20) |
| Q6: alert rate at most 25% | 8.7% | PASS |

Q5 could fail on test.

## Step 10: explainability (validation only; run `20261011-031637_explain`)

**(a) Permutation importance**, as the PR AUC drop over 20 repeats:

| Feature | Mean drop (std) |
|---|---|
| `collusion_score` | 0.227 (0.048) |
| `customer_similarity` | 0.198 (0.033) |
| `time_of_day_entropy` | 0.052 (0.022) |
| `submission_frequency` | 0.037 (0.030) |

**(b) Ablation:** refit on training with seeds 1–5; mean validation PR AUC, with the bootstrap 95% CI.

| Feature set | PR AUC (CI) | Change vs chosen |
|---|---|---|
| Chosen (4 features) | 0.742 (0.567–0.898) | 0.000 |
| Without `customer_similarity` | 0.623 (0.424–0.808) | −0.118 |
| Without `collusion_score` | 0.636 (0.461–0.811) | −0.106 |
| Without `time_of_day_entropy` | 0.733 (0.554–0.891) | −0.009 |
| Without `submission_frequency` | 0.767 (0.590–0.913) | **+0.026** |
| With `volume_vs_peers` (5 features) | 0.739 (0.572–0.891) | −0.002 |

The answer to "which features are most effective" is `customer_similarity` and `collusion_score`. Dropping `submission_frequency` raises PR AUC by 0.026, but that is within noise, and nothing was changed because of it.

**(c) Explanation method:** the largest scaled deviations, |z| from the training mean using the model's own scaler, with values shown against the training median. SHAP TreeExplainer was the first choice, but `shap` is not installed in this environment (Python 3.14), and no new package was installed without asking. The method shows how unusual an agent is on each feature, not the forest's internal attribution.
- Explanations are computed for flagged agents only. Scoring takes 0.076 ms per agent; scoring with explanations takes 0.098 ms per agent.
- A feature after the first is listed only if |z| ≥ 1. Run `20261011-031554_explain` is kept as superseded: its reasons padded the top 3 with features at about 0 SD.

**(d) Plain-language reasons**, for example: "66% of customers also used by other agents vs typical 0%; submission times concentrated in few hours: entropy 0.58 vs typical 0.79; busiest 24 hours: 25 submissions vs typical 14".

**(e) Sanity check:** the top feature of each validation fraud agent, against the feature expected for its pattern.

| Pattern | Agents | Top feature matches | Note |
|---|---|---|---|
| ring | 6 | 4 | The other 2 have entropy first and collusion second. |
| sequential | 3 | 3 | – |
| duplicate | 3 | **0** | Their top feature is `submission_frequency` or entropy. |
| weak_ring | 4 | **0** | – |
| weak | 4 | – | No expectation set. |

The duplicate result comes from the method. Sequential agents' very high similarity inflates the training standard deviation of `customer_similarity` (0.045), so a duplicate agent's 0.12 is under 1 SD from the mean.

**Validation scoring output:** `validation_scores.csv` has the agreed schema (`agent_id`, `analysis_period_start`, `analysis_period_end`, `score`, `flag`, `threshold`, `model_version`, `top_features`, `reason`). 13 of 150 agents are flagged, one of them a false positive (A12671, legitimate: low volume and spread-out hours). Unflagged rows have an empty `top_features` and the reason "not flagged".

## Step 10 follow-up: explanation method changed (on validation; explanations only)

**Decided by the author, made on validation, before any test result:**
- `top_features` (the top 3 by deviation) is now filled for **every** row, so criterion S3 stays as written. The criteria were not changed.
- The plain-language `reason` stays for flagged agents only; unflagged rows read "not flagged".

**Method change, made on principle:** the method moved from mean and standard deviation (z-scores, using the model scaler) to a **robust deviation**: (value − training median) / max(training IQR, 0.001), computed on training agents only, with no labels.
- **Why:** outliers inflate the standard deviation. The few sequential agents (similarity 0.3–0.5) pushed the training SD of `customer_similarity` to 0.045, which hid duplicate agents' 0.12–0.13.
- **Scope:** this changes explanations only. Scores, flags and the cutoff are identical: the largest score difference across the 150 validation agents is 0.0, and every flag is the same.

**Runs**
- Current: `20261011-032400_explain`.
- Superseded and kept: `20261011-031554_explain` (mean and SD, padded reasons), `20261011-031637_explain` (mean and SD), `20261011-032329_explain` (robust, before a wording fix).
- The wording fix: similarity is shown with 3 decimals, and values below typical read "less alike than usual".

**Sanity check, old vs new** (validation fraud agents whose top feature is the expected one):

| Pattern | Expected top feature | Mean and SD (old) | Median and IQR (new) |
|---|---|---|---|
| ring | `collusion_score` | 4 / 6 | 6 / 6 |
| sequential | `customer_similarity` | 3 / 3 | 3 / 3 |
| duplicate | `customer_similarity` | 0 / 3 | 3 / 3 |
| weak_ring | `collusion_score` | 0 / 4 | 4 / 4 |

**New weakness:** the training IQR of `customer_similarity` is very small (0.0024). Differences of about 0.002 therefore count as unusual and can appear in a reason, for example "similarity 0.104 vs typical 0.102" for the legitimate false positive A12671.

**Scoring time** for the 150 validation agents: 0.114 ms per agent for scores only, and 0.175 ms per agent with `top_features` for every row and reasons for flagged rows.

## SRS system checks S1–S4, re-checked before Step 11 (features only, no labels; run `20261011-032454_system_checks_s101`)

| Check | Result | Measured |
|---|---|---|
| S1: scoring time | PASS | 1000-agent table in 0.048 s, 0.048 ms per agent (targets ≤ 5 s and ≤ 10 ms). Feature computation for 1000 agents takes 5.6 s, reported separately. |
| S2: model replaceable, threshold as config | PASS | A LOF bundle fitted on training features scored through the same `score_agents` call; the threshold came from the bundle. |
| S3: output fields | PASS | All 1000 rows have all 9 fields non-empty. |
| S4: scaling (timing only) | PASS | Scoring takes 0.04 s, 0.05 s, 0.13 s and 0.24 s at 500, 1000, 5000 and 10000 agents. End-to-end at 10000 agents (1.38 million records) takes 56 s (targets ≤ 60 s for scoring and ≤ 600 s end-to-end). |

These checks are formally repeated at Step 11.

## Freeze before Step 11

`ml/results/FREEZE.md` was written by `ml/freeze.py`. It records sha256 hashes, computed in Python without git, of:
- the data files, the features and the split;
- the model scaler, the chosen model, `operating_point.json` and the scoring bundle;
- `acceptance_criteria.md` and `selection_rule.md`.

It states that no test label has been loaded. `ml/tests/test_freeze.py` fails if any of these files changes.

## Data change 5: integrity rules and SalesMesh context (2026-10-13)

**Why.** A review of the frozen v3 data found two problems:
1. Honest agents shared a customer on the same client and category. By the platform rule one customer activates one client service once, so a second activation is a duplicate and should occur only in fraud. On seed 42, 33 (customer, client, category) combinations were used by 2 or more honest agents. A further 243 were used by 2 or more fraud agents (correct), and 10 mixed an honest and a fraud agent.
2. The data had too little SalesMesh context: `agents.csv` held only `agent_id`, `registration_timestamp` and `region`; activations had no quality score or commission; agents had no identity details.

**Nature of the change.** This is a validity fix found by review. It was not tuned to improve any metric, and no model was run to choose it. It was made **after validation results on the old data had been seen** (Steps 7 to 10). **The test set was never read:** the labels guard stayed on; the generator's own checks use the labels it creates, for the data audit only; the report examples used training labels only, through `labels_guard`. **The selection rule (with its amendment) and the acceptance criteria apply unchanged**; `selection_rule.md` and `acceptance_criteria.md` were not edited, and their hashes are in the new `FREEZE.md`.

**What changed in the generator**
- Rules R1 to R6 are enforced while generating, not by filtering (definitions in DATA_CARD.md): no honest pair is used by another agent (R1); honest repeats of a pair are retries after a failed or pending attempt only, with at most one completed activation per pair (R2); popular pool picks skip taken pairs (R3); only the planted fraud patterns break R1 and R2 (R4); activations only in certified categories, after registration and certification (R5); pending only in the last 72 hours, with completed to failed kept at 17:1 (R6).
- `legit_repeat` is now cross sell plus retries. The per-agent share (15% to 50%) is kept; the 4 to 12 regular customers repeated for the same client are gone. Single-client `legit_repeat` agents get one cross-sell client (same category when possible).
- New fields and files from separate RNG streams spawned from seed 42: `account_status` in `agents.csv`; new `agent_identity.csv` and `agent_categories.csv`; `commission_per_activation_kes` in `clients.csv`; `quality_score` and `commission_kes` in `activation_records.csv`. The same distributions apply to honest and fraud agents; no fraud pattern uses them.
- Unchanged: seed, 1000 agents, 130 fraud, pattern shares, counties, clients, categories, window, time zone, customer id format, hour and volume settings, ring settings, and the 4 model features. `agents.csv` (first three columns), `labels.csv` and `rings.csv` are byte-identical to v3a, so the split assignment is unchanged.

**Archived, unchanged (sha256 checked after the move):** v3 data in `ml/data/archive_v3a/` (8 files); all 26 v3a run folders (148 files) in `ml/results/archive_v3a/runs/`; `data_cleaning_report.md`, `FREEZE_v3a.md` (copy), `DATA_CARD_v3a.md` (copy) and the v3a generator, checks and generator tests in `ml/results/archive_v3a/`.

**New generation run:** `20261013-091128_datagen_s42`; datagen freeze note in `FREEZE.md` (written by `freeze.py --data`).

**Behaviour before and after (seed 42)**

| | v3a | Change 5 |
|---|---|---|
| Records | 135,509 | 135,494 |
| Fraud agents by pattern (ring / weak_ring / sequential / duplicate / weak) | 41 / 21 / 21 / 21 / 26 | 41 / 21 / 21 / 21 / 26 |
| Pairs used by 2+ honest agents | 33 | 0 |
| Pairs used by 2+ fraud agents | 243 | 290 |
| Pairs shared by an honest and a fraud agent | 10 | 0 |
| Customers shared by 2+ honest agents (any client) | 464 | 356 |
| Honest `collusion_score` max (non-zero agents) | 0.110 (353) | 0.100 (258) |
| Strong ring `collusion_score` min / median / max | 0.340 / 0.611 / 0.760 | 0.288 / 0.581 / 0.814 |
| Weak ring `collusion_score` min / median / max | 0.032 / 0.074 / 0.149 | 0.030 / 0.090 / 0.164 |
| Repeated customer share (legit / legit_repeat / duplicate / weak / ring) | 0.012 / 0.261 / 0.581 / 0.127 / 0.214 | 0.052 / 0.367 / 0.636 / 0.164 / 0.236 |
| Same-pair repeat share (legit / legit_repeat / duplicate) | 0.001 / 0.223 / 0.578 | 0.041 / 0.044 / 0.634 |
| Records per agent, mean (legit / legit_repeat / legit_busy / ring / sequential / duplicate / weak) | 116.7 / 115.5 / 260.3 / 207.9 / 301.8 / 256.1 / 160.6 | 117.5 / 124.1 / 255.0 / 201.3 / 300.3 / 253.9 / 153.4 |
| Status shares (completed / failed / pending) | weights 0.85 / 0.05 / 0.10, at any time | 0.917 / 0.053 / 0.030 |

Plain legit agents now repeat a customer in 5.2% of records (v3a: 1.2%), because failed attempts are retried. The overlap audit has one new zero-overlap row, the same-pair repeat share of duplicate fraud, which follows from R2; it is a raw descriptor, not a model feature, and is added to the accepted list. The model feature `customer_similarity` still overlaps for duplicate fraud (76% of duplicate agents inside the honest range).

**Independence table** (single-field AUC against `is_fraud`, data audit only): account status 0.496, number of categories 0.515, registration age 0.515, mean quality 0.524, completed share 0.516, all inside 0.35 to 0.65. **Commission total is 0.679, outside the range**, because it follows completed volume and fraud agents submit more; commission per record is 0.550.

**Checks** (in `data_checks.json`): R1, R2, R5 and R6 honest counts are 0; fraud side R1 290 and R2 4,887. Referential integrity, value ranges and identity uniqueness and format all report 0 problems.

**Tests**
- New: `ml/tests/test_integrity_rules.py` (12 tests: one per rule R1 to R6 on small fixtures, the rules on generated data, identity, the model input list of exactly 4 features with no context or identity column, feature vectors without context columns, identity columns not in `labels.csv`, and the independence of the context fields).
- New in `test_data_generation.py`: `test_new_files_and_columns`, `test_context_fields_do_not_change_behaviour`, `test_quality_and_commission_follow_status`.
- Changed for the new schema: `test_agents_file_carries_no_labels` (agents now have `account_status`; also checks the new files carry no label column); `test_only_accepted_signatures_have_zero_overlap_with_legit` (adds the duplicate same-pair repeat share, which R2 makes a definitional signature); `test_freeze.py` now checks the new freeze note (11 hashes instead of 12; the test code is unchanged).
- Code changed for the new schema: `clean_data.EXPECTED_COLUMNS` includes `quality_score` and `commission_kes`; `feature_engineering.MODEL_FEATURES` names the chosen model's 4 inputs; `freeze.py --data` writes the datagen freeze note.
- Skipped until the pipeline is re-run (they need `split.csv` and `feature_vectors.csv`, which were archived): `test_step_7_and_8_run_without_any_test_label`, `test_unlabelled_test_features_carry_no_labels`, `test_real_scaler_matches_training_agents`.
- Backend (not touched): `test_pipeline.py::test_collusion_ring_agents_from_synthetic_data_score_above_every_legit_agent` now fails on its fixed floor of 0.3 (lowest strong ring 0.288); the separation it is about still holds (0.288 against an honest maximum of 0.100). The two known backend failures are unchanged.

**Backend and database changes needed later (backend sprint)**
1. `agents` table: add `account_status` (`active` or `suspended`).
2. New table `agent_identity` (`agent_id` primary key and foreign key, `full_name`, `phone_number`, `national_id_number`), separate from `agents`, readable by admin roles only, never joined into the feature or scoring pipeline.
3. New table `agent_categories` (`agent_id`, `category`, `certification_status`, `certified_at`; key `agent_id` + `category`).
4. `activation_records` table: add `quality_score` (integer 0 to 100) and `commission_kes` (integer).
5. Client reference data: add `commission_per_activation_kes` per client.
6. `backend/src/load_data.py`: load the two new files and the new columns.
7. **Data minimisation:** in the analyst interface, API responses and logs, show phone number and national ID number masked, with only the last 3 digits visible; never write the full values to logs or audit records.
8. The backend feature pipeline must keep ignoring every context and identity column (parity with `MODEL_FEATURES`).
9. Update the backend test with the 0.3 floor, and reload the database with this data (Step 13).

**Process note.** During this change one read-only `git diff --stat` was run by mistake (no output, nothing changed). `run_info.json` records the commit through the read-only `git rev-parse HEAD`, as in every earlier run.

## Pipeline rerun on the change 5 data (2026-10-13, validation only)

**Decisions recorded before the rerun (author):** commission total AUC 0.679 accepted as volume driven (both commission total and commission per record are reported); the extra cross-sell client for single-client `legit_repeat` agents and R6 (pending probability 0.30 in the last 72 hours) confirmed; the backend test with the 0.3 floor left for the backend sprint; `git rev-parse HEAD` kept in `run_info.json`.

**Every setting was applied unchanged:** the selection rule with its amendment, the grid (64 candidates), seeds 1 to 5 and 42, bootstrap (1000, seed 0), tie margin 0.02, alert budget 15%, cost ratio 5:1 (sensitivity 2:1 and 10:1), the `volume_vs_peers` decision rule, the 4 model features, and the acceptance criteria. `selection_rule.md` and `acceptance_criteria.md` were not edited; their hashes in the new `FREEZE.md` equal the v3a hashes. The test labels stayed locked; Step 11 was not run.

**Runs (all kept in `ml/runs/`)**

| Step | Run |
|---|---|
| 2 cleaning | `20261013-092936_clean` |
| 5 split | `20261013-092952_split_s42` |
| 3 EDA (train and validation agents only) | `20261013-092959_eda_s0` |
| 4 features | `20261013-093008_features` |
| 4 feature checks | `20261013-093024_feature_checks` |
| 6 preprocessing | `20261013-093031_preprocess_s0` |
| 7 baselines | `20261013-093033_baselines` |
| 8 default models | `20261013-093036_models_default_s42` |
| 9 selection | `20261013-093050_selection_s42` |
| 9B learning curve | `20261013-093222_learning_curve` |
| 10 explanations and scoring bundle | `20261013-093225_explain` |
| 10 system checks S1 to S4 | `20261013-093332_system_checks_s101` (the first attempt, `20261013-093236_system_checks_s101`, stopped in S4 and holds only `run_info.json`; kept) |

**Steps that behaved differently from before**
1. **EDA ran after the split, without test agents.** The v3a EDA read every label before the split existed. To keep the test labels unread, `eda.py --without-test` loads labels through the new `labels_guard.load_labels` (test rows dropped on read) and describes 850 agents; descriptors still use every agent's unlabelled records. The split itself still reads every agent's pattern to stratify, as designed.
2. **`feature_analysis.py` had a syntax error** (a line break inside a string, from an edit on 2026-10-11 after its last run). The `\n` was restored; no logic changed.
3. **Q1 and Q2 reference value.** The criterion is "above the best single-feature validation PR AUC from Step 7". `selection.py` had the v3a value 0.541 written in; it now reads the value from the Step 7 run (`collusion_score`, 0.574) before the grid runs. Q1 and Q2 against 0.541 are also saved (`acceptance_validation_v3a_reference.csv`); both pass either way.
4. **S4 generated behaviour only.** The change 5 name lists hold 70 x 70 = 4,900 unique full names, so `generate_dataset` refuses 5,000 and 10,000 agents. S4 times features and scoring, which need only agents and activations, so `system_checks.behaviour_dataset` draws those exactly as `generate_dataset` does, without the context fields. The generator was not changed.
5. **A different model was chosen** (below).

**Split** (identical to v3a; `split.csv` byte-identical): train 700 (91 fraud), validation 150 (20), test 150 (19).

**Feature checks** (700 training agents): `volume_vs_peers` KEEP (AUC 0.760 > 0.55; max Spearman 0.803 <= 0.85). Shortcut-risk features (strength >= 0.95): ring on `collusion_score` 1.000 and `time_of_day_entropy` 0.956; weak_ring on `collusion_score` 0.981; sequential on `customer_similarity` 1.000, `volume_vs_peers` 0.974 and `submission_frequency` 0.955; duplicate on `customer_similarity` 0.997, `time_of_day_entropy` 0.977 and `volume_vs_peers` 0.956.

**Baselines on validation (150 agents, 20 fraud)**

| Baseline | PR AUC | ROC AUC | Precision | Recall | F1 |
|---|---|---|---|---|---|
| Random (mean of 20 seeds) | 0.157 | 0.516 | 0.133 | 0.152 | 0.142 |
| Volume rule (`submission_frequency` > training P90, 24.1) | 0.434 | 0.758 | 0.583 | 0.350 | 0.438 |
| Best single feature (`collusion_score`) | 0.574 | 0.757 | 0.478 | 0.550 | 0.512 |
| `duplicate_activation_rule` (pairs > 0) | 0.870 | 0.925 | 1.000 | 0.850 | 0.919 |

**`duplicate_activation_rule`** is new: from the unlabelled activation records only, the count of an agent's (customer, client) pairs that another agent also used, or that the agent repeated after a completed activation; flagged when above 0. On training it scores PR AUC 0.790, ROC AUC 0.879, precision 1.000, recall 0.758. It is a reported baseline, not a selection candidate, and did not change the selection. It catches ring, weak_ring, duplicate and weak agents and no sequential agent. Its precision of 1.000 follows from R1 and R2: the generator never lets an honest agent share a pair or repeat one after completion, so the rule restates the integrity rules rather than learning anything. On real data, honest data-entry errors would break that.

**Default models (validation, 15% budget):** Isolation Forest 4 features PR AUC 0.784, ROC AUC 0.911; 5 features 0.744, 0.897; LOF 4 features 0.489, 0.657; 5 features 0.415, 0.696.

**Selection (amended rule, unchanged).** 64 candidates; the median CI width is 0.306. Best by family: LOF 4 features (`n_neighbors` 50) 0.813; Isolation Forest 4 features (500 trees, `max_samples` 64, `max_features` 1.0) 0.807; LOF 5 features 0.782; Isolation Forest 5 features 0.777. The tie set (within 0.02 of 0.813) holds 11 candidates: the top LOF and 10 Isolation Forests. The original (superseded) rule would pick LOF 4 features `n_neighbors` 35 (0.775), with a tie set of 60.

**Chosen: `lof_v3_4f`, LOF, 4 features, `n_neighbors` 50. This is not the v3a choice (`if_v3_4f`).** It is the top candidate by mean validation PR AUC, and the simplicity order put it first among the ties: `selection.choose` counts a LOF as 0 trees and 0 `max_samples`, so it sorts before every Isolation Forest with the same feature count. That treatment has been in the code since the amendment; no test covers LOF against Isolation Forest in a tie. Had a LOF sorted after the forests, the pick would be Isolation Forest, 100 trees, `max_samples` 64, `max_features` 0.8 (0.804).

**Chosen model on validation** (seed 42; LOF is deterministic, so the seed mean equals it):

| PR AUC (95% CI) | ROC AUC | Cutoff (5:1) | Flagged | Precision | Recall | F1 | Train ROC AUC | Gap |
|---|---|---|---|---|---|---|---|---|
| 0.813 (0.660 to 0.942) | 0.924 | 1.445 | 20 (13.3%) | 0.750 | 0.750 | 0.750 | 0.940 | 0.016 |

Recall by pattern at 5:1: ring 1.00, weak_ring 0.75, sequential 1.00, duplicate 1.00, weak 0.00. Other operating points: 2:1 and max F1 cutoff 1.766 (14 flagged, precision 0.929, recall 0.65); 10:1 cutoff 1.164 (51 flagged, recall 0.90); 15% budget (23 flagged, precision 0.652, recall 0.75). 4 against 5 features: 0.813 against 0.782, CIs overlapping 94% (within noise).

**Acceptance on validation:** Q1 0.813 > 0.574 PASS; Q2 0.813 > 0.574 PASS; Q3 0.813 >= 0.400 and CI low 0.660 > 0.133 PASS; Q4 gap 0.016 PASS; Q5 recall 0.75 PASS; Q6 alert rate 13.3% PASS.

**Learning curve** (validation PR AUC / ROC AUC, 5 stratified repeats): 10% 0.737 / 0.860; 25% 0.773 / 0.914; 50% 0.796 / 0.924; 75% 0.813 / 0.932; 100% 0.813 / 0.924. It rises to about 75% and is flat after.

**Permutation importance** (PR AUC drop, 20 repeats): `collusion_score` 0.324, `customer_similarity` 0.279, `time_of_day_entropy` 0.273, `submission_frequency` 0.040.

**Ablation** (mean validation PR AUC, change against 0.813): without `submission_frequency` 0.754 (-0.059); without `time_of_day_entropy` 0.735 (-0.078); without `customer_similarity` 0.736 (-0.077); without `collusion_score` 0.751 (-0.062); with `volume_vs_peers` 0.782 (-0.031). Every drop is inside the CI width.

**Explanations:** the top feature matches the pattern's expected feature for ring 6 of 6, weak_ring 4 of 4, sequential 3 of 3, duplicate 3 of 3. 20 of 150 validation agents are flagged, 5 of them honest; several honest flags have low volume (busiest 24 hours 7 against a typical 14).

**System checks S1 to S4: all PASS.** S1 0.017 ms per agent (1000 agents in 0.017 s; features 1.4 s). S2 a LOF swap scored through the same entry point with the threshold from the bundle. S3 all 1000 rows have the 9 fields. S4 scoring 0.011 / 0.020 / 0.113 / 0.148 s and end to end 0.7 / 1.8 / 8.8 / 17.4 s at 500 / 1000 / 5000 / 10000 agents.

**Compared with v3a (validation, not the same data):** v3a chose `if_v3_4f` with PR AUC 0.742 (CI 0.567 to 0.898), recall 0.60 at 13 flags; now `lof_v3_4f` with 0.813 (0.660 to 0.942), recall 0.75 at 20 flags. Weak fraud recall is 0 in both.

**Code changed for this rerun:** `baselines.py` (duplicate rule, training and validation table); `labels_guard.load_labels`; `eda.py --without-test`; `selection.py` (Q1/Q2 reference from Step 7); `system_checks.py` (behaviour-only S4); `feature_analysis.py` (syntax fix); `freeze.py` (new run ids, all 5 data files and the generator hashed); `feature_engineering.py` (comments only).

**Tests:** 156 passed, 0 skipped, 0 failed. The 3 tests that skipped now run. Changed: `test_step_7_and_8_run_without_any_test_label` copies `activation_records_clean.csv` too, because the baselines now read it. New: `tests/test_duplicate_rule.py` (by hand, no labels, not a selection candidate, Q1 reference) and `test_load_labels_refuses_test_and_drops_test_rows`. `test_freeze.py` now checks 15 hashes.

**Freeze:** `ml/results/FREEZE.md` is the new model freeze; the datagen note it replaces is kept as `results/FREEZE_data_change5.md`.

## Records, reason text fix, Step 12a, reference table and retrain (2026-10-13, validation only)

**Author decisions:** `lof_v3_4f` accepted as the rule selected it, and the selection rule is not changed; the behaviour-only S4 is kept and the 4,900-name limit documented, with the generator untouched; EDA after the split, without test agents, confirmed.

**Records of the rerun (Part 1)**
1. **Tie order.** The amended rule does not say how to order a LOF against an Isolation Forest in a tie. The code reads a LOF's missing trees and `max_samples` as 0, so it sorts as simplest. The chosen `lof_v3_4f` is also the top mean PR AUC (0.813); the alternative would have been Isolation Forest, 100 trees, `max_samples` 64, `max_features` 0.8 (0.804). Recorded in the new `results/selection_notes.md` (`selection_rule.md` and its hash unchanged) and documented by `test_amended_rule_tie_order_puts_lof_first`.
2. **EDA and test labels.** The v3a EDA read the labels of test agents, for descriptive tables and plots only; no modelling decision used it. It now runs after the split, on training and validation agents only (850), through `labels_guard.load_labels`.
3. **Q1 and Q2 reference.** It was hard coded to the v3a value (0.541). It now reads the Step 7 best single-feature validation PR AUC (0.574 on this data), as the criterion defines it.
4. **`feature_analysis.py`** had a broken string (a line break inside it); the `\n` was restored, with no logic change.
5. **S4** times the generation of agents and activations only, because the fictional name lists allow 70 x 70 = 4,900 unique full names, and `generate_dataset` refuses more agents. The generator is not changed (author decision).
6. **`duplicate_activation_rule`** is a reported baseline only. Its precision of 1.000 depends on the generator making R1 and R2 absolute for honest agents, so it is a reference ceiling, not real-world evidence.

**Reason text fix (Part 2).** A feature now appears in the reason only if its robust deviation |d| >= 1 **and** |value − training median| >= 10% of its training P5 to P95 range; this now applies to the first feature too, which was previously always shown. If no feature passes, the reason reads "no single feature far from typical; flagged on the combination of features". `reference_stats` now also stores P5 and P95.
- New explain run `20261013-094740_explain` (the bundle with the new reference statistics; new `validation_scores.csv`) and system checks `20261013-094743_system_checks_s101` (all PASS). `FREEZE.md` rewritten; `test_freeze.py` passes. Run `20261013-093225_explain` is superseded and kept.
- Scores, flags and `top_features` are identical (largest score difference 0.0).
- **For the 20 flagged validation agents no reason changed:** each shown feature already passed both conditions. Applied to all 150 validation agents as if flagged, 61 reasons change, all to the combination sentence, for example "customer IDs look alike: similarity 0.104 vs typical 0.102" for A13905. Those lines come from the first feature, which used to be shown regardless of size.
- For `customer_similarity`, 10% of the training P5 to P95 range (0.0014) is smaller than one IQR (0.0026), so on this data the IQR condition is the binding one for that feature.
- Tests: `test_reason_display_rule_needs_iqr_and_range_size`, `test_reference_stats_include_p5_and_p95`.

**Step 12a: 5-fold cross-validation (run `20261013-095040_cross_validation_s42`; informational, did not change the selection).** 850 training and validation agents (111 fraud); folds stratified by pattern, seed 42; scaler and model fitted inside each fold on its training part only; no tuning.

| Method | PR AUC folds 1 to 5 | PR AUC mean (SD) | ROC AUC mean (SD) |
|---|---|---|---|
| `lof_v3_4f` (chosen) | 0.841, 0.846, 0.848, 0.802, 0.883 | 0.844 (0.029) | 0.937 (0.015) |
| Isolation Forest 100 / 64 / 0.8 (sensitivity) | 0.825, 0.828, 0.825, 0.868, 0.894 | 0.848 (0.032) | 0.942 (0.018) |
| Random (mean of 20 seeds) | 0.148, 0.164, 0.156, 0.141, 0.144 | 0.151 (0.009) | 0.493 (0.018) |
| Volume rule (fold-train P90) | 0.384, 0.406, 0.378, 0.441, 0.368 | 0.395 (0.029) | 0.743 (0.054) |
| Best single feature (`collusion_score`) | 0.563, 0.536, 0.557, 0.557, 0.540 | 0.550 (0.012) | 0.720 (0.028) |
| `duplicate_activation_rule` | 0.842, 0.881, 0.763, 0.763, 0.774 | 0.805 (0.054) | 0.888 (0.031) |

Pooled out-of-fold recall by pattern (models and the single feature at the 15% budget; the rules at their own flags):

| Method | ring | weak_ring | sequential | duplicate | weak | honest flag rate |
|---|---|---|---|---|---|---|
| `lof_v3_4f` | 1.00 | 0.67 | 1.00 | 0.94 | 0.09 | 0.06 |
| Isolation Forest | 1.00 | 0.67 | 1.00 | 0.94 | 0.09 | 0.06 |
| Volume rule | 0.29 | 0.00 | 0.72 | 0.56 | 0.14 | 0.07 |
| `collusion_score` | 1.00 | 0.94 | 0.00 | 0.06 | 0.05 | 0.10 |
| `duplicate_activation_rule` | 1.00 | 0.61 | 0.00 | 1.00 | 1.00 | 0.00 |

The LOF and the Isolation Forest are indistinguishable (difference 0.004, against an SD of about 0.03).

**Reference table (run `20261013-095059_union_reference`; reported only, not a selection candidate, not used for any decision)**, validation:

| Method | Flagged | Precision | Recall | ring (6) | weak_ring (4) | sequential (3) | duplicate (3) | weak (4) |
|---|---|---|---|---|---|---|---|---|
| `lof_v3_4f` (cutoff 1.445) | 20 | 0.75 | 0.75 | 1.00 | 0.75 | 1.00 | 1.00 | 0.00 |
| `duplicate_activation_rule` | 17 | 1.00 | 0.85 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 |
| Union (either flags) | 25 | 0.80 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

**Step 13a: retrain command.** `retrain.py` refits the scaler and the model on unlabelled agent features, recomputes the explanation reference, and sets the cutoff as the score quantile for the validated alert rate (13.3%, read from the selection run's operating points). It reads no label. Run `20261013-095135_retrain_s42` on the 850 training and validation agents: cutoff 1.476, 113 flagged (13.3%), `model_version` `lof_v3_4f_r20261013-095135`. This run is a demonstration; it does not replace the frozen model. Tests: `tests/test_retrain.py` (3).

**Docs:** new `ml/README.md`; `MODEL_CARD.md` rewritten for `lof_v3_4f` (the v3a draft is kept as `results/archive_v3a/MODEL_CARD_v3a_draft.md`).

**New modules** (`cross_validation.py`, `union_reference.py`, `retrain.py`) are added to the labels-guard source scan in `test_labels_guard.py`.

## Reason wording, reproduce command, model card and pre-declaration (2026-10-13, validation only)

**Author decisions:** keep the display rule as it is; keep `lof_v3_4f`; Step 12 robustness runs inside the Step 11 task; add the reproduce command.

**Reason wording.** The display conditions are unchanged. Each shown feature line now ends with its standing among training agents. Values at or above the training median read "(higher than P percent of training agents)", P being the share of training agents strictly below. Values below it read "(lower than P percent of training agents)", P being the share strictly above. P is rounded down. The reference statistics now store each feature's sorted training values; no label is used.
- New explain run `20261013-100433_explain` and system checks `20261013-100436_system_checks_s101` (all PASS). Runs `20261013-094740_explain` and `20261013-094743_system_checks_s101` are superseded and kept.
- Scores, flags, `top_features` and the threshold are identical (largest score difference 0.0).

| Agent | Before | After |
|---|---|---|
| A23473 | 10% of customers also used by other agents vs typical 0%; customer IDs look alike: similarity 0.111 vs typical 0.102 | 10% of customers also used by other agents vs typical 0% (higher than 95 percent of training agents); customer IDs look alike: similarity 0.111 vs typical 0.102 (higher than 93 percent of training agents) |
| A97580 | busiest 24 hours: 7 submissions vs typical 14 | busiest 24 hours: 7 submissions vs typical 14 (lower than 98 percent of training agents) |
| A86099 | customer IDs look alike: similarity 0.108 vs typical 0.102; busiest 24 hours: 23 submissions vs typical 14 | customer IDs look alike: similarity 0.108 vs typical 0.102 (higher than 91 percent of training agents); busiest 24 hours: 23 submissions vs typical 14 (higher than 86 percent of training agents) |

Test: `test_reason_adds_training_percentile`.

**Reproduce command.** `run_pipeline.py` runs Steps 1 to 10 in order (generate, clean, split, EDA without test agents, features, feature checks, preprocessing, baselines, default models, selection, learning curve, explanations, system checks); each step writes its run folder. Options: `--seed` (generation only), `--skip-generation`, `--dry-run`. It never reads test labels and does not run Step 11 or the freeze. Only its dry run was executed; the full pipeline was not re-run by it. `ml/README.md` now uses it. Tests: `tests/test_run_pipeline.py` (3); `run_pipeline.py` is added to the labels-guard source scan.

**MODEL_CARD.md:** new sections "Scope", "Fit to SRS" (S1 to S4, SRS 3.6, 7.5 and 8.2) and "Class imbalance handling"; Limitations now state that `duplicate_activation_rule` is a reference ceiling, not a real-world estimate, and that weak fraud is missed by the model.

**Pre-declared secondary analysis** (in `results/selection_notes.md`; `selection_rule.md` unchanged): Step 11 reports `lof_v3_4f` alone as the primary result, and the union of its flags with `duplicate_activation_rule` flags as a secondary analysis. The union is not a candidate for selection. `selection_notes.md` is now hashed in `FREEZE.md`, so the declaration cannot change unnoticed.

**Freeze:** `FREEZE.md` rewritten (16 hashes; the new bundle and scaler, and `selection_notes.md` added). `test_freeze.py` passes. ML tests: 171 passed, 0 skipped, 0 failed.

## Step 11: the final test (2026-10-13, test set read once)

**Script:** `final_evaluation.py`, the only file that calls `labels_guard.unlock_test_labels`.
- Before reading any test label it checked all 16 hashes in `FREEZE.md` and the `labels.csv` hash from the generation run; **all 17 matched**.
- It logged the unlock in `results/test_read_attempts.log` (one entry), and after the run wrote `results/test_read_once.json` (timestamp, run id, hashes).
- A second run now stops at once. This was checked once by hand, and is tested by `test_marker_blocks_a_second_run` and `test_real_marker_blocks_a_second_run`.

**Rehearsed first.** Before the real run, every code path was run on a substitute dataset (seed 101, 400 agents, its own split, model and cutoff; `tests/test_final_evaluation.py`), and the figures were inspected. The rehearsal found and fixed:
- a default-argument bug in the read-once check (the real marker check worked; only patching it in tests did not);
- two figure layout problems (overlapping histogram bars; a legend over the value labels).

The rehearsal used no real test label.

**Run `20261013-103859_final_evaluation_s42`:** `lof_v3_4f`, scaler fitted on training only, cutoff 1.445 from validation; no refit and no new cutoff. Bootstrap 95% CIs from 1000 agent-level resamples, seed 42.

| Method (test, 150 agents, 19 fraud) | PR AUC (CI) | ROC AUC (CI) | Precision | Recall | F1 | Flagged |
|---|---|---|---|---|---|---|
| **`lof_v3_4f` (primary)** | **0.845 (0.684 to 0.960)** | **0.953 (0.897 to 0.992)** | 0.600 | 0.789 | 0.682 | 25 |
| Random (20 seeds, 15% budget) | 0.140 (0.104 to 0.221) | 0.474 | 0.104 | 0.126 | 0.114 | 23 |
| Volume rule (training P90, 24.1) | 0.346 (0.201 to 0.593) | 0.749 | 0.385 | 0.263 | 0.312 | 13 |
| `collusion_score` (15% budget) | 0.565 (0.360 to 0.778) | 0.734 | 0.435 | 0.526 | 0.476 | 23 |
| `duplicate_activation_rule` | 0.862 (0.696 to 1.000) | 0.921 | 1.000 | 0.842 | 0.914 | 16 |
| Union (pre-declared secondary) | 0.655 on the 0/1 flag | 0.962 on the 0/1 flag | 0.655 | 1.000 | 0.792 | 29 |

- **Confusion matrix:** TN 121, FP 10, FN 4 (all weak fraud), TP 15.
- **Cost sensitivity** (validation cutoffs): 2:1 cutoff 1.766 flags 17 (precision 0.824, recall 0.737); 10:1 cutoff 1.164 flags 61 (precision 0.295, recall 0.947). Nothing was changed.
- **Recall by pattern:** ring, weak_ring, sequential and duplicate 1.00; weak 0.00.
- **Rings:** 14 of 14 rings have at least half their members flagged; the 14 ring candidates (at least 3 shared customers) map one to one onto true rings, with no honest member.
- **Timing and size:** 0.060 ms per agent; model 0.35 MB.
- **Acceptance:** Q1 to Q6 and S1 to S4 all PASS. Q2 is judged against the best single feature on test (0.670).
- Full results, the error analysis, subgroups, limitations and disclosures are in `results/FINAL_TEST_RESULTS.md`; figures `fig11` to `fig15`, with captions, are in the run folder.

## Step 12: stability across data seeds (run `20261013-104305_stability`)

`stability.py`: seeds 101 to 110, each a separate dataset with its own split (70/15/15 by pattern), the frozen `lof_v3_4f` settings fitted on its training agents, and a cutoff set without labels (validation-score quantile at 13.3%). The seed 42 test set was not used again. No tuning.

| Method | PR AUC mean (SD) [range] | ROC AUC mean (SD) | Precision mean | Recall mean [range] | F1 mean |
|---|---|---|---|---|---|
| `lof_v3_4f` | 0.811 (0.035) [0.746 to 0.860] | 0.933 (0.019) | 0.748 | 0.689 [0.579 to 0.737] | 0.713 |
| `duplicate_activation_rule` | 0.835 (0.039) [0.770 to 0.862] | 0.905 (0.022) | 1.000 | 0.811 [0.737 to 0.842] | 0.895 |
| Union (secondary) | 0.792 (0.097) [0.675 to 0.950] | 0.972 (0.023) | 0.805 | 0.979 [0.895 to 1.000] | 0.882 |

Seed 42's test PR AUC (0.845) and ROC AUC (0.953) are about one SD above these means.

## Closing records (2026-10-13, after Step 12; the test set stays read once)

- **Disclosure wording corrected everywhere:** the generator was changed after labelled summaries had been seen, in four label-aware changes plus the integrity fix (change 5). DATA_CARD.md, MODEL_CARD.md, this file, FINAL_TEST_RESULTS.md and DEVIATIONS_FROM_PROPOSAL.md now all say so.
- **Acceptance table:** `results/ACCEPTANCE_TABLE.md` gives every criterion's exact text from `acceptance_criteria.md`, its threshold, and its validation and test values.
  - **Q6 is defined on the test alert rate, with a 25% limit:** 16.7% passes.
  - The 15% figure is the Step 7 and 8 comparison budget, not a criterion.
  - No criterion was changed.
- **Score figure redrawn, presentation only:** `fig13b_score_distribution_clipped.png` (axis clipped at 5, overflow bin; 2 fraud agents score 8.8 and 9.8).
  - It was built by `redraw_score_figure.py` from the saved `test_scores.csv` and `error_analysis.csv`, with nothing recomputed and `labels.csv` not read.
  - The original figure is kept.
- **Deviations file:** `results/DEVIATIONS_FROM_PROPOSAL.md`, 11 deviations from Chapters 1 to 3 with reasons, plus the disclosures. Items that need the proposal's exact wording are marked for the author.
- **Reproduction check:** the `ml` folder was copied outside the repository and `run_pipeline.py` ran there for real (13 steps, exit 0). Compared with the frozen runs:
  - **identical:** the hashes of the 5 data files, `split.csv` and `feature_vectors.csv` (and of `labels.csv` and `rings.csv`, by hash only);
  - **identical:** the chosen model (`lof_v3_4f`, `n_neighbors` 50, 4 features, seed 42) and the cutoff (1.4447993633890617);
  - **identical (largest numeric difference 0):** every validation table: the selection grid (64 rows), the per-seed grid (320 rows), operating points, acceptance, baselines, default models, learning curve, permutation importance, ablation, and `validation_scores.csv` including reasons;
  - S1 to S4 passed in the copy;
  - `chosen_model.joblib` and `scoring_bundle.joblib` differ byte-wise, as expected; their behaviour is identical (score difference 0.0 on all 1000 agents, same flags, same scaler and explanation reference); `scaler.joblib` is byte-identical.
  - No frozen file was replaced, and the temporary copy was deleted.
- **`run_info.json` audit:** all 18 runs used in the results have one, with seed, commit (read-only `git rev-parse HEAD`), parameters and input hashes.
  - Steps with no randomness record `seed: null`; their seed lists are in the parameters.
  - The stability run lists no input files, because its 10 datasets are generated in memory.
  - The commits recorded are `ac3df5d` (generation), `bdcaca2` (Steps 2 to 9B), `b6d69cc` (explanations to retrain) and `19917bc` (Steps 11 and 12).
- **Tests:** `tests/test_reporting_modules.py` added, so every `ml/*.py` module now has a test.
- **Docs:** root `README.md` rewritten for v3 (it still described the v2 pipeline); `results/PR_DESCRIPTION.md` written.

## Model results

Final. `lof_v3_4f` on test: PR AUC 0.845 (CI 0.684 to 0.960), recall 0.789, precision 0.600; every acceptance criterion passes. The model choice did not change after the test. The v3a choice (`if_v3_4f`) was made on earlier data and never tested. This section will be filled in after Step 11, with old and new numbers side by side, and it will state whether the model choice changed.

## Stress test (issue #26, 2026-10-22)

- **Rule written first:** `stress_test_rule.md`, committed in `1f812e7` before the script existed.
- **Run once:** `runs/20261022-185935_stress_test_s201`, by `stress_test.py`. The script refuses to run a second time (`tests/test_stress_test.py`).
- **What was compared:** the frozen `lof_v3_4f` (frozen cutoff), `duplicate_activation_rule` and their union, on new seed 201 data:
  - control;
  - shifted: ring sizes 7 to 12, sequential gaps 1 to 3, duplicate fraud over 60 days, doubled night share;
  - Evasion A (rule aware);
  - Evasion B (feature aware).
- **Verdicts:**

  | Test | Verdict | Δ (95% CI) |
  |---|---|---|
  | Shifted | No clear difference; the point estimate favours the rule | −0.103 (−0.239 to 0.027) |
  | Evasion A | Model degrades more gracefully | 0.568 (0.460 to 0.674) |
  | Evasion B | No clear difference | −0.005 (−0.128 to 0.111) |

  Write-up: `results/STRESS_TEST_RESULTS.md`.
- **No frozen file changed:**
  - `data_generation.py` was not edited. The shifted settings that are module constants (`RING_SIZE_RANGE`, `LEGIT_PATTERN_SHARES`, `LEGIT_NIGHT_SHARE_RANGE`) were set in memory for one call and restored. The rest is post-processing of the generated records.
  - The frozen hashes were checked before and after the run, and `tests/test_freeze.py` passes.
- **Label-aware data, disclosed:** the stress transforms choose agents by their generated `profile` label. This applies only to the seed 201 stress data, never to the frozen seed 42 data, and no model, cutoff or setting was changed.
- **Known deviation:** two shifted rings have 6 and 5 members instead of 7 to 12. The frozen generator's last-ring remainder rule causes this.

## identifier_similarity on any id format (issue #26, 2026-10-23)

- **The bug:** `feature_engineering.identifier_similarity` (the `customer_similarity` feature) assumed every id was a 4-character prefix plus equal-length digits.
  - Ids of different lengths crashed it (ragged array).
  - A shorter prefix crashed it (`C001`: division by zero).
  - Ids with no prefix were scored wrongly: `12345678` against `12345679` gave 0.75, because the first 4 digits were cut off.
  - `data_checks.py` re-exports the same function; there is no second copy.
- **The new rule:**
  1. Each id loses its leading run of non-digit characters when a digit follows. An id with no digit is kept whole.
  2. Ids are aligned on the right, and a shorter id is padded with a filler that never matches.
  3. The denominator is the longest length times the number of pairs, as before.
- **No frozen value or result changed:**
  - For the v3 data (`CUST` plus 8 digits), the new function returns exactly the old values for all 1000 agents (difference 0.0).
  - `tests/test_identifier_similarity.py` recomputes `customer_similarity`, passes it through the pipeline's CSV write and read, and requires an exact match (difference 0) with the frozen `data/synthetic/feature_vectors.csv`.
  - A freshly computed value can differ from its CSV copy in the last binary digit (up to 9.7e-17 here, for the old code too), hence the round trip.
  - The model, the cutoff, the data, the test set and every hash in `results/FREEZE.md` are unchanged.
  - This is not a generator change, and it is not label-aware.
- **Model card:** it now states that `collusion_score` is computed across all agents' records, in every split, without labels. The "13 of 14" rings that span splits was checked against `runs/20261013-103859_final_evaluation_s42/ring_candidates.csv` joined with the frozen split: 13 of the 14 candidates have members in more than one split.
