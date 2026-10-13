# Model card: `if_v3_4f` (DRAFT notes; the full card is written at Step 13)

**Status:** notes made at Step 10. These are validation results only; no test result exists yet.

## Model

- **What it is:** an Isolation Forest (scikit-learn) with 100 trees, `max_samples` 64 and `max_features` 1.0, `contamination="auto"` and seed 42.
- **Inputs:** a StandardScaler fitted on the 700 training agents only, applied to 4 features: `submission_frequency`, `time_of_day_entropy`, `customer_similarity` and `collusion_score`.
- **Unsupervised:** no labels are used in training.
- **How it was chosen:** on validation, by the amended selection rule (`ml/results/selection_rule.md`). The amendment was post hoc, made on validation only, and is logged in `CHANGES.md`.
- **Operating point:** score ≥ 0.536, the minimum expected cost at a 5:1 cost of a missed fraud agent to a false alarm, chosen on validation. It is stored in `operating_point.json`. Scores are **not** calibrated probabilities.

## Explanations

- **Method:** robust deviation, (value − training median) / max(training IQR, 0.001), on training agents only, with no labels.
- **What is shown:** `top_features` (the top 3 by |deviation|) for every agent. Flagged agents also get a plain-language reason listing the first feature and any other at least 1 IQR from the median, each against the typical (median) value. SHAP was not used, because it is not installed.
- **Limitations:**
  - It explains how unusual an agent is, not the forest's internal attribution.
  - The `customer_similarity` IQR is tiny (0.0024), so differences of about 0.002 can appear as reasons.
- **Validation sanity check:** each fraud agent's top feature matched its pattern for ring 6/6, sequential 3/3, duplicate 3/3 and weak_ring 4/4.

## Validation results (not final)

- **PR AUC:** 0.751 (CI 0.579–0.907), against 0.133 for a random score. ROC AUC 0.904.
- **At the operating point:** precision 0.923, recall 0.60, alert rate 8.7%.
- **Recall by pattern:** ring 1.00, sequential 1.00, duplicate 0.67, weak_ring 0.25, weak 0.00.

## Known limits (so far)

- The weak-fraud pattern is not detected (recall 0.00), and weak rings are mostly missed.
- Strong rings and sequential agents are separable on single features, so results on them mostly reflect those signatures.
- The validation set has 20 fraud agents, so every figure has a wide CI.
- The data is synthetic only.
