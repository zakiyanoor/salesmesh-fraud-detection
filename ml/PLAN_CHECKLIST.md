# ML rework plan checklist

An item is ticked only when it has been done, with one line of evidence (a file, a number or a test name). At Step 13, every unticked item is listed.

- [x] **Scope: U-CS 56 only; other SalesMesh modules out of scope.** Evidence: DATA_CARD.md "Scope" section; the generator has no client management, task limits, payouts or reputation.
- [x] **Test-set guard: test labels can be loaded only by the Step 11 final evaluation script.** Evidence: `ml/labels_guard.py` (`TestLabelsLocked`); 6 tests in `ml/tests/test_labels_guard.py`, including `test_step_7_and_8_run_without_any_test_label`.
- [x] **Single-feature tables show direction-free strength max(AUC, 1 - AUC) next to raw AUC.** Evidence: DATA_CARD.md Step 4 table; `baselines.py` output (`val_auc_raw`, `val_strength`).
- [x] **Rule: record, activation and agent ids are never model inputs.** Evidence: `ml/tests/test_no_id_inputs.py`, 3 tests passing (`test_feature_columns_contain_no_id_column`, `test_feature_matrix_ignores_id_columns`, `test_fitted_models_see_only_feature_columns`). To be re-run against the Step 4 feature matrix.

## Step 0 and Step 1 (done)

- [x] Archive v2 results and data. Evidence: `ml/results/archive_v2/` (6 files) and `ml/data/archive_v2/` (7 files), each checked byte-identical with `cmp` (CHANGES.md, header).
- [x] Data generator rewritten. Evidence: `ml/data_generation.py` (parameters `--n-agents`, `--fraud-rate`, `--seed`); `ml/tests/test_data_generation.py`, 34 tests passing.
- [x] Labels kept in `labels.csv` and `rings.csv`, not in `agents.csv`. Evidence: `agents.csv` columns are `agent_id`, `registration_timestamp` and `region`; test `test_agents_file_carries_no_labels`.
- [x] Run folder with `run_info.json`. Evidence: `ml/runs/20261011-022249_datagen_s42/run_info.json`, holding the seed, parameters, data file hashes, library versions and system information.

## Step 1B (data changes; re-ticked on the frozen Step 1C data)

- [x] 47 counties, with a floor of 2 agents per county. Evidence: `COUNTY_MIN_AGENTS = 2`; agents per county min 5, median 20, max 89, 0 counties under 5; test `test_every_county_has_at_least_the_floor`.
- [x] 1000 agents. Evidence: `DEFAULT_N_AGENTS = 1000`, giving 1000 agents with 130 fraud (0.130); test `test_default_counts_follow_n_agents_and_fraud_rate`.
- [x] Shared popular customers per county. Evidence: 353 of 870 legitimate agents have a non-zero `collusion_score` (max 0.110); test `test_some_legit_agents_share_customers_mostly_within_their_county`.
- [x] Weak rings. Evidence: 5 weak rings with 21 agents, `collusion_score` 0.032 / 0.074 / 0.149 (min / median / max), 15 of 21 inside the legitimate range; test `test_weak_rings_share_less_than_strong_rings`.
- [x] Categories and clients. Evidence: `clients.csv` holds 20 clients across 12 categories; each agent has 1–3 clients (450 / 413 / 137 agents); tests `test_clients_reference_list`, `test_record_category_comes_from_its_client` and `test_agents_work_with_one_to_three_clients_mostly_in_one_or_two_categories`.
- [x] Fraud independent of region, category and client, with chi-square p values. Evidence: county p = 0.649, former region p = 0.403, primary category p = 0.946, primary client p = 0.821 (`data_checks.json`, frozen run); test `test_fraud_is_independent_of_county_region_category_and_client`.
- [x] Requirements traceability table (SRS). Evidence: DATA_CARD.md "Requirements traceability", covering 2.2.4, 7.5, 3.6, 3.1/8.4, 4.3/8.2, 5.1, 5.3 and the section 2 constraints, plus the Chapters 1–3 behaviours.
- [x] Reason for using 1000 agents. Evidence: DATA_CARD.md "Why 1000 agents".
- [x] Every label-aware change listed in order. Evidence: DATA_CARD.md "Label-aware changes, in order" lists 4 changes, marked final.
- [x] Independent units are agents. Evidence: DATA_CARD.md "Independent units" (1000 agents and 130 fraud; the 135,509 records are not independent).
- [x] Time zone, observation window and data dictionary. Evidence: DATA_CARD.md (Africa/Nairobi, 2026-08-01 to 2026-08-30; every column of the 5 files); test `test_timestamps_fall_in_the_observation_window`.
- [x] Duplicate pattern is the same customer for the same client; the same customer for different clients is rare. Evidence: tests `test_duplicate_fraud_resubmits_the_same_customer_for_the_same_client` and `test_same_customer_for_different_clients_is_rare` (1,848 pairs, under 5%).
- [x] The data has customer ids only, with no addresses, stated as a limitation. Evidence: DATA_CARD.md "Limits of this data".

