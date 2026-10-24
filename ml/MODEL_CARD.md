# Model card: `lof_v3_4f`

**Status:** final. The test set was read once on 2026-10-13 (Step 11, run `20261013-103859_final_evaluation_s42`), after every frozen hash had been checked. Stability across 10 other data seeds is Step 12 (run `20261013-104305_stability`). Full write-up: `results/FINAL_TEST_RESULTS.md`. The earlier draft for `if_v3_4f` (v3a data) is superseded; its numbers are in `results/CHANGES.md`.

## Test results (Step 11; 150 agents, 19 fraud; 95% bootstrap CIs)

| PR AUC | ROC AUC | Precision | Recall | F1 | Flagged |
|---|---|---|---|---|---|
| 0.845 (0.684 to 0.960) | 0.953 (0.897 to 0.992) | 0.600 (0.391 to 0.793) | 0.789 (0.583 to 0.957) | 0.682 (0.500 to 0.815) | 25 (16.7%) |

- **Confusion matrix:** 15 fraud caught, 4 missed (all weak fraud), 10 false alarms and 121 honest agents correctly left unflagged.
- **Recall by pattern:** ring 1.00 (6), weak_ring 1.00 (3), sequential 1.00 (3), duplicate 1.00 (3), weak 0.00 (4).
- **Acceptance criteria Q1 to Q6 and S1 to S4: all PASS.** Q2 is judged against the best single feature on test (`customer_similarity`, 0.670).
- **Baselines on test (PR AUC):** random 0.140, volume rule 0.346, `collusion_score` 0.565, `duplicate_activation_rule` 0.862 (precision 1.000; see below).
- **Pre-declared secondary analysis**, the union with `duplicate_activation_rule`: recall 1.000, precision 0.655, 29 flagged. It is not a candidate; the primary result is the model alone.
- **Collusion rings:** all 14 true rings have at least half their members flagged, and the 14 ring candidates map one to one onto them. Training and validation agents' flags here are in-sample.
- **Size and speed:** the model is 0.35 MB (bundle 0.37 MB); scoring takes 0.060 ms per agent.

## Stability across data seeds (Step 12)

Ten other synthetic datasets (seeds 101 to 110), each with its own split and its own fit, with the cutoff set without labels at the validated alert rate (13.3%), evaluated on its own test split:

| | PR AUC | ROC AUC | Precision | Recall | F1 |
|---|---|---|---|---|---|
| Mean (SD) | 0.811 (0.035) | 0.933 (0.019) | 0.748 (0.105) | 0.689 (0.058) | 0.713 (0.057) |
| Min to max | 0.746 to 0.860 | 0.900 to 0.956 | 0.609 to 0.933 | 0.579 to 0.737 | 0.611 to 0.824 |

Seed 42's test PR AUC and ROC AUC are about one SD above these means. Recall fell below 0.60 on 1 of 10 seeds.

## Model

- **What it is:** Local Outlier Factor (scikit-learn), `n_neighbors` 50, `novelty=True`, `contamination="auto"`. LOF is deterministic; the model seed (42) is recorded but unused.
- **Inputs:** exactly 4 features, `submission_frequency`, `time_of_day_entropy`, `customer_similarity` and `collusion_score` (`feature_engineering.MODEL_FEATURES`), scaled by a StandardScaler fitted on the 700 training agents only. No id, context or identity column is an input (`tests/test_no_id_inputs.py`, `tests/test_integrity_rules.py`).
- **Unsupervised:** no label is used in training. Labels were used only to choose among candidates on validation.
- **Operating point:** flag when score >= **1.445**, the minimum expected cost at 5:1 (a missed fraud agent costs 5 false alarms), chosen on validation and stored in `operating_point.json`. Scores are **not** calibrated probabilities.
- **Files:** `runs/20261013-093050_selection_s42/chosen_model.joblib`, `operating_point.json`; scoring bundle `runs/20261013-100433_explain/scoring_bundle.joblib`. Hashes: `results/FREEZE.md`.

## How it was chosen

- 64 candidates (Isolation Forest 27 settings and LOF 5 settings, each with 4 and 5 features), 5 seeds each, mean validation PR AUC with a bootstrap 95% CI. The selection rule and its amendment (`results/selection_rule.md`) were applied unchanged.
- The tie set (within 0.02 of the top) held 11 candidates. **Tie order note** (`results/selection_notes.md`): the rule does not say how to order a LOF against an Isolation Forest; the code reads a LOF's missing trees and `max_samples` as 0, so a LOF sorts as simplest. The chosen model is also the top candidate (0.813). Had a LOF sorted after the forests, the pick would have been Isolation Forest, 100 trees, `max_samples` 64, `max_features` 0.8 (0.804). The author accepted the rule's choice.
- 4 against 5 features: 0.813 against 0.782, CIs overlapping 94% (within noise).

