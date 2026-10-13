# Model selection rule (Step 9)

**Written 2026-10-11 02:55, before the Step 9 grid was run.** Only training agents (to fit) and validation agents (to evaluate) are used. Test labels stay locked.

## Candidates

Every candidate is run with 4 features (base) and with 5 features (base + `volume_vs_peers`). `contamination` is `"auto"` everywhere. It is never set to the true fraud rate (about 0.13), and it does not change scores (see the Step 9 report).

| Model | Grid |
|---|---|
| Isolation Forest | `n_estimators` {100, 200, 500} × `max_samples` {64, 128, 256} × `max_features` {0.6, 0.8, 1.0} |
| LOF (`novelty=True`) | `n_neighbors` {10, 20, 35, 50, 100} |

That gives 27 × 2 = 54 Isolation Forest candidates and 5 × 2 = 10 LOF candidates, 64 in total.

## Selection metric

For each candidate:
- **Mean validation PR AUC over 5 model seeds (1, 2, 3, 4, 5).** Each seed fits the candidate on all training agents and scores the validation agents. LOF is deterministic, so its 5 seeds give the same value.
- **Bootstrap 95% CI** of that mean. Validation agents are resampled with replacement 1000 times, with a fixed bootstrap seed of 0; resamples with no fraud agent are redrawn. In each resample, PR AUC is computed for each seed's scores and averaged. The CI is the 2.5th to 97.5th percentile. It is wide because validation has only 20 fraud agents.

## Post hoc amendment (2026-10-11 03:11, made on validation only, before any test result)

**The tie rule below ("Choice", the ORIGINAL rule) was replaced by the author after the grid had been run.** This is a post hoc change. It was made on validation results only. No test label had been loaded, and the test set stays locked until Step 11.

**What the original rule did** (run `20261011-025652_selection_s42`, kept): its tie set held 60 of the 64 candidates. It chose **LOF, 4 features, `n_neighbors` 35**, with a mean validation PR AUC of **0.682** (CI 0.495–0.854), 61st of 64. The top candidate was Isolation Forest, 4 features, 500 trees, `max_samples` 64, `max_features` 0.8, at **0.754** (CI 0.580–0.910).

**Why it failed:** validation has only 20 fraud agents, so every bootstrap 95% CI of PR AUC is about 0.33 wide. Nearly every candidate's CI therefore overlaps the top CI by at least 75%, and the heavy-overlap condition could not tell good candidates from poor ones. The tie set became almost the whole grid, and the size tie-break, not performance, made the choice.

**Amended rule (now in force):**
1. **Top** = the candidate with the highest mean validation PR AUC.
2. **Tie set** = every candidate whose mean validation PR AUC is less than **0.02** below the top's. The CI-overlap condition is dropped. CIs are still computed and reported.
3. **Chosen** = the simplest candidate in the tie set, ordered by:
   1. fewer features (4 before 5);
   2. fewer trees;
   3. smaller `max_samples`;
   4. faster scoring (median time per validation agent).
4. Unchanged: the chosen configuration is refitted with `MODEL_SEED = 42`, and its validation scores set the operating point.

Nothing else in this file or in `acceptance_criteria.md` was changed. Code: `selection.choose` (amended) and `selection.choose_original` (original, still tested).

## Choice (ORIGINAL rule, superseded by the amendment above; kept for the record)

1. **Top** = the candidate with the highest mean validation PR AUC.
2. **Tie set** = the top candidate plus every candidate that meets either condition:
   - its mean PR AUC is less than **0.02** below the top's; or
   - its CI **overlaps heavily** with the top's CI. Heavy overlap means the overlapping part is at least **75%** of the shorter CI's width.
3. **Chosen** = the simplest candidate in the tie set, ordered by:
   1. fewer features (4 before 5);
   2. smaller saved model size (bytes of the seed-1 artifact: scaler and model). This captures fewer trees, smaller sub-samples and stored neighbours, and goes with faster scoring;
   3. higher mean PR AUC.
4. The chosen configuration is refitted on all training agents with `MODEL_SEED = 42`. That model's validation scores set the operating point (acceptance_criteria.md, section 3).

The report states whether the 4-feature or the 5-feature version was chosen, and whether the difference between them is within noise, meaning their CIs overlap heavily.

## What is kept

- The full grid, with one row per candidate and per seed, is saved as CSV in the selection run folder, including every candidate that was not chosen.
- Only the chosen model is saved as an artifact. Saving 320 fitted models (about 64 candidates × 5 seeds) would take several GB, and the per-seed metrics are enough to re-run any of them.
