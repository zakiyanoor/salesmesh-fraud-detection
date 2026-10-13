# Evaluation summary: redesigned ML pipeline (v2)

Pipeline, in order (all in `ml/`): `data_generation.py` → `clean_data.py` → `feature_engineering.py` → `split.py` → `model.py` / `model_lof.py` / `baseline.py` → `run_experiments.py` → `evaluate.py`. Raw outputs: `final_evaluation.csv`, `multi_seed_results.csv`, `data_cleaning_report.md`. The two `*_baseline_results.txt` files are the original v1 outputs, kept for comparison. The v1 Isolation Forest file (F1 0.800, ROC-AUC 0.981) could not be reproduced from the v1 code and data, which gave 0.933 / 0.998.

## What changed from v1

**Original setup (v1).** Both models were fitted and scored on all 115 agents, with no held-out data. Contamination was set to 0.13, which was the generator's known fraud share, so each model flagged exactly 15 agents by construction. The data was perfectly separable: fraud submitted only at 01:00–03:00, used 5-digit customer ids (legit used 6-digit), submitted about 8× the legit volume, and all three rings followed one template. With that setup, LOF scored 1.000 on every metric.

**Data generation (Step 1).**
- **The three rings now differ structurally:**

  | Ring | Agents | Shared pool | Timing | Daily submissions |
  |---|---|---|---|---|
  | 1 | 4 | 300 customers | late night | 8–20 |
  | 2 | 3 | 120 customers | evening | 5–14 |
  | 3 | 2 | 40 customers | business hours | 3–10 |

- **Fraud agents look partly normal.** 30% of each fraud agent's activity is normal (fresh customer ids at normal hours), and fraud agents skip about 10% of days.
- **16 of the 100 legitimate agents overlap with fraud behaviour:**
  - 6 make occasional night submissions (15% between 00:00 and 05:00).
  - 6 have repeat customers (15–50% of submissions go to 8 regulars).
  - 4 are high-volume.
- **All customer ids are now 6 digits.**
- **Registration dates are fixed to the analysis window,** so the output is byte-reproducible for a given seed.
- **Scale:** 115 agents (13.0% fraud) and 16,341 records, down from 24,991. The record count fell because fraud volume no longer sits far above legitimate volume.
- **The generator was adjusted once more before any model was run.** A feature review showed that `customer_similarity` still separated the classes perfectly, so the legit repeat-customer share was widened to vary between agents.
- **Result:** no single feature separates the classes. The number of legit agents whose value falls inside the fraud range is 4 for volume, 94 for time-of-day, 2 for customer similarity and 79 for collusion.

**Cleaning (Step 2).** These checks were run on the raw records without reading labels:
- nulls in every column
- exact duplicate rows
- duplicate record ids
- duplicate events (same agent, customer and timestamp)
- timestamps outside the analysis window
- invalid status values
- malformed customer ids
- unknown agents
- volume outliers, by IQR and robust z-score

Nothing needed removing: all 16,341 records passed. The checks were confirmed to catch 6 injected bad rows. 18 of 115 agents are volume outliers. They are reported but kept, because outliers are the signal being detected. Failed and pending activations are counted in `submission_frequency`: the feature measures attempted submissions, and the live backend counts them the same way. Status is independent of fraud in this data, so the choice has no effect here.

**Feature engineering (Step 3).**
- The analysis period is now derived from the data (`2026-08`) instead of being hard-coded.
- Each feature is documented: what it measures and why it indicates fraud.
- The offline features match the live backend `pipeline.py` exactly (largest difference about 1e-16).

**Evaluation protocol (Steps 4–10).**
- Agents are split 80/20, stratified on the fraud label: 92 train (12 fraud) and 23 test (3 fraud). The split is saved to `train_test_split.csv`.
- `StandardScaler` is fitted on the training agents only.
- Contamination is 0.10, a stated assumption rather than the known fraud rate (rationale in `preprocessing.py`).
- Both models are fitted on the training agents only. LOF now uses `novelty=True` so that it can score unseen agents.
- A frequency baseline flags agents above the 90th percentile of training-set volume.
- Variability is measured over seeds 1–5. Each seed reruns the full pipeline: new data, its own split, and its own models.
- The final evaluation uses the seed-42 test set, which was untouched until that step. No setting was changed after any test result was seen.

## Results

**Held-out test set (seed 42: 23 agents, 3 fraud):**

