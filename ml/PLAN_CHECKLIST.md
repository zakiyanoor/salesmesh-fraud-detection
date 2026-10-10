# ML rework plan checklist

An item is ticked only when it has been done, with one line of evidence (a file, a number or a test name). At Step 13, every unticked item is listed.

- [x] **Scope: U-CS 56 only; other SalesMesh modules out of scope.** Evidence: DATA_CARD.md "Scope" section; the generator has no client management, task limits, payouts or reputation.

## Step 0 and Step 1 (done)

- [x] Archive v2 results and data. Evidence: `ml/results/archive_v2/` (6 files) and `ml/data/archive_v2/` (7 files), each checked byte-identical with `cmp` (CHANGES.md, header).
- [x] Data generator rewritten. Evidence: `ml/data_generation.py` (parameters `--n-agents`, `--fraud-rate`, `--seed`); `ml/tests/test_data_generation.py`, 30 tests passing.
- [x] Labels kept in `labels.csv` and `rings.csv`, not in `agents.csv`. Evidence: `agents.csv` columns are `agent_id`, `registration_timestamp` and `region`; test `test_agents_file_carries_no_labels`.
- [x] Run folder with `run_info.json`. Evidence: `ml/runs/20261011-015537_datagen_s42/run_info.json`, holding the seed, parameters, data file hashes, library versions and system information.

## Step 1B (data changes, then FROZEN)

- [x] 47 counties, with a floor of 2 agents per county. Evidence: `COUNTY_MIN_AGENTS = 2`; agents per county min 5, median 20, max 89, 0 counties under 5; test `test_every_county_has_at_least_the_floor`.
- [x] 1000 agents. Evidence: `DEFAULT_N_AGENTS = 1000`, giving 1000 agents with 130 fraud (0.130); test `test_default_counts_follow_n_agents_and_fraud_rate`.
- [x] Shared popular customers per county. Evidence: 359 of 870 legitimate agents have a non-zero `collusion_score` (max 0.074); test `test_some_legit_agents_share_customers_mostly_within_their_county`.
- [x] Weak rings. Evidence: 5 weak rings with 21 agents, `collusion_score` 0.056 / 0.094 / 0.125 (min / median / max), 4 of 21 inside the legitimate range; test `test_weak_rings_share_less_than_strong_rings`.
- [x] Categories and clients. Evidence: `clients.csv` holds 20 clients across 12 categories; each agent has 1–3 clients (450 / 412 / 138 agents); tests `test_clients_reference_list`, `test_record_category_comes_from_its_client` and `test_agents_work_with_one_to_three_clients_mostly_in_one_or_two_categories`.
- [x] Fraud independent of region, category and client, with chi-square p values. Evidence: county p = 0.649, former region p = 0.403, primary category p = 0.547, primary client p = 0.702 (`data_checks.json`); test `test_fraud_is_independent_of_county_region_category_and_client`.
- [x] Requirements traceability table (SRS). Evidence: DATA_CARD.md "Requirements traceability", covering 2.2.4, 7.5, 3.6, 3.1/8.4, 4.3/8.2, 5.1, 5.3 and the section 2 constraints, plus the Chapters 1–3 behaviours.
- [x] Reason for using 1000 agents. Evidence: DATA_CARD.md "Why 1000 agents" (about 19–20 fraud agents per split at 1000, against about 11–12 at 600).
- [x] Every label-aware change listed in order. Evidence: DATA_CARD.md "Label-aware changes, in order" lists 3 changes, plus the non-label changes listed separately.
- [x] Independent units are agents. Evidence: DATA_CARD.md "Independent units" (1000 agents and 130 fraud; the 138,756 records are not independent).
- [x] Time zone, observation window and data dictionary. Evidence: DATA_CARD.md sections "Time zone and observation window" (Africa/Nairobi, 2026-08-01 to 2026-08-30) and "Files and data dictionary"; test `test_timestamps_fall_in_the_observation_window`.
- [x] Duplicate pattern is the same customer for the same client; the same customer for different clients is rare. Evidence: tests `test_duplicate_fraud_resubmits_the_same_customer_for_the_same_client` and `test_same_customer_for_different_clients_is_rare` (2,150 pairs, under 5%).
- [x] The data has customer ids only, with no addresses, stated as a limitation. Evidence: DATA_CARD.md "Limits of this data".
- [x] Generator declared FROZEN. Evidence: DATA_CARD.md header; the `data_generation.py` docstring says it is frozen at Step 1B.

## Step 2: cleaning

- [ ] Cleaning report.
- [ ] Near-duplicate check.

## Step 3: exploratory analysis

- [ ] Raw sample table.
- [ ] Distributions by group.

## Step 4: features

- [ ] The four features: `submission_frequency`, `time_of_day_entropy`, `customer_similarity` and `collusion_score`.
- [ ] Feature functions take `period_start` and `period_end`; output rows include `analysis_period_start` and `analysis_period_end`.
- [ ] `submission_frequency` uses a sliding window (busiest 24 hours, `SUBMISSION_WINDOW_HOURS`).
- [ ] `customer_similarity` is the mean pairwise similarity of customer identifiers, as defined in DATA_CARD.md and confirmed against Chapter 3.
- [ ] Candidate feature `volume_vs_peers`: peers are the same primary category within the same former region, falling back to the same category in all regions, then to all agents, with minimum group size `PEER_MIN_GROUP = 15`.
- [ ] Single-feature AUC table (shortcut check).
- [ ] Decision rule for `volume_vs_peers` written before any model is run: keep it only if it passes the same checks as the other features.

## Step 5: split

- [ ] 70/15/15 split, stratified at agent level.
- [ ] Fail if validation or test has fewer than 15 fraud agents.
- [ ] Split saved, with its seed.
- [ ] No agent in two splits.

## Step 6: preprocessing

- [ ] Scaler fitted on train only.
- [ ] Before-and-after scaling sample.

## Step 7: baseline

- [ ] Simple rule baseline and trivial baseline, both on validation.

## Step 8: models

- [ ] Isolation Forest and LOF (`novelty=True`), on the same features and split.

## Step 9: selection on validation only

- [ ] Selection rule written before running.
- [ ] Hyperparameter grid.
- [ ] Contamination not equal to the true fraud rate.
- [ ] Threshold chosen on validation.
- [ ] Train vs validation gap check.
- [ ] Models compared with and without `volume_vs_peers`, on validation only, with both results reported.
- [ ] `ml/results/acceptance_criteria.md`, agreed with the supervisor first. It must include these SRS-based criteria, each measured at Step 11:
  - [ ] scoring time per agent and for the whole table;
  - [ ] the model can be replaced without changing the pipeline, and the threshold is a config value;
  - [ ] every score output includes `agent_id`, `analysis_period`, `score`, `flag`, `threshold`, `model_version` and `top_features`;
  - [ ] scoring time at 500, 1000, 5000 and 10000 synthetic agents (timing only, no accuracy claim).

## Step 9B: learning curve

- [ ] Learning curve at 10%, 25%, 50%, 75% and 100% of the training data.

## Step 10: explainability

- [ ] Permutation importance or SHAP.
- [ ] Feature ablation: drop one feature at a time, on validation only, to answer the research question on which features are most effective.
- [ ] Top contributing features for each flagged agent, for admin review.

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
