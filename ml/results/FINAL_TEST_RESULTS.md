# Final test results (Step 11) and stability across seeds (Step 12)

**Run:** `ml/runs/20261013-103859_final_evaluation_s42` (2026-10-13 10:38 to 10:42). **Stability run:** `ml/runs/20261013-104305_stability`.

## What was tested

- **The frozen model `lof_v3_4f`:** Local Outlier Factor, `n_neighbors` 50, on 4 behaviour features (`submission_frequency`, `time_of_day_entropy`, `customer_similarity`, `collusion_score`). The scaler was fitted on the 700 training agents only. Agents with score >= **1.445** are flagged; that cutoff was chosen on validation.
- **The test set:** 150 agents held out since the split, **19 of them fraud** (12.7%). Their labels were read **once**, by `final_evaluation.py`.
- **Nothing was refitted and no cutoff was chosen on test.** No model, setting, feature, cutoff or criterion was changed after the results were seen.

**How the read-once rule was enforced**
1. Before any test label was read, the script checked the sha256 of every file in `results/FREEZE.md`: data, generator, features, split, scaler, model, operating point, scoring bundle, acceptance criteria, selection rule and selection notes. It also checked `labels.csv` against the hash recorded at generation. **All 17 matched.**
2. It logged the unlock in `results/test_read_attempts.log` (one entry).
3. After the run it wrote `results/test_read_once.json` (timestamp, run id, hashes). The script now refuses to run again; this was checked once, and `tests/test_final_evaluation.py` tests it.

**How the numbers were computed**
- Confidence intervals: 1000 bootstrap resamples of test agents, seed 42.
- Baselines use their frozen settings: random scores (mean of 20 seeds, 15% budget); the volume rule (`submission_frequency` > training P90, 24.1); the best single feature from Step 7 (`collusion_score`, 15% budget); and `duplicate_activation_rule` (pairs > 0).

## Results on the test set (primary: `lof_v3_4f` alone)

| Method | PR AUC (95% CI) | ROC AUC (95% CI) | Precision (CI) | Recall (CI) | F1 (CI) | Flagged (alert rate) |
|---|---|---|---|---|---|---|
| **`lof_v3_4f`, cutoff 1.445** | **0.845 (0.684 to 0.960)** | **0.953 (0.897 to 0.992)** | 0.600 (0.391 to 0.793) | 0.789 (0.583 to 0.957) | 0.682 (0.500 to 0.815) | 25 (16.7%) |
| Random scores | 0.140 (0.104 to 0.221) | 0.474 (0.445 to 0.504) | 0.104 | 0.126 | 0.114 | 23 (15.3%) |
| Volume rule | 0.346 (0.201 to 0.593) | 0.749 (0.603 to 0.878) | 0.385 | 0.263 | 0.312 | 13 (8.7%) |
| Best single feature (`collusion_score`) | 0.565 (0.360 to 0.778) | 0.734 (0.605 to 0.872) | 0.435 | 0.526 | 0.476 | 23 (15.3%) |
| `duplicate_activation_rule` | 0.862 (0.696 to 1.000) | 0.921 (0.823 to 1.000) | 1.000 (1.000 to 1.000) | 0.842 (0.647 to 1.000) | 0.914 (0.786 to 1.000) | 16 (10.7%) |

A random score's PR AUC equals the fraud rate, 0.127.

**In plain words:** the model ranks fraud agents well above honest ones (ROC AUC 0.95). At the frozen cutoff it flags 25 of 150 agents and catches 15 of the 19 fraud agents; 10 of its 25 flags are honest agents. It is far better than random scores, the volume rule and the best single feature. It is about level with the duplicate rule on PR AUC, but less precise. The duplicate rule's advantage comes from how the data was generated (see below).

**Score distribution:** `fig13_score_distribution.png` (full axis) and `fig13b_score_distribution_clipped.png` (axis clipped at 5, with an overflow bin). Two fraud agents score 8.8 and 9.8; in the full-axis figure they compress the region around the cutoff. The clipped figure is presentation only: it was redrawn from the saved run files (`test_scores.csv` and `error_analysis.csv`, by `redraw_score_figure.py`), with nothing recomputed and `labels.csv` not read again.