## Validation results (150 agents, 20 fraud)

| PR AUC (95% CI) | ROC AUC | Flagged | Precision | Recall | F1 | Train ROC AUC (gap) |
|---|---|---|---|---|---|---|
| 0.813 (0.660 to 0.942) | 0.924 | 20 (13.3%) | 0.750 | 0.750 | 0.750 | 0.940 (0.016) |

A random score has PR AUC 0.133. The best single feature (`collusion_score`) has 0.574.

**Recall by pattern at the cutoff:** ring 1.00 (6 agents), weak_ring 0.75 (4), sequential 1.00 (3), duplicate 1.00 (3), weak **0.00** (4).

**Acceptance criteria Q1 to Q6 on validation:** all pass (Q5 recall 0.75 against 0.60; Q6 alert rate 13.3% against at most 25%). The final check is Step 11 on test.

**Cross-validation (Step 12a, informational):** 5 folds over the 850 training and validation agents. PR AUC 0.844 ± 0.029 and ROC AUC 0.937 ± 0.015. The Isolation Forest alternative scored 0.848 ± 0.032 and 0.942 ± 0.018, so the two are indistinguishable. Pooled recall of weak fraud at a 15% alert budget: 0.09.

**Learning curve:** validation PR AUC rises from 0.737 (10% of training agents) to 0.813 (75%) and is flat after.

**Feature importance** (PR AUC drop when permuted): `collusion_score` 0.324, `customer_similarity` 0.279, `time_of_day_entropy` 0.273, `submission_frequency` 0.040.

## The duplicate activation rule (reference only)

`duplicate_activation_rule` flags an agent if any (customer, client) pair it used was also used by another agent, or was repeated by it after a completed activation. It needs no model and no label. On validation it scores PR AUC 0.870 with precision 1.000 and recall 0.850; across the CV folds it scores 0.805 ± 0.054. It catches every weak fraud agent and no sequential agent.

**It is a reference ceiling, not real-world evidence.** Its precision of 1.000 exists because the generator makes rules R1 and R2 absolute for honest agents: an honest agent never shares a pair or repeats one after completion. Real data would contain honest errors (re-keyed records, system retries, shared family customers), and its precision would fall.

Combined with the model (either flagging), validation recall is 1.00 at 25 flags (precision 0.80). That table is reported only; it was produced after the model was frozen and was not used for any decision. The rule is not part of the model, and it was not a selection candidate.

## Explanations

- **Method:** robust deviation, d = (value − training median) / max(training IQR, 0.001), with statistics from training agents only and no labels. SHAP is not installed.
- **`top_features`:** the 3 features with the largest |d|, for every agent.
- **Reason text** (flagged agents only): a feature is shown only if |d| >= 1 **and** |value − training median| >= 10% of its training P5 to P95 range. If no feature passes, the reason reads "no single feature far from typical; flagged on the combination of features". Each shown feature is described against the typical (median) value and its standing among training agents, for example "busiest 24 hours: 7 submissions vs typical 14 (lower than 98 percent of training agents)". The percentile uses training values only, with no labels.
- **Sanity check on validation:** the top feature matched the pattern's expected feature for ring 6/6, weak_ring 4/4, sequential 3/3 and duplicate 3/3.
- **Limits:** it shows how unusual an agent is on each feature, not LOF's internal reasoning (density relative to neighbours). An agent can be flagged for an unusual combination even when no single feature is far from typical.

## Retraining

`python retrain.py` refits the scaler and the model on new unlabelled agent features. It sets the cutoff without labels, as the score quantile that flags the validated alert rate of 13.3%, and writes a new `model_version`. On the 850 training and validation agents it gave a cutoff of 1.476, flagging 113 agents (13.3%). See `README.md`.

## Scope

**What the model does:** once per analysis period (by default 2026-08-01 to 2026-08-31), it gives every agent an anomaly score from 4 behaviour features computed on the agent's activation records. Agents at or above the cutoff are flagged for **human review**, with the top 3 features and, for flagged agents, a plain-language reason. It belongs to SalesMesh module U-CS 56 (AI Fraud Detection).

**What it does not do:**
- It does not decide that an agent is fraudulent, and it does not block, suspend or penalise anyone; an analyst reviews each flag.
- It does not score single activations in real time; it scores agents per period.
- It does not use identity, account status, certifications, quality scores, commission, region or any id as an input.
- It does not give a probability of fraud; scores are not calibrated.
- It does not cover agent registration, KYC, training, certification, task allocation, verification, commission, reputation or analytics; other modules own those.
- It has not been tested on real SalesMesh data.