## Step 1C (label-aware change #4, then FROZEN for good)

- [x] Legitimate hours have an off-hours tail, with no clipping. Evidence: `OFF_HOURS_SHARE_RANGE = (0.01, 0.06)`, with resampling instead of a clip; the hour rule now flags 120 fraud agents and 846 of 870 legitimate agents (before: 80 and 0); test `test_legit_agents_also_work_off_hours`.
- [x] Heavy-tailed daily volume with no cap; weak fraud has a random elevated rate. Evidence: negative binomial (dispersion 3) for every group; legitimate busiest day ranges 5–48; weak fraud busiest day ranges 10–25 (12 distinct values); test `test_daily_volume_has_no_class_specific_cap`.
- [x] Overlap audit of every raw descriptor, with every zero-overlap row classified. Evidence: `ml/runs/20261011-022249_datagen_s42/overlap_audit.csv` (13 descriptors × 6 groups) and DATA_CARD.md "Overlap audit"; 3 zero-overlap rows, all accepted signatures; test `test_only_accepted_signatures_have_zero_overlap_with_legit`.
- [x] Constants, clips, caps and exact values that apply to only one class are checked and fixed. Evidence: DATA_CARD.md "Hard limits and exact values checked in the generator" (7 fixed, 2 kept with reasons).
- [x] Step 1 and 1B checks and tests re-run. Evidence: 52 ML tests passing; backend 66 passed and 2 known failures; checks in `data_checks.json`.
- [x] Generator declared FROZEN for good. Evidence: DATA_CARD.md header; the `data_generation.py` docstring says it is frozen after change #4.

## Step 2: cleaning (re-run on the frozen data)

- [x] Cleaning report. Evidence: `ml/results/data_cleaning_report.md` and run `ml/runs/20261011-022427_clean/`: 135,509 rows in and 135,509 out (0 removed); 63 agents flagged as IQR volume outliers and kept; 14 tests in `ml/tests/test_clean_data.py`. Run `20261011-020933_clean` is superseded.
- [x] Near-duplicate check. Evidence: same customer and client within 10 minutes, 93 records from 47 agents; customer id one digit away, 541 records from 21 agents. All are flagged and kept, in `record_flags.csv`. Test `test_near_duplicates_by_hand`.

## Step 3: exploratory analysis (re-run on the frozen data)

- [x] Raw sample table. Evidence: `ml/runs/20261011-022430_eda_s0/raw_sample.md`, with 8 raw activation records, 5 agents and 5 clients (seed 0).
- [x] Distributions by group. Evidence: same run, `fig03_distributions_by_group.png`, `descriptors_by_group.csv`, `fig02_volume_by_hour.png`, `fig01_class_balance.png`, `fig04_correlations.png` and `findings.md`, which includes a shortcut check confirming both are gone. Runs `20261011-021228_eda_s0` and `20261011-021303_eda_s0` are superseded.

## Step 4: features (done after Step 5; label checks on training agents only)