**Confusion matrix (model):**

| | Not flagged | Flagged |
|---|---|---|
| True honest | 121 | 10 |
| True fraud | 4 | 15 |

**Cost sensitivity.** Every cutoff below was chosen on validation, none on test.

| Rule | Cutoff | Flagged | Precision | Recall | Cost per agent at 5:1 | at 2:1 | at 10:1 |
|---|---|---|---|---|---|---|---|
| Min cost 5:1 (frozen) | 1.445 | 25 | 0.600 | 0.789 | 0.200 | 0.120 | 0.333 |
| Min cost 2:1 | 1.766 | 17 | 0.824 | 0.737 | 0.187 | 0.087 | 0.353 |
| Min cost 10:1 | 1.164 | 61 | 0.295 | 0.947 | 0.320 | 0.300 | 0.353 |

On test, the 2:1 cutoff would have given a slightly lower cost even at 5:1. This is reported, not acted on: the cutoff stays 1.445.

## Secondary analysis (pre-declared): union of model and duplicate rule

Declared in `results/selection_notes.md` before the test was read. It is not a candidate; the primary result is the model alone.

| | Flagged | Precision (CI) | Recall (CI) | F1 (CI) | ring (6) | weak_ring (3) | sequential (3) | duplicate (3) | weak (4) |
|---|---|---|---|---|---|---|---|---|---|
| Model alone | 25 | 0.600 | 0.789 | 0.682 | 1.00 | 1.00 | 1.00 | 1.00 | **0.00** |
| Duplicate rule alone | 16 | 1.000 | 0.842 | 0.914 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 |
| **Union (secondary)** | 29 | 0.655 (0.462 to 0.826) | 1.000 (1.000 to 1.000) | 0.792 (0.632 to 0.905) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

The union catches all 19 fraud agents with the model's same 10 false alarms. The two methods are complementary: the rule finds weak fraud, the model finds sequential fraud. The union's PR AUC (0.655) and ROC AUC (0.962) are computed on a 0/1 flag, so they are not comparable with score-based AUCs.

## Recall by pattern and by former region (model)

| Pattern | Test agents | Flagged | Recall |
|---|---|---|---|
| ring | 6 | 6 | 1.00 |
| weak_ring | 3 | 3 | 1.00 |
| sequential | 3 | 3 | 1.00 |
| duplicate | 3 | 3 | 1.00 |
| weak | 4 | 0 | **0.00** |
| legit (plain) | 97 | 5 | false alarms |
| legit_busy | 11 | 3 | false alarms |
| legit_night | 13 | 1 | false alarm |
| legit_repeat | 10 | 1 | false alarm |

| Former region | Agents | Fraud | Flagged | Caught | False alarms |
|---|---|---|---|---|---|
| Central | 16 | 1 | 3 | 1 | 2 |
| Coast | 12 | 1 | 2 | 1 | 1 |
| Eastern | 29 | 6 | 5 | 4 | 1 |
| Nairobi | 17 | 4 | 5 | 4 | 1 |
| North Eastern | 6 | 0 | 0 | 0 | 0 |
| Nyanza | 15 | 0 | 1 | 0 | 1 |
| Rift Valley | 39 | 4 | 5 | 2 | 3 |
| Western | 16 | 3 | 4 | 3 | 1 |

**These counts are very small:** 0 to 6 fraud agents per region and 3 to 6 per pattern. No difference between regions or patterns can be read from them, and county-level results are too small to interpret at all. No threshold was changed for any subgroup.

## Error analysis (every miss and every false alarm)

The full table, with the four feature values and the reason text, is `error_analysis.csv` in the run folder.

**Missed fraud: 4 agents, all of the weak pattern.** Weak fraud agents make only 10% to 25% fraudulent submissions and otherwise behave normally.

| Agent | Score | One-line explanation |
|---|---|---|
| A36685 | 1.437 | Missed by 0.008: hours slightly spread (entropy 0.87) and 3% shared customers, both mild. |
| A10851 | 1.339 | Slightly busy (22 per 24 h), spread hours and similarity 0.106: three mild signals, none strong. |
| A38569 | 1.254 | Spread hours, 4% shared customers and similarity 0.106, all within the range of honest agents. |
| A98184 | 1.144 | Only customer similarity is a little high (0.106); otherwise typical. |