## Fit to SRS

| SRS | Requirement | How the model meets it | Evidence (validation, run `20261013-100436_system_checks_s101`) |
|---|---|---|---|
| 5.1 (S1) | Near real time | Scoring a precomputed feature table | 1000 agents in 0.032 s (0.032 ms per agent; limits 5 s and 10 ms); feature computation 1.4 s. PASS |
| Section 2 (S2) | Configurable, auditable; model replaceable | Any detector bundle with `score_samples` scores through the same entry point; the threshold is read from the bundle | A LOF bundle swap scored 50 agents with the bundle's threshold. PASS |
| 4.3, 8.2 (S3) | AI decisions and scoring outcomes logged | Every output row carries `agent_id`, the analysis period, `score`, `flag`, `threshold`, `model_version`, `top_features` and `reason` | All 1000 rows complete. PASS |
| 5.3 (S4) | Growth in agents | Timing at 500, 1000, 5000 and 10000 agents (timing only) | Scoring 10000 agents 0.25 s; features plus scoring 15.9 s (limits 60 s and 600 s). PASS. Generation was timed for behaviour only (the name lists allow 4,900 unique names) |
| 3.6 | Flag suspicious or low-quality onboardings | Agents whose activation behaviour is anomalous are flagged for review | Validation recall 0.75 at precision 0.75; quality scores are not an input |
| 7.5 | Detect anomalies, flag collusion and fake activations, admin review | `collusion_score` (collusion), `customer_similarity` (fake or repeated customers), timing and volume features; reasons support review | Recall ring 1.00, weak_ring 0.75, sequential 1.00, duplicate 1.00, weak 0.00 |
| 8.2 | Scoring outcomes recorded and auditable | `model_version` on every row; models, cutoff and rules hashed in `results/FREEZE.md`; `run_info.json` per run | `tests/test_freeze.py` |

## Class imbalance handling

- **Prevalence kept as it is:** 13% of agents are fraud (130 of 1000), and every split keeps about that share (train 13.0%, validation 13.3%, test 12.7%).
- **Stratified agent-level split:** 70/15/15, stratified by pattern (legitimate plus the five fraud patterns), so every split holds every pattern; validation and test must each have at least 15 fraud agents.
- **No SMOTE, oversampling or undersampling:** the model is unsupervised and never sees a label, so resampling the labelled classes would not change what it learns. Synthetic minority samples would also add invented agents to an evaluation that is already synthetic. Chapter 3 proposed SMOTE; it was not used, for this reason.
- **PR AUC is the main metric** (random baseline 0.133 on validation), with ROC AUC as secondary. Accuracy is not used: flagging nobody would score 87%.
- **Operating point from costs, not from the fraud rate:** the cutoff minimises expected cost at 5:1 (a missed fraud agent costs 5 false alarms), with 2:1 and 10:1 as sensitivity. `contamination` stays `"auto"` and is never set to the true fraud rate. The Step 7 and 8 comparison tables used a fixed alert budget of 15%, set before any result.

## Limitations

- **Synthetic data only.** Every pattern and rate is an assumption by the author. These results cannot show performance on real SalesMesh agents.
- **Weak fraud is missed by the model:** test recall 0.00 (0 of 4), validation 0.00 (0 of 4) and pooled CV recall 0.09. Weak fraud agents behave normally 75% to 90% of the time.
- **The duplicate_activation_rule is a reference ceiling, not a real-world estimate.** Its precision of 1.000 depends on the generator making R1 and R2 absolute for honest agents (no honest agent shares a (customer, client) pair or repeats one after a completed activation). Real records would contain honest errors and retries, so its precision there would be lower. It is not part of the model.
- **Small evaluation sets:** test has 19 fraud agents and validation 20 (3 to 6 per pattern), so every figure has a wide CI (test PR AUC 0.684 to 0.960).
- **Some patterns are separable on one feature:** strong rings (`collusion_score`), and sequential and duplicate agents (`customer_similarity`). Results on those patterns mostly reflect these signatures.
- **Honest false positives:** 10 of the 25 test flags (and 5 of 20 on validation) are honest: busy agents, quiet agents with concentrated hours (LOF flags unusually quiet agents too), and honest shared customers.
- **Platform-wide features:** `collusion_score` is computed across all agents' records, in every split, without labels, as in deployment; rings span splits (13 of 14).
- **The generator was changed after seeing labelled summaries: four label-aware changes, plus the integrity fix (change 5)** (DATA_CARD.md). The integrity fix came after validation results had been seen.
- **Scores are not probabilities,** and the cutoff assumes a 5:1 cost ratio that is not measured.
