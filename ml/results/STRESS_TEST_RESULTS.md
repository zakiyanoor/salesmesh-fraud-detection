# Stress test results (issue #26)

**Run:** `ml/runs/20261022-185935_stress_test_s201` (2026-10-22 18:59), the only run.

**Rule:** `ml/stress_test_rule.md`, committed (`1f812e7`) before `stress_test.py` was written. `run_info.json` records that commit and the sha256 of the rule file, the script, `data_generation.py` and the scoring bundle. The generator and bundle hashes match `results/FREEZE.md`; they were checked before and after the run, and `tests/test_freeze.py` passed afterwards.

**Run log:**
- A first launch never started the script (the shell could not create its log file). No data was generated and no run folder was written.
- Nothing in the rule or the script was changed between that launch and the run.

## What was tested

- **Systems:**
  - the frozen `lof_v3_4f` bundle at the frozen cutoff 1.444799 (no refit, no tuning);
  - `duplicate_activation_rule` (pairs > 0);
  - their union (flagged by either).
- **Data:** new synthetic datasets from seed 201, 1000 agents each (130 fraud, rate 0.13). The seed 42 data and test set were not read.
- **Processing:** every dataset went through `clean_data` and `compute_feature_vectors` (1 to 30 August 2026) before scoring.

| Dataset | What changed |
|---|---|
| Control | Nothing: the frozen generator, seed 201. |
| Shifted | Ring sizes 7 to 12; sequential customer numbers with gaps of 1 to 3; duplicate fraud spread over 60 days; twice as many honest night-profile agents (8% to 16%), each with twice the night share (0.20 to 0.50). |
| Evasion A (rule aware) | Every fraud agent drops each activation that would trigger the duplicate rule. |
| Evasion B (feature aware) | Every ring and weak_ring agent draws each record's hour from the pooled hour distribution of honest agents. |

## Verdicts (as pre-registered)

`drop` = PR AUC on control − PR AUC on the test dataset. `Δ = drop_rule − drop_model`; its 95% interval comes from 2000 independent bootstrap draws of each dataset.

| Test | Model drop | Rule drop | Δ (95% CI) | PR AUC after: model / rule / union | Verdict |
|---|---|---|---|---|---|
| Shifted | 0.136 | 0.033 | −0.103 (−0.239 to 0.027) | 0.722 / 0.793 / 0.615 | No clear difference |
| Evasion A (rule aware) | 0.128 | 0.696 | 0.568 (0.460 to 0.674) | 0.731 / 0.130 / 0.431 | Model degrades more gracefully than the rule |
| Evasion B (feature aware) | 0.005 | 0.000 | −0.005 (−0.128 to 0.111) | 0.854 / 0.826 / 0.718 | No clear difference |

**Shifted.**
- The verdict is "no clear difference", because the interval includes zero.
- The point estimate favours the rule: the model's PR AUC fell four times as much as the rule's (0.136 against 0.033).
- After the shift the rule is higher than the model (0.793 against 0.722).

**Evasion A.**
- This test is built against the rule: fraud agents remove exactly the records the rule looks for. The rule's collapse to a random-level PR AUC (0.130, nothing flagged) is the attack working, not a finding.
- The verdict shows only that the model does not depend on the rule's signal. It does not show that the model is robust to evasion.
- The model lost every duplicate agent (recall 0.952 to 0.000). Avoiding the rule also removes the repeated customers that the model's `customer_similarity` responds to.

**Evasion B.**
- The transform did make ring timing look honest: the ring and weak_ring mean `time_of_day_entropy` went from 0.698 to 0.792, against 0.788 for honest agents.
- The model barely changed, and the high ring recall (1.000) comes mostly from `collusion_score`, not from robustness to timing. Ring agents' customer sharing was not touched: their mean `collusion_score` stayed at 0.369, against 0.011 for honest agents.
- Weak_ring recall, where sharing is lower, fell from 0.905 to 0.810.

## Results

| Dataset | System | PR AUC (95% CI) | ROC AUC | Flagged | Precision | Recall |
|---|---|---|---|---|---|---|
| Control | model | 0.859 (0.812 to 0.902) | 0.957 | 153 | 0.667 | 0.785 |
| Control | rule | 0.826 (0.763 to 0.882) | 0.900 | 104 | 1.000 | 0.800 |
| Control | union | 0.718 (0.654 to 0.786) | 0.971 | 181 | 0.718 | 1.000 |
| Shifted | model | 0.722 (0.653 to 0.787) | 0.891 | 153 | 0.529 | 0.623 |
| Shifted | rule | 0.793 (0.728 to 0.854) | 0.881 | 99 | 1.000 | 0.762 |
| Shifted | union | 0.615 (0.547 to 0.684) | 0.939 | 197 | 0.635 | 0.962 |
| Evasion A | model | 0.731 (0.659 to 0.792) | 0.871 | 132 | 0.614 | 0.623 |
| Evasion A | rule | 0.130 (0.109 to 0.150) | 0.500 | 0 | 0.000 | 0.000 |
| Evasion A | union | 0.431 (0.351 to 0.507) | 0.782 | 132 | 0.614 | 0.623 |
| Evasion B | model | 0.854 (0.805 to 0.901) | 0.954 | 151 | 0.662 | 0.769 |
| Evasion B | rule | 0.826 (0.763 to 0.884) | 0.900 | 104 | 1.000 | 0.800 |
| Evasion B | union | 0.718 (0.651 to 0.785) | 0.971 | 181 | 0.718 | 1.000 |