**False alarms: 10 honest agents.**

| Agent | Group | Score | One-line explanation |
|---|---|---|---|
| A30517 | legit | 2.796 | Very quiet (busiest 24 h only 4, below every training agent) with concentrated hours; LOF flags sparse, unusual agents too. |
| A69429 | legit | 2.199 | Quiet (7 per 24 h) with concentrated hours (entropy 0.67). |
| A82603 | legit_busy | 1.914 | Very busy (41 per 24 h); high volume is the designed hard case. |
| A47828 | legit_busy | 1.742 | Very busy (39 per 24 h). |
| A40784 | legit | 1.555 | 8% of customers shared with other agents, through the county's popular customers on other clients (honest sharing). |
| A34931 | legit_repeat | 1.537 | Cross-sold customers raise identifier similarity to 0.118; the designed hard case. |
| A74332 | legit_busy | 1.521 | Very busy (36 per 24 h). |
| A77839 | legit_night | 1.492 | Night work spreads hours (entropy 0.84) and similarity is a little high. |
| A30861 | legit | 1.478 | 7% shared customers, through honest popular-customer sharing. |
| A79514 | legit | 1.477 | Spread hours (0.85) and 3% shared customers. |

## Collusion ring export

The frozen model scored all 1000 agents, as it would in deployment. Flagged agents sharing at least 3 customers were joined into ring candidates (`ring_candidates.csv`); the threshold of 3 was set in the script before the run. The candidates were then compared with the true rings.
- **14 of 14 true rings have at least one flagged member, and 14 of 14 have at least half their members flagged.** The 9 strong rings are fully flagged; the 5 weak rings have 2 to 5 of their 3 to 5 members flagged.
- **The 14 candidates map one to one onto the 14 true rings**, with no honest agent in any candidate.
- **Caveat:** training and validation agents' flags here are in-sample for the model. The test members of rings (9 agents: 6 strong, 3 weak) are all flagged.

## Timing and size

| What | Value |
|---|---|
| Scoring, test agents | 0.060 ms per agent; 0.206 ms per agent with explanations |
| Scoring, all 1000 agents | 0.035 s |
| Saved model (`chosen_model.joblib`, model and scaler) | 0.35 MB (347,013 bytes) |
| Scoring bundle (model, scaler, cutoff, explanation reference) | 0.37 MB (372,744 bytes) |

## Acceptance criteria

| Criterion | Measured on | Value | Result |
|---|---|---|---|
| Q1 mean validation PR AUC > best single feature | validation | 0.813 > 0.574 | PASS |
| Q2 test PR AUC > best single-feature test PR AUC | test | 0.845 > 0.670 (best of the 5 features, `customer_similarity`; `collusion_score` 0.565) | PASS |
| Q3 test PR AUC >= 3 x fraud rate, CI low > fraud rate | test | 0.845 >= 0.380; CI low 0.684 > 0.127 | PASS |
| Q4 train minus validation ROC AUC <= 0.10 | validation | 0.016 (train minus test: -0.013) | PASS |
| Q5 recall >= 0.60 | test | 0.789 | PASS |
| Q6 alert rate <= 25% | test | 16.7% | PASS |
| S1 scoring time | test | 0.060 ms per agent; 1000 agents in 0.035 s | PASS |
| S2 model replaceable, threshold from config | frozen system checks | LOF swap, threshold read from the bundle | PASS |
| S3 output fields | test | all 150 rows have the 9 fields, non-empty | PASS |
| S4 scaling | frozen system checks | 10000 agents: scoring 0.25 s, end to end 15.9 s | PASS |

**All ten pass.** Weak-fraud recall (0 of 4) has no target in the criteria. It is a known limitation, not a pass.