| Detector | Precision | Recall | F1 | ROC-AUC | TP | FP | FN | TN |
|---|---|---|---|---|---|---|---|---|
| Isolation Forest | 1.000 | 0.667 | 0.800 | 1.000 | 2 | 0 | 1 | 20 |
| LOF | 1.000 | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 | 20 |
| Frequency rule (baseline) | 1.000 | 0.667 | 0.800 | 0.967 | 2 | 0 | 1 | 20 |

**Variability across seeds 1–5 (each on its own 23-agent test set with 3 fraud), mean ± std [min–max]:**

| Detector | Precision | Recall | F1 | ROC-AUC | Pooled TP/FP/FN/TN |
|---|---|---|---|---|---|
| Isolation Forest | 1.000 ± 0 [1.00–1.00] | 1.000 ± 0 [1.00–1.00] | 1.000 ± 0 [1.00–1.00] | 1.000 ± 0 [1.00–1.00] | 15 / 0 / 0 / 100 |
| LOF | 0.150 ± 0.34 [0.00–0.75] | 0.200 ± 0.45 [0.00–1.00] | 0.171 ± 0.38 [0.00–0.86] | 0.923 ± 0.06 [0.85–1.00] | 3 / 4 / 12 / 96 |
| Frequency rule | 0.733 ± 0.44 [0.00–1.00] | 0.467 ± 0.30 [0.00–0.67] | 0.553 ± 0.33 [0.00–0.80] | 0.993 ± 0.02 [0.97–1.00] | 7 / 1 / 8 / 99 |

**How to read these numbers.**
- **The single test split disagrees with the multi-seed results.** On the seed-42 split LOF is perfect and Isolation Forest misses one agent (a duplicate-pattern agent that ranked above every legitimate agent but fell just below the threshold). Across five other seeds the reverse holds. With 3 fraud agents per test set, one agent moves recall by 33 percentage points, so the single split cannot rank the models. The multi-seed results are the more reliable comparison.
- **LOF ranks fraud well but fails at its threshold.** On seed 1, each test fraud agent's 5 nearest training neighbours were all fraud agents of the same pattern. Their local density therefore looked normal, and they scored 2.4–2.9, below the flag threshold of 3.87. They still scored above every test legitimate agent (at most 2.1). This is LOF's known masking effect: fraud forms small dense clusters, and the unlabelled training data contains fraud. The contamination setting was not tuned to compensate.
- **Volume alone ranks fraud almost perfectly.** The frequency rule's ROC-AUC of 0.97–1.00 means the classes remain close to separable even on this harder data.

## Limitations that remain

1. **The data is still too easy for Isolation Forest.** It scores 1.000 on every seed. No single feature separates the classes any more, but the four features together still do. All results are on synthetic data whose difficulty was chosen by the author. They show the pipeline works and that the evaluation is sound; they are not evidence of real-world performance.
2. **The test sets are tiny.** Each has 3 fraud agents (15 pooled across seeds), so every precision and recall figure has a very wide uncertainty. The seed-42 test set contains no ring 2 or sequential-pattern agents at all.
3. **Few independent fraud examples.** There are 15 fraud agents per dataset, built from 5 behavioural templates (3 rings plus 2 solo patterns). The effective number of independent fraud examples is far below 15.
4. **Variability only covers 5 seeds,** and it combines data variation with model variation.
5. **`collusion_score` is computed across the split.** Each agent is compared with all other agents, including test agents, which mirrors production. No labels cross the split, but the two partitions are not fully independent at the feature level.
6. **`time_of_day_dist` measures spread, not timing.** It cannot tell a 03:00 cluster from a 14:00 cluster, and it barely separates the classes in v2.
7. **Contamination 0.10 is an assumption, not a measurement.** Precision, recall and F1 depend on it (ROC-AUC does not), and it was not tested for sensitivity.
8. **One choice in the data generator was made after looking at feature distributions.** The repeat-customer share was widened in Step 1 once the feature review showed perfect separation. This was before any model was run, but it was informed by the labels.
9. **The deployed model is in-sample for most agents.** The live backend now loads the Isolation Forest artifact (`ml/models/isolation_forest_v2.joblib`, trained on the 92 seed-42 training agents) and no longer refits. On the reloaded database it flags 12 of 115 agents, all of them fraud. But 92 of those 115 agents are the model's own training agents, so that count is not a fresh test. The held-out figures above are the honest measure. With every other feature normal, an agent with collusion score 0.5 scores above legitimate agents but is not flagged.
