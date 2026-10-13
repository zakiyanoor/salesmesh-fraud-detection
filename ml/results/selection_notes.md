# Selection notes (Step 9, rerun on the change 5 data)

Written 2026-10-13, after the rerun, on validation only. This file adds notes; it does not change the rule. `selection_rule.md` is unchanged, and its hash in `FREEZE.md` equals the v3a hash.

## How LOF is ordered against Isolation Forest in a tie

The amended rule orders the tie set by fewer features, then fewer trees, then smaller `max_samples`, then faster scoring. **It does not say where a LOF goes in that order**, because LOF has neither trees nor `max_samples`.

**What the code does:** `selection.choose` reads a missing `n_estimators` or `max_samples` as 0. A LOF therefore counts as 0 trees and sorts as the simplest candidate among those with the same number of features. This behaviour has been in the code since the amendment (2026-10-11) and was not changed. `ml/tests/test_selection.py::test_amended_rule_tie_order_puts_lof_first` documents it.

**Run `20261013-093050_selection_s42`:**
- The tie set (within 0.02 of the top mean validation PR AUC) held 11 candidates: one LOF and 10 Isolation Forests, all with 4 features.
- **Chosen: `lof_v3_4f`, LOF, 4 features, `n_neighbors` 50.** It is also the top candidate: mean validation PR AUC **0.813** (CI 0.660 to 0.942).
- **Had a LOF been sorted after the forests**, the pick would have been Isolation Forest, 4 features, 100 trees, `max_samples` 64, `max_features` 0.8: mean validation PR AUC **0.804** (CI 0.646 to 0.936).
- The difference, 0.009, is well inside the CI widths (about 0.29).

**Decision (author, 2026-10-13):** accept `lof_v3_4f` as the rule, as implemented, selected it. The selection rule is not changed. The Isolation Forest above is kept as a sensitivity comparison in the Step 12a cross-validation.

## Pre-declared secondary analysis for Step 11 (written 2026-10-13, before any test result)

- **Primary result:** `lof_v3_4f` alone, at its saved cutoff (1.445). Every acceptance criterion (Q1 to Q6) is judged on it alone.
- **Secondary analysis, declared now:** Step 11 will also report, on test, the union of `lof_v3_4f` flags and `duplicate_activation_rule` flags (an agent is flagged if either flags it), with recall by pattern, precision and flagged count, next to the model alone and the rule alone.
- **The union is not a candidate for selection.** It does not replace the model, it does not change the cutoff, and no decision before or after Step 11 will be based on it. It is reported because the rule's validation precision (1.000) rests on the generator making R1 and R2 absolute for honest agents; the union shows how much a rule-based check adds on this synthetic data, not what it would add on real data.
- The validation version of this table (run `20261013-095059_union_reference`) was reported only and was produced after the model was frozen.