**Q6 is defined on the test alert rate, with a limit of 25%.** The test alert rate was 16.7% (25 of 150), so Q6 passes. The 15% figure elsewhere in this work is the Step 7 and 8 comparison budget, not an acceptance criterion. The test alert rate is above that 15% budget and above the validation alert rate (13.3%); this is reported, not acted on. The exact criterion text, thresholds, and validation and test values are in `results/ACCEPTANCE_TABLE.md`.

## Stability across 10 other data seeds (Step 12)

Seeds 101 to 110 are separate synthetic datasets. Each was generated, split 70/15/15 by pattern, fitted with `lof_v3_4f` (frozen settings, scaler on training only) and evaluated on its own test split (150 agents, 19 fraud). The cutoff was set **without labels**, as the validation-score quantile flagging 13.3% of agents. No tuning. The seed 42 test set was not used again.

| Method | PR AUC mean (SD) [min to max] | ROC AUC mean (SD) [min to max] | Precision mean (SD) | Recall mean (SD) [min to max] | F1 mean (SD) |
|---|---|---|---|---|---|
| `lof_v3_4f` | 0.811 (0.035) [0.746 to 0.860] | 0.933 (0.019) [0.900 to 0.956] | 0.748 (0.105) | 0.689 (0.058) [0.579 to 0.737] | 0.713 (0.057) |
| `duplicate_activation_rule` | 0.835 (0.039) [0.770 to 0.862] | 0.905 (0.022) [0.868 to 0.921] | 1.000 (0.000) | 0.811 (0.044) [0.737 to 0.842] | 0.895 (0.028) |
| Union (secondary) | 0.792 (0.097) [0.675 to 0.950] | 0.972 (0.023) [0.924 to 0.996] | 0.805 (0.086) | 0.979 (0.037) [0.895 to 1.000] | 0.882 (0.059) |

Per-seed values: `stability_per_seed.csv`.

**Seed 42 against the average:** seed 42's test PR AUC (0.845) and ROC AUC (0.953) are about one standard deviation above the 10-seed means (0.811 and 0.933), so seed 42 was a somewhat favourable but not unusual draw. Its higher recall (0.789 against 0.689) also reflects its cost-based cutoff, which flagged 16.7% of agents against 13.3% here. Recall fell below 0.60 on 1 of the 10 seeds (seed 104, 0.579), so Q5 is not guaranteed on new data.

## Limitations

- **Synthetic data only.** Every pattern and rate is an assumption by the author. These results cannot show how the model would perform on real SalesMesh agents.
- **19 fraud agents in the test set** (3 to 6 per pattern), so the intervals are wide: PR AUC 0.684 to 0.960, recall 0.58 to 0.96.
- **Weak fraud is missed by the model** (0 of 4 on test; recall about 0.09 in cross-validation).
- **The duplicate rule's precision of 1.000 depends on the generator making R1 and R2 absolute for honest agents:** no honest agent shares a (customer, client) pair or repeats one after completion. Real records would contain honest errors, so it is a reference ceiling, not a real-world estimate. The same caveat applies to the union.
- **Strong rings, sequential and duplicate agents** separate on single features in this data, so the model's perfect recall on them mostly reflects those designed signatures.
- **LOF also flags unusually quiet agents** (2 of the 10 false alarms).
- **The ring export uses in-sample flags** for training and validation agents.

## Disclosures

1. **The acceptance criteria were drafted after the default validation results had been seen**, on the earlier (v3a) data, and before any test result.
2. **The selection rule was amended post hoc** (2026-10-11), on validation only, after the original tie rule chose a weak candidate. The tie order between LOF and Isolation Forest is recorded in `results/selection_notes.md`.
3. **The generator was changed after labelled summaries had been seen:** four label-aware changes (v2 repeat-share widening; v3 Step 1 customer id length; Step 1B popular customers and weak rings; Step 1C removal of hard limits), plus the integrity fix (change 5, 2026-10-13), which came after validation results had been seen. All are listed in `DATA_CARD.md`.
4. **The supervisor's review of the acceptance criteria was pending** at the time of the test, because the supervisor was away. The criteria were applied exactly as hashed in `FREEZE.md`.
5. **v2 was deployed post hoc:** the v2 switch of the live detector to Isolation Forest was decided after seeing test results. That is why v3 added a validation set and this read-once test.