- [x] The four features: `submission_frequency`, `time_of_day_entropy`, `customer_similarity` and `collusion_score`. Evidence: `ml/feature_engineering.py`; `ml/runs/20261011-023639_features/feature_vectors.csv`, 1000 rows.
- [x] Feature functions take `period_start` and `period_end`; output rows include `analysis_period_start` and `analysis_period_end`. Evidence: `compute_feature_vectors(..., period_start, period_end)`; test `test_period_filter_and_period_columns`.
- [x] `submission_frequency` uses a sliding window (busiest 24 hours). Evidence: `SUBMISSION_WINDOW_HOURS = 24`; test `test_submission_frequency_by_hand`.
- [x] `customer_similarity` is the mean similarity of identifiers over pairs. Evidence: `identifier_similarity`; test `test_identifier_similarity_by_hand`.
- [x] Candidate `volume_vs_peers`, with the agreed peer rule and minimum group size 15. Evidence: `PEER_MIN_GROUP = 15`; 578 agents at category + region and 422 at category level; test `test_volume_vs_peers_by_hand`.
- [x] Each feature defined exactly. Evidence: DATA_CARD.md "Feature definitions (Step 4)" gives formula, window and units.
- [x] Single-feature AUC table, overall and per pattern, on training agents only. Evidence: `ml/runs/20261011-023802_feature_checks/single_feature_auc.csv` (700 training agents, 91 fraud); 7 feature-pattern pairs at separation 0.95 or above are listed as limitations in DATA_CARD.md.
- [x] Decision rule for `volume_vs_peers` written before the table. Evidence: `decision_rule.md`, written by `feature_analysis.py` before any AUC; `decision.md` says KEEP (AUC 0.780 > 0.55; max correlation 0.807 <= 0.85).
- [x] ID column test re-run against the feature matrix. Evidence: test `test_real_feature_matrix_contains_no_id_columns` passing.
- [x] No label or agent-id information enters the features. Evidence: test `test_no_label_or_id_information_enters_the_features` (renaming every agent id changes no feature value).

## Step 5: split (done first)

- [x] 70/15/15 split, stratified at agent level by pattern (legit plus 5 fraud patterns). Evidence: `ml/runs/20261011-023607_split_s42/split.csv`; 700 / 150 / 150 agents; tests `test_split_sizes_are_70_15_15` and `test_every_pattern_is_in_every_split`.
- [x] Fail if validation or test has fewer than 15 fraud agents. Evidence: `MIN_FRAUD_PER_EVAL_SPLIT = 15`; validation 20 and test 19; test `test_too_few_fraud_agents_fails`.
- [x] Split saved, with its seed. Evidence: `SPLIT_SEED = 42`; `split.csv` and `run_info.json` in the run folder; test `test_split_is_deterministic`.
- [x] No agent in two splits. Evidence: tests `test_no_agent_is_in_two_splits` and `test_duplicate_assignment_is_rejected`.
- [x] Rings spanning splits, and platform-wide `collusion_score`, documented. Evidence: DATA_CARD.md "Split (Step 5)" (13 of 14 rings span splits; not label leakage; deployment behaviour).

## Step 6: preprocessing

- [x] Scaler fitted on train only, then applied to validation and test. Evidence: `ml/runs/20261011-023846_preprocess_s0/scaler.joblib` and `scaler_stats.csv` (scaler mean equals training mean, for example `submission_frequency` 15.7329 against 15.6850 over all agents); test `test_scaler_statistics_come_from_training_only`.
- [x] Scaler saved. Evidence: `scaler.joblib` (scaler, feature list, `fitted_on="train"`, 700 agents); test `test_saved_scaler_round_trips`.
- [x] Before-and-after scaling sample. Evidence: `scaling_sample.md`, 5 training and 5 validation agents.

## Step 7: baselines (on validation)

- [x] Operating point fixed before results: alert budget of the top 15% of agents. Evidence: `metrics.ALERT_BUDGET = 0.15` (23 of 150 validation agents); random PR AUC baseline 0.133 reported.
- [x] Trivial baseline: random scores, mean of 20 seeds. Evidence: run `ml/runs/20261011-024811_baselines/`; ROC AUC 0.516 and PR AUC 0.157 (std 0.063 and 0.033).
- [x] Rule baseline: `submission_frequency` above the training 90th percentile. Evidence: cap 24; validation ROC AUC 0.795, PR AUC 0.373, P / R / F1 0.462 / 0.300 / 0.364.
- [x] Single-feature scores, with direction chosen on training. Evidence: `single_feature_directions.csv`; validation ROC AUC 0.614–0.813; recall by pattern reported in `baseline_metrics.csv`.

## Step 8: models (fit on train, score validation, default settings)

