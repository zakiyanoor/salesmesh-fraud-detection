# Acceptance criteria: DRAFT, for agreement with the supervisor before Step 11

**Status:** draft, written 2026-10-11 02:55, before the Step 9 grid was run. **Disclosure:** it was drafted after the default validation results from Steps 7 and 8 had been seen, and before any test result. No test label has been loaded (`ml/labels_guard.py`).

Every criterion below is measured at Step 11, on the test set, read once. Criteria marked *(validation)* are also checked at Step 9. A criterion passes only if its stated condition holds. Each one is reported as PASS or FAIL, with the measured value.

## 1. Primary metric

**PR AUC** (average precision) of the anomaly score against the fraud label. Fraud is rare (about 13% of agents), so PR AUC reflects how useful the alert list is to an analyst. ROC AUC is reported alongside it as a secondary metric.

## 2. Error costs

| Error | Cost (relative units) | Why |
|---|---|---|
| Missed fraud agent (false negative) | **5** | A fraudulent agent keeps earning commission on fake activations for at least another analysis period, and the fraud can spread to a ring. |
| False alarm (false positive) | **1** | An analyst spends one review on an honest agent. The review is human-in-the-loop, so a false alarm costs time, not money paid out. |

The assumed ratio is **5 : 1**. It is an assumption, not a measured value. Sensitivity is reported at **2 : 1** and **10 : 1**.

Expected cost = 5 × FN + 1 × FP, reported per evaluated agent.

## 3. Operating point rule

- The score cutoff is chosen **on validation only**. It is the cutoff that minimises expected cost at 5 : 1.
- Ties go to the higher cutoff, which means fewer alerts.
- The cutoff is placed halfway between the lowest flagged and the highest unflagged validation score.
- It is saved as a value in the model's `operating_point.json`, together with `model_version`, and the scoring code reads it from there. It is not hard-coded, and it is not changed after Step 9.
- `contamination` is left at `"auto"` and does not set the operating point.

## 4. Pass/fail rules (model quality)

| # | Criterion | Pass condition |
|---|---|---|
| Q1 | Beats the best single-feature baseline *(validation)* | Mean validation PR AUC over seeds 1–5 is above the best single-feature validation PR AUC from Step 7 (`collusion_score`, 0.541). |
| Q2 | Beats the best single-feature baseline (test) | Test PR AUC is above the best single-feature test PR AUC. Each feature's direction is the one fixed on training at Step 7. |
| Q3 | Well above random (test) | Test PR AUC is at least 3 × the test fraud rate, **and** the lower bound of its bootstrap 95% CI (1000 resamples of test agents) is above the test fraud rate. |
| Q4 | No serious overfitting *(validation)* | Train ROC AUC − validation ROC AUC ≤ 0.10, for the chosen configuration. |
| Q5 | Recall at the chosen cutoff (test) | Overall recall is at least **0.60**. **Why 0.60:** with a 5 : 1 cost ratio, missing most fraud would defeat the purpose. The weak-fraud pattern (about 20% of fraud agents) is designed to be near-invisible, which caps realistic recall well below 1. A target of 0.60 asks the model to catch most of the remaining fraud. |
| Q6 | Analyst workload (test) | The alert rate at the chosen cutoff is at most **25%** of agents. Above that, review is no longer a targeted check. |

**No recall target is set for the weak-fraud pattern.** Weak fraud agents deviate only slightly: 10–25% of their submissions are fraudulent, and their volume is only slightly raised. Missing them is a **known limitation**, reported per pattern but not counted as a failure. Recall per pattern (ring, weak_ring, sequential, duplicate, weak) and the false-positive rate on the hard legitimate groups are reported without pass/fail targets. Each pattern has only 3–6 test agents.

## 5. SRS-based criteria (system)

Timings are taken on the reference machine named in `run_info.json`, as the median of 5 runs.

| # | Source | Criterion | Pass condition |
|---|---|---|---|
| S1 | SRS 5.1 (near real time) | Scoring time per agent, and for the whole table | Scoring an already-computed feature table takes ≤ 10 ms per agent and ≤ 5 s for the whole 1000-agent table. Feature computation is timed and reported separately. |
| S2 | SRS section 2 (configurable, auditable) | The model can be replaced without changing the pipeline, and the threshold is a config value | The scoring entry point loads any saved detector artifact that has `score(df)` and its own `operating_point.json`. A test swaps Isolation Forest for LOF with no code change. The threshold is read from the artifact, never from code. |
| S3 | SRS 4.3, 8.2 (AI decisions logged); 7.5 (admin review) | Output fields | Every score output row contains `agent_id`, `analysis_period`, `score`, `flag`, `threshold`, `model_version` and `top_features`, so it can be reviewed and logged. A schema test fails if any is missing or empty. |
| S4 | SRS 5.3 (growth) | Scaling time | Synthetic datasets of 500, 1000, 5000 and 10000 agents are generated and timed for feature computation plus scoring. **Timing only, with no accuracy claim.** Pass: all four complete, scoring 10000 agents takes ≤ 60 s, and end-to-end time (features + scoring) for 10000 agents is ≤ 10 minutes. |

## 6. What is not claimed

- These criteria are about synthetic data only. Passing them does not show real-world performance.
- Scores are not calibrated probabilities.
- The test set has 150 agents, 19 of them fraud. Every test figure is reported with its bootstrap 95% CI.