The fraud rate, which is the PR AUC of a random score, is 0.130 in every dataset.

### Recall by pattern

Agents per pattern in every dataset: ring 41, weak_ring 21, sequential 21, duplicate 21, weak 26.

| Dataset | System | ring | weak_ring | sequential | duplicate | weak |
|---|---|---|---|---|---|---|
| Control | model | 1.000 | 0.905 | 1.000 | 0.952 | 0.038 |
| Control | rule | 1.000 | 0.762 | 0.000 | 1.000 | 1.000 |
| Control | union | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Shifted | model | 1.000 | 0.619 | 1.000 | 0.286 | 0.000 |
| Shifted | rule | 1.000 | 0.524 | 0.000 | 1.000 | 1.000 |
| Shifted | union | 1.000 | 0.762 | 1.000 | 1.000 | 1.000 |
| Evasion A | model | 1.000 | 0.857 | 1.000 | 0.000 | 0.038 |
| Evasion A | rule | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| Evasion A | union | 1.000 | 0.857 | 1.000 | 0.000 | 0.038 |
| Evasion B | model | 1.000 | 0.810 | 1.000 | 0.952 | 0.038 |
| Evasion B | rule | 1.000 | 0.762 | 0.000 | 1.000 | 1.000 |
| Evasion B | union | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

### Evasion B feature check (means)

| Group | Agents | submission_frequency | time_of_day_entropy | customer_similarity | collusion_score |
|---|---|---|---|---|---|
| ring + weak_ring, control | 62 | 16.242 | 0.698 | 0.104 | 0.369 |
| ring + weak_ring, Evasion B | 62 | 16.258 | 0.792 | 0.104 | 0.369 |
| honest agents, control | 870 | 15.180 | **0.788** | 0.103 | 0.011 |

The mean `time_of_day_entropy` of honest agents in the control dataset is **0.788**. The pooled honest hour distribution used for the draw is in `honest_hour_distribution.csv`.

### Transform counts

| Transform | Identified and changed |
|---|---|
| Ring sizes | Control: 17 rings (11 strong, 6 weak), sizes 2 to 6. Shifted: 8 rings (5 strong, 3 weak), sizes 12, 9, 8, 8, 7, 7, 6, 5. |
| Night share | Honest night-profile agents 70 → 139. Their night-hour records (00:00 to 04:59): 1,477 of 8,309 → 5,766 of 16,497. |
| Sequential gaps | 21 agents; 4,413 records identified as pattern records; 4,397 renumbered (the other 16 drew the number they already had). |
| Duplicate spread | 21 agents; 452 pairs used at least 3 times; 3,742 records identified; 3,684 moved to another day; 1,866 landed after 30 August and were removed by cleaning (`timestamp_outside_window` 1,866). |
| Evasion A | Fraud agents: ring 41, weak_ring 21, sequential 21, duplicate 21, weak 26. 4,879 records dropped: ring 1,034, weak_ring 40, sequential 0, duplicate 3,312, weak 493. |
| Evasion B | 62 agents; 8,551 records given a new hour; 8,039 of them changed hour. |

## Disclosures

- **Ring size deviation.** The rule file set shifted ring sizes of 7 to 12. Two shifted rings have **6 and 5 members**. This comes from the frozen generator's own `make_rings`: when the agents left for the last ring are fewer than drawn, it shrinks that ring, and it only merges a remainder below 2. The other six rings are 7 to 12. The generator was not edited to prevent this, and the run was not repeated.
- **Union PR AUC caveat.** As pre-registered (and as in `stability.py`), the union's PR AUC is computed on its 0/1 flag. The model's and the rule's are computed on continuous scores (the score and the pair count). A 0/1 score has a step-shaped precision-recall curve, so the union's PR AUC is lower than both systems' on every dataset even where its recall is higher. It is not comparable with theirs. As the rule file states, the union is judged on recall, precision and the size of its drop.
- **Label use.** The transforms read the generated labels (`profile`) to choose which agents to change. That is by design for a stress test. It did not touch the frozen seed 42 data.
- **Heuristic pattern records.** The generator does not mark pattern records, so the sequential and duplicate transforms identified them heuristically (counts above).
- **Scope.** One seed and one combined shift; the shifts are not separated. Synthetic data only.

## Conclusion

The model and the rule fail in different ways:

| Situation | Model | Rule |
|---|---|---|
| Weak fraud | Misses it (recall 0.038 on control) | Catches it (1.000) |
| Sequential fraud | Catches it (1.000 everywhere) | Never catches it (0.000 everywhere) |
| Duplicate fraud spread over 60 days | Loses most of it (0.286) | Keeps it (1.000) |
| More honest night work | Loses precision (0.667 to 0.529) | Keeps precision at 1.000 |
| Rule-aware fraud (Evasion A) | Keeps most patterns | Catches nothing |

The model is not more robust to the shift than the rule; on this run it degraded more, though not significantly.

**The hybrid is the system.**
- The union kept recall at 1.000 on control and Evasion B and 0.962 on the shifted data, at a precision of 0.635 to 0.718.
- **The exception is Evasion A.** When fraud agents avoid the rule, the union is no better than the model alone (recall 0.623). It misses every duplicate agent and almost every weak agent, because the rule was the only system catching them.
- Duplicate and weak fraud that is aware of the rule is therefore undetected by both systems on this data.