- [x] Isolation Forest (`n_estimators=200`, `contamination="auto"`, seed 42) and LOF (`novelty=True`, `n_neighbors=20`), each with 4 and 5 features. Evidence: run `ml/runs/20261011-024834_models_default_s42/`; `model_metrics.csv` and 4 `.joblib` files.
- [x] Scores oriented so higher = more anomalous. Evidence: `detectors.Detector.score`; test `test_scores_are_higher_for_an_obvious_outlier`.
- [x] Validation metrics, recall by pattern, training vs validation AUCs, fit time, scoring time per agent and model file size. Evidence: `model_metrics.csv` (for example, IF with 5 features: validation ROC AUC 0.891 against training 0.926; 0.112 ms per agent; 1,675,262 bytes).
- [x] Best on validation stated, without a final choice. Evidence: run report; the choice is left to Step 9.

## Step 9: selection on validation only

- [x] Selection rule written before running. Evidence: `ml/results/selection_rule.md` (written 02:55; the grid run started 02:56, `20261011-025652_selection_s42`).
- [x] Hyperparameter grid. Evidence: `grid.csv` (64 candidates) and `grid_per_seed.csv` (5 seeds each), all candidates kept.
- [x] Contamination not equal to the true fraud rate. Evidence: `contamination="auto"` everywhere; the run report explains that it does not change scores or rankings.
- [x] Threshold chosen on validation, saved as a value with the model version. Evidence: first under the original rule (cutoff 1.695, `lof_v3_4f`, run `…025652`), then re-done for the amended pick (cutoff 0.536, `if_v3_4f`, run `…031206`).
- [x] Train vs validation gap check. Evidence: `if_v3_4f` ROC AUC 0.933 against 0.904 (gap 0.029), PR AUC 0.805 against 0.751. The original pick had a gap of 0.029 too.
- [x] Models compared with and without `volume_vs_peers`, on validation only, with both reported. Evidence: best 4-feature 0.754 against best 5-feature 0.739, CIs overlapping about 97% (within noise).
- [x] Bootstrap 95% CI of validation PR AUC per candidate. Evidence: `pr_auc_ci_low` and `pr_auc_ci_high` in `grid.csv` (1000 resamples); test `test_weighted_average_precision_matches_sklearn`.
- [x] **Selection outcome confirmed by the author (option B: post hoc margin-only tie rule, on validation only).** Evidence: `selection_rule.md` amendment (03:11) and CHANGES.md; the original pick (LOF k=35, 0.682) is kept in run `20261011-025652_selection_s42`; the amended pick is `if_v3_4f` (IF, 100 trees, `max_samples` 64, `max_features` 1.0, 4 features; 0.742) in run `20261011-031206_selection_s42`; tests `test_amended_rule_simplicity_order` and `test_amended_rule_ignores_ci_overlap`.
- [x] Operating point recomputed for the amended pick and saved with `model_version` `if_v3_4f`. Evidence: `operating_point.json`, cutoff 0.536 (5:1); `operating_points.csv` with 2:1, 10:1, max F1 and 15% budget.
- [x] Acceptance checks Q1–Q6 re-evaluated on validation. Evidence: `acceptance_validation.csv`, all PASS (Q5 recall exactly 0.60).
- [ ] `ml/results/acceptance_criteria.md`, agreed with the supervisor first. (The draft is written, with a disclosure at the top; agreement is pending.) It must include these SRS-based criteria, each measured at Step 11:
  - [x] scoring time per agent and for the whole table. Evidence: criterion S1 in the draft.
  - [x] the model can be replaced without changing the pipeline, and the threshold is a config value. Evidence: criterion S2 in the draft.
  - [x] every score output includes `agent_id`, `analysis_period`, `score`, `flag`, `threshold`, `model_version` and `top_features`. Evidence: criterion S3 in the draft.
  - [x] scoring time at 500, 1000, 5000 and 10000 synthetic agents (timing only, no accuracy claim). Evidence: criterion S4 in the draft.

## Step 9B: learning curve

