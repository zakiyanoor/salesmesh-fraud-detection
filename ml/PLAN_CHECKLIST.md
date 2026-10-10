# ML rework plan checklist

An item is ticked only when it has been done, with one line of evidence (a file, a number or a test name). At Step 13, every unticked item is listed.

## Step 0 and Step 1 (done)

- [x] Archive v2 results and data. Evidence: `ml/results/archive_v2/` (6 files) and `ml/data/archive_v2/` (7 files), each checked byte-identical with `cmp` (CHANGES.md, header).
- [x] Data generator rewritten. Evidence: `ml/data_generation.py` (parameters `--n-agents`, `--fraud-rate`, `--seed`), covered by the 21 tests in `ml/tests/test_data_generation.py`, all passing.
- [x] Labels kept in `labels.csv` and `rings.csv`, not in `agents.csv`. Evidence: `agents.csv` columns are `agent_id`, `registration_timestamp` and `region`; test `test_agents_file_carries_no_labels` (CHANGES.md, Step 1 table, "Labels" row).
- [x] Run folder with `run_info.json`. Evidence: `ml/runs/20261011-010944_datagen_s42/run_info.json`, holding the seed, parameters, data file hashes and library versions.

## Step 1B (data changes, then frozen)

Several items were partly done on the 600-agent Step 1B data. They stay unticked until the 1000-agent data is generated and checked.

- [ ] 47 counties, with a floor of 2 agents per county. (Partial: 47 counties are done, but there is no floor yet. At 600 agents, Lamu has 0 agents.)
- [ ] 1000 agents. (Not done: the current data has 600.)
- [ ] Shared popular customers per county. (Partial: done at 600 agents, where 188 of 522 legitimate agents have a non-zero `collusion_score`.)
- [ ] Weak rings. (Partial: done at 600 agents, with weak rings scoring 0.043–0.173 on `collusion_score`.)
- [ ] Categories and clients. (The generator already draws `client_id` and `category` independently of fraud. Not yet checked for 1B.)
- [ ] Fraud independent of region, category and client, with chi-square p values. (Partial: region only at 600 agents, province p = 0.997 and county p = 0.702.)
- [ ] Requirements traceability table (SRS).
- [ ] Reason for using 1000 agents.
- [ ] Every label-aware change listed in order. (Partial: DATA_CARD.md, Known issues item 1, lists 3 changes. It needs updating for the 1000-agent change.)
- [ ] Independent units are agents. (Partial: the DATA_CARD.md section "Independent units" exists, but its numbers are for 600 agents.)

## Step 2: cleaning

- [ ] Cleaning report.
- [ ] Near-duplicate check.

## Step 3: exploratory analysis

- [ ] Raw sample table.
- [ ] Distributions by group.

## Step 4: features

- [ ] Four features, plus the candidate feature `volume_vs_peers`.
- [ ] Single-feature AUC table (shortcut check).
- [ ] Decision rule for `volume_vs_peers` written before any model is run.

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
- [ ] `ml/results/acceptance_criteria.md`, agreed with the supervisor first. It must include these SRS criteria:
  - [ ] scoring time per agent and for the whole table;
  - [ ] model replaceable, with the threshold as a config value;
  - [ ] each output carries model version, threshold, score and top contributing features;
  - [ ] scoring time at 500, 1000, 5000 and 10000 synthetic agents.

## Step 9B: learning curve

- [ ] Learning curve at 10%, 25%, 50%, 75% and 100% of the training data.

## Step 10: explainability

- [ ] Permutation importance or SHAP.
- [ ] Top features per agent, for admin review.

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
- [ ] pytest tests for each module.
- [ ] `MODEL_CARD.md`, covering:
  - [ ] no labels used in training;
  - [ ] scores not calibrated;
  - [ ] no oversampling or augmentation, and why;
  - [ ] results on synthetic data alone cannot prove real-world performance;
  - [ ] a section "Fit to SRS".
- [ ] README with one command to reproduce everything.
- [ ] `CHANGES.md`.
- [ ] `DATA_CARD.md`.
- [ ] `run_info.json` with Python, OS, CPU, RAM and git commit hash (read-only `git rev-parse HEAD`). (Implemented in `ml/run_utils.py` and present in `ml/runs/20261011-010944_datagen_s42/run_info.json`; to be confirmed for the final runs at Step 13.)
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
