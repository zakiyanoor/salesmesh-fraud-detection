# ML v3: three-way split, integrity-checked synthetic data, frozen LOF model and a read-once test

## Summary

This pull request rebuilds the U-CS 56 fraud detection ML pipeline (`ml/`) so that every model choice is made on a validation set and the test set is read exactly once.

- **Data (final after change 5):** synthetic SalesMesh-style data, seed 42: 1000 agents, 13% fraud, 135,494 activations.
  - Integrity rules R1 to R6 are enforced in the generator: honest agents never share a (customer, client) pair or re-complete one; only planted fraud breaks the rules.
  - Context files: agent identity (fictional), certifications, account status, quality score and commission. None of them is a model input.
- **Design:** agent-level 70/15/15 split, stratified by fraud pattern, seed 42. Scaler and models are fitted on train only. Selection and cutoff use validation only, under rules written in advance.
- **Model:** `lof_v3_4f`, a Local Outlier Factor (`n_neighbors` 50) on 4 features (`submission_frequency`, `time_of_day_entropy`, `customer_similarity`, `collusion_score`). The cutoff is 1.445, the minimum expected cost at 5:1, chosen on validation. Flagged agents get the top features and a plain-language reason.
- **Results:**
  - Stability over 10 independent datasets (seeds 101 to 110): PR AUC 0.811 (SD 0.035), ROC AUC 0.933.
  - Test (150 agents, 19 fraud, read once): PR AUC 0.845 (95% CI 0.684 to 0.960), recall 0.789, precision 0.600.
  - Acceptance criteria Q1 to Q6 and S1 to S4 all pass.
  - The model catches every ring, sequential and duplicate fraud agent, and no weak fraud agent.
- **Also added:** a reproduce command (`run_pipeline.py`), a label-free retrain command (`retrain.py`), 5-fold cross-validation, a stability study, a pre-declared secondary analysis (the model united with a duplicate-activation rule), and the data and model cards.
- **Backend not changed.** It still serves the v2 model; the schema and parity changes it needs are listed in `ml/results/CHANGES.md`, change 5.

## Evidence and where to find it

| What | File |
|---|---|
| Final test results, error analysis, rings, subgroups, limitations, disclosures | `ml/results/FINAL_TEST_RESULTS.md` |
| Acceptance criteria: exact text, thresholds, validation and test values | `ml/results/ACCEPTANCE_TABLE.md` (criteria: `ml/results/acceptance_criteria.md`) |
| Frozen hashes checked before the test was read | `ml/results/FREEZE.md`; `ml/results/test_read_once.json`; `ml/results/test_read_attempts.log` (one entry) |
| Selection rule, its post hoc amendment, tie order note, pre-declared secondary analysis | `ml/results/selection_rule.md`, `ml/results/selection_notes.md` |
| Step-by-step history with every number | `ml/results/CHANGES.md` |
| Progress checklist and unticked items | `ml/PLAN_CHECKLIST.md` |
| Data dictionary, rules R1 to R6, checks, independence table | `ml/DATA_CARD.md` |
| Model, SRS fit, scope, class imbalance, limitations | `ml/MODEL_CARD.md` |
| Deviations from Chapters 1 to 3, with disclosures | `ml/results/DEVIATIONS_FROM_PROPOSAL.md` |
| Run folders (`run_info.json` with seed, commit, parameters, hashes) | `ml/runs/20261013-*`; final test `ml/runs/20261013-103859_final_evaluation_s42` (figures `fig11` to `fig15`, with captions) |
| Earlier v3 material (v3a), archived unchanged | `ml/data/archive_v3a/`, `ml/results/archive_v3a/` |

**Reproduction check:** the `ml` folder was copied outside the repository and the whole pipeline re-run. The data, split, features, chosen model and cutoff, and every validation table were identical; the model's scores on all 1000 agents differed by 0.0.

## How to test

From `ml/`, with the repository's virtual environment active:

```bash
python -m pytest -q tests          # all ML tests (includes the frozen-hash checks)
python run_pipeline.py --dry-run   # the 13 steps of Steps 1 to 10, in order
python run_pipeline.py             # optional: full re-run (about 10 minutes; writes new run folders and overwrites the working copies in data/synthetic/ with identical files)
python final_evaluation.py         # must refuse: the test set has already been read once
```

Backend tests (unchanged by this PR) run from `backend/` with `pytest`. Three backend failures are known and listed in CHANGES.md:
- two predate this work;
- `test_collusion_ring_agents_from_synthetic_data_score_above_every_legit_agent` has a fixed floor of 0.3 that the new data (lowest strong ring 0.288) no longer meets; it is left for the backend sprint.

## Limitations

- **Synthetic data only;** these results cannot show performance on real SalesMesh agents.
- **19 fraud agents in the test set**, so the intervals are wide.
- **Weak fraud is missed** by the model (0 of 4 on test).
- **The duplicate-activation rule's precision of 1.000 depends on the generator** making R1 and R2 absolute for honest agents; it is a reference ceiling, not a real-world estimate.
- **Disclosures:**
  - the acceptance criteria were drafted after the default validation results had been seen (on earlier data);
  - the selection rule was amended post hoc, on validation only;
  - the generator was changed after labelled summaries had been seen, in four label-aware changes plus the integrity fix (change 5);
  - the supervisor's review of the criteria was pending because the supervisor was away;
  - v2 was deployed post hoc.

Closes #3