- [x] Learning curve at 10%, 25%, 50%, 75% and 100% of the training data, stratified, 5 repeats each. Evidence: run `20261011-030156_learning_curve` (the rule's choice) and `20261011-030202_learning_curve` (the margin-only alternative), each with `learning_curve.png`; both are flat from about 25–50%.

## Step 10: explainability (validation only)

- [x] Permutation importance (20 repeats, as PR AUC drop). Evidence: run `20261011-031637_explain/permutation_importance.csv`; `collusion_score` 0.227, `customer_similarity` 0.198, entropy 0.052, frequency 0.037.
- [x] Feature ablation (drop one at a time, `volume_vs_peers` in or out, seeds 1–5, bootstrap CI). Evidence: `ablation.csv`; without similarity −0.118, without collusion −0.106, without frequency +0.026 (within noise), with `volume_vs_peers` −0.002.
- [x] Top contributing features per flagged agent, for admin review, with the method stated. Evidence: largest scaled deviation (SHAP not installed); `validation_scores.csv` `top_features`; computed for flagged agents only (test `test_explanations_only_for_flagged_agents`).
- [x] Plain-language reason per flagged agent. Evidence: `validation_scores.csv` `reason`; test `test_top_contribution_and_reason_by_hand`.
- [x] Sanity check of the top feature by pattern. Evidence: `pattern_sanity.csv`; ring 4/6, sequential 3/3, duplicate 0/3, weak_ring 0/4, with mismatches listed and explained.
- [x] Validation scoring output with the agreed schema. Evidence: `validation_scores.csv` (`agent_id`, `analysis_period_start`, `analysis_period_end`, `score`, `flag`, `threshold`, `model_version`, `top_features`, `reason`); tests `test_output_schema_and_unflagged_rows` and `test_threshold_comes_from_the_bundle_not_the_code`.

## Step 11: final test (test set read once)

- [ ] Precision, recall, F1, ROC AUC and PR AUC.
- [ ] Bootstrap 95% confidence intervals.
- [ ] Confusion matrix.
- [ ] ROC, PR and score distribution plots.
- [ ] Error analysis and difficult cases.
- [ ] Collusion ring evaluation and ring CSV export.
- [ ] Subgroup results by the 8 former regions and by pattern, with counts.
- [ ] A sentence saying county-level results are too small to interpret.
- [ ] Timing and model file size.
- [ ] Comparison with the acceptance criteria, stating pass or fail.

## Step 12: robustness

- [ ] Seeds 1 to 10.
- [ ] 5-fold stratified cross-validation at agent level.
- [ ] Mean and spread reported.

## Step 13: artifacts and docs

- [ ] Model and scaler saved with joblib.
- [ ] A retrain command that writes a new versioned model, with `model_version` stored on every flag (periodic retraining).
- [ ] pytest tests for each module.
- [ ] `MODEL_CARD.md`, covering:
  - [ ] no labels used in training;
  - [ ] scores not calibrated;
  - [ ] results on synthetic data alone cannot prove real-world performance;
  - [ ] a section "Fit to SRS";
  - [ ] a section "Scope";
  - [ ] a section "Class imbalance handling": stratified agent-level split, PR AUC and F1 instead of accuracy, no oversampling or augmentation, and why.
- [ ] README with one command to reproduce everything.
- [ ] `CHANGES.md`.
- [ ] `DATA_CARD.md`.
- [ ] `run_info.json` with Python, OS, CPU, RAM and git commit hash (read-only `git rev-parse HEAD`). (Implemented in `ml/run_utils.py`; to be confirmed for the final runs.)
- [ ] Backend feature parity: `backend/src/pipeline.py` computes the v3 feature definitions, including `time_of_day_entropy`, the 24-hour window, similarity of identifiers and `volume_vs_peers`.
- [ ] Backend database reloaded with v3 data, and the backend tests that depend on it fixed. Today these are `test_agent_detail_context_lists_only_known_clients_and_categories` and the `A1104` API tests.
- [ ] List of known limitations:
  - [ ] strong rings are easy to separate;
  - [ ] in v2, the model choice was made after seeing test results;
  - [ ] the data is synthetic;
  - [ ] the test set is small.

## Disclosures for the documentation

- [ ] SMOTE from Chapter 3 was not used: it needs labels, and the models are unsupervised.
- [ ] All data is synthetic, not SalesMesh data.
- [ ] The features differ from Chapter 3.
- [ ] The generator was changed after seeing labels.
- [ ] The Streamlit dashboard became a React app.

## Unticked items at Step 13

To be filled in at Step 13.
