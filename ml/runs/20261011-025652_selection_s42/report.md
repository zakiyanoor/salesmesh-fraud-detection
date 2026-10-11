# Step 9 selection report (run `20261011-025652_selection_s42`)

**Data used:** 700 training agents to fit, and 150 validation agents (20 fraud) to evaluate. Test labels were not loaded. The rules were written before this run:
- `ml/results/selection_rule.md`
- `ml/results/acceptance_criteria.md` (draft)

**Grid:** 64 candidates, each with 5 model seeds:
- Isolation Forest: 27 settings × 2 feature sets;
- LOF: 5 settings × 2 feature sets.

The full table is in `grid.csv` (one row per candidate) and `grid_per_seed.csv` (one row per candidate and seed). Every candidate that was not chosen is kept there.

## Why `contamination` stays `"auto"`

In both Isolation Forest and LOF, `contamination` only sets the internal offset behind `predict()`, which decides which agents fall below the cutoff. The anomaly scores themselves (`score_samples`) do not depend on it. So the ranking of agents, the ROC AUC and the PR AUC are the same for every contamination value. Setting it to the true fraud rate (about 0.13) would quietly hand the model the answer to "how many agents to flag".

Instead, the operating cutoff is chosen from validation scores directly, by minimising expected cost (next section).

## Result of the rule written in advance

| | Candidate | Mean validation PR AUC (95% CI) | ROC AUC | Model size |
|---|---|---|---|---|
| Top | IF, 4 features, 500 trees, `max_samples` 64, `max_features` 0.8 | 0.754 (0.580–0.910) | 0.909 | 1.82 MB |
| Best 5-feature | IF, 5 features, 100 trees, `max_samples` 64, `max_features` 1.0 | 0.739 (0.572–0.891) | 0.907 | 0.37 MB |
| Best LOF | LOF, 5 features, `n_neighbors` 50 | 0.717 (0.539–0.875) | 0.893 | 0.36 MB |
| **Chosen by the rule** | **LOF, 4 features, `n_neighbors` 35** | **0.682 (0.495–0.854)** | 0.877 | **0.26 MB** |

**Why the rule chose LOF.** The tie set has 60 of the 64 candidates. With 20 fraud agents, every bootstrap CI is about 0.33 wide, so almost every candidate's CI overlaps the top CI by at least 75%. Inside that tie set, the tie-break order (4 features first, then smallest saved model) selects the smallest 4-feature model, LOF with `n_neighbors` 35. It is ranked 61st of 64 on mean PR AUC.

**The rule as written does not do what it was meant to do.** The heavy-overlap condition makes almost every candidate a tie. A margin-only tie set (within 0.02 of the top: 28 candidates) would choose **IF, 4 features, 100 trees, `max_samples` 64, `max_features` 1.0** (mean PR AUC 0.742, CI 0.567–0.898, 0.35 MB).

The rule has **not** been changed after seeing the grid. This is left to the author.

## 4 features or 5?

**The rule picks the 4-feature version.** The difference is within noise:
- The best 4-feature IF scores 0.754 and the best 5-feature IF scores 0.739.
- Their CIs overlap almost completely (0.97 overlap share).
- Every 5-feature IF configuration is 0.01–0.04 below its 4-feature twin.

So `volume_vs_peers` adds nothing measurable on validation.

## Operating point (chosen configuration, refitted with seed 42, validation scores)

| Rule | Cutoff | Flagged (alert rate) | Precision | Recall | F1 | Cost per agent, 5:1 |
|---|---|---|---|---|---|---|
| **Min expected cost, 5:1 (chosen)** | **1.695** | 17 (11.3%) | 0.765 | 0.65 | 0.703 | 0.260 |
| Min expected cost, 2:1 | 1.695 | 17 (11.3%) | 0.765 | 0.65 | 0.703 | 0.260 |
| Min expected cost, 10:1 | 1.101 | 73 (48.7%) | 0.260 | 0.95 | 0.409 | 0.393 |
| Max F1 | 1.695 | 17 (11.3%) | 0.765 | 0.65 | 0.703 | 0.260 |
| Alert budget 15% | 1.500 | 23 (15.3%) | 0.565 | 0.65 | 0.605 | 0.300 |

The cutoff is saved in `operating_point.json` with `model_version` `lof_v3_4f`.

## Recall by fraud pattern, at the 5:1 cutoff (validation)

| Pattern | Recall | Agents in validation |
|---|---|---|
| ring | 1.00 | 6 |
| weak_ring | 0.50 | 4 |
| sequential | 1.00 | 3 |
| duplicate | 0.67 | 3 |
| weak | 0.00 | 4 |

## Train vs validation (chosen configuration)

| | Train | Validation |
|---|---|---|
| ROC AUC | 0.906 | 0.877 |
| PR AUC | 0.711 | 0.682 |

The ROC AUC gap is 0.029, within the 0.10 limit (criterion Q4).
