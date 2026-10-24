# Stress test rule (written before any stress run)

Issue #26. Written on 2026-10-22, before any stress data was generated or scored. This file is committed before the run. After the run it is not edited; results go to `results/STRESS_TEST_RESULTS.md`.

## Question

Does the frozen model `lof_v3_4f` lose less performance than `duplicate_activation_rule` in each of three situations?

1. Fraud behaves differently from the data the model was chosen on (shifted generator).
2. Fraud agents know the rule and avoid triggering it (Evasion A, rule aware).
3. Ring agents know the model's timing feature and hide their timing (Evasion B, feature aware).

Their union (either flags) is reported beside both.

## What stays fixed

- **Model and cutoff:** the frozen scoring bundle `runs/20261013-100433_explain/scoring_bundle.joblib`, with cutoff 1.444799 (`results/FREEZE.md`). No refit, no new cutoff, no tuning.
- **Rule:** `baselines.duplicate_activation_counts`, unchanged. An agent is flagged when pairs > 0.
- **Generator:** `data_generation.py` is not edited. Its sha256 is checked before and after the run, and `tests/test_freeze.py` must pass after it.
- **Seed 42 data and test set:** not read. Every stress dataset is new, from seed **201**, a seed no earlier run has used. All 1000 agents are evaluated, because none of them was used to fit or choose anything.
- **Processing:** each dataset goes through the same steps as deployment: `clean_data.clean_data`, then `feature_engineering.compute_feature_vectors` over 1 to 30 August 2026, then the frozen bundle.

## Datasets

| Dataset | How it is made |
|---|---|
| **Control** | `generate_dataset(seed=201)`, unchanged. This is the reference all three tests are compared with. |
| **Shifted** | Seed 201 with all five shifted settings below, applied together. |
| **Evasion A (rule aware)** | The control dataset with the Evasion A transform below. |
| **Evasion B (feature aware)** | The control dataset with the Evasion B transform below. |

### Shifted generator settings

The generator only takes `--seed`, `--n-agents` and `--fraud-rate` as parameters. The new script `stress_test.py` produces each shift as follows:

| Shift | Frozen setting | Shifted setting | How it is produced |
|---|---|---|---|
| Ring sizes | `RING_SIZE_RANGE` (2, 6) members, strong and weak rings | (7, 12) members | Module constant set at run time, before `generate_dataset` is called. The file is not edited. |
| Sequential gaps | Each sequential customer number is the previous one + 1 | The previous one + a random gap of 1, 2 or 3 | Post-processing of the generated records (below). |
| Duplicate fraud over 60 days | Repeats fall inside the 30-day analysis window | Repeats are spread over 60 days (1 August to 29 September); only the 30-day window is analysed | Post-processing of the generated records (below). |
| Night share: agents | `LEGIT_PATTERN_SHARES["legit_night"]` 0.08 of honest agents have the night profile | 0.16 (the plain `legit` profile shrinks to match) | Module constant set at run time. |
| Night share: submissions | `LEGIT_NIGHT_SHARE_RANGE` (0.10, 0.25) of a night-profile agent's submissions at 00:00 to 04:59 | (0.20, 0.50) | Module constant set at run time. |

**Post-processing details:**

- **Sequential gaps:** for each sequential agent, its pattern records are the longest run of its customer numbers in which neighbours (sorted) differ by at most 50. Taken in time order, they are renumbered from the run's first number, adding a gap drawn uniformly from {1, 2, 3} each time. A number already used anywhere in the dataset is skipped. The `CUST` prefix and 8 digits are kept.
- **Duplicate spread:** for each duplicate agent, its pattern records are the records of (customer, client) pairs it used at least 3 times. Each gets a new day drawn uniformly from the 60 days; the hour, minute, second and status are kept. Records that land after 30 August are removed by the standard cleaning step (`timestamp_outside_window`), as they would be by the 30-day analysis window in deployment.
- **Randomness:** both transforms use `numpy.random.default_rng(201)`.

### Evasion A (rule aware)

Every fraud agent, of every pattern, knows the duplicate rule and skips any activation that would trigger it. Records are processed in time order over the whole dataset. A fraud agent's record is **dropped** if its (customer, client) pair was already used:
- by another agent (in a record that was kept), or
- by the same agent in an earlier kept record with status `completed`.

Honest agents' records are not changed.

By construction, the rule should flag almost no fraud agent after this; that is the attack, not a finding. The test's question is how much of the fraud the model and the union still catch.

### Evasion B (feature aware)

Every `ring` and `weak_ring` agent spreads its submission times like an honest agent, so that its `time_of_day_entropy` looks honest.

- **How:** the pooled hour distribution of honest agents is the share of all honest agents' records (in the control dataset, after cleaning) in each of the 24 hours. For each ring and weak_ring agent, every record (pattern and normal alike, since the generator does not mark them) gets a new hour drawn independently from that distribution, with `numpy.random.default_rng(201)`.
- **What stays the same:** dates, minutes, seconds, customers, clients, statuses and the number of records. All other agents are not changed.
- **Side effects:**
  - Changing the hour within a day can also change `submission_frequency` (the busiest 24 hours).
  - It can change the order of an agent's same-day records, which the rule's "repeated after a completed activation" check depends on.
  - Both effects are kept, and are reported as part of the result.

## Systems compared

1. `lof_v3_4f` at the frozen cutoff 1.444799.
2. `duplicate_activation_rule` (pairs > 0).
3. Union: flagged by either.

## Metrics

Each system gets each metric on each of the four datasets:

- **PR AUC (primary).** Model: its score. Rule: its pair count. Union: its 0/1 flag, as in `stability.py`. The fraud rate (PR AUC of a random score) is reported beside it.
- **Precision and recall** at the flags above, plus the number flagged.
- **Recall by pattern:** ring, weak_ring, sequential, duplicate and weak, with the number of agents in each.
- **ROC AUC**, secondary.
- **Uncertainty:** 95% bootstrap intervals, from 2000 agent resamples of each dataset with `default_rng(0)`.
- **Feature check for Evasion B:** the mean of each of the four model features for ring and weak_ring agents, before and after the transform. Next to them, the same means for honest agents in the control dataset, including the mean `time_of_day_entropy` of honest agents. This shows whether the transform made their timing look honest. The pooled honest hour distribution used for the draw is saved with the run.

## Transform counts

The run reports, for each transform, how many agents, records and pairs it identified and how many it changed or dropped:

| Transform | Counts reported |
|---|---|
| Sequential gaps | Agents; records identified as pattern records; records renumbered |
| Duplicate spread | Agents; pairs used at least 3 times; records identified; records moved; records then outside the window and removed |
| Ring sizes, night share | Rings and ring sizes; honest agents with the night profile; their night-hour records (control against shifted) |
| Evasion A | Fraud agents, by pattern; records dropped |
| Evasion B | Ring and weak_ring agents; records given a new hour; records whose hour actually changed |

## What counts as degrading more gracefully

For each test T (shifted, Evasion A, Evasion B), and for the model (m) and the rule (r):

`drop = PR AUC on control − PR AUC on T`

`Δ = drop_r − drop_m`. Its 95% interval comes from resampling the control and T datasets independently (2000 paired draws).

| Result | Verdict |
|---|---|
| Δ > 0 and the interval excludes 0 | The model degrades more gracefully than the rule. |
| Δ < 0 and the interval excludes 0 | The rule degrades more gracefully than the model. |
| The interval includes 0 | No clear difference. |

The verdict is about the size of the drop, not about which system is better. The PR AUC level of each system on T is reported next to the verdict. If the rule falls further but still ends higher than the model, the write-up says so in those words.

For the union, recall can never be below either system's by construction, so the union is judged on what it costs in precision and on how much its PR AUC drops.

## Run once, report honestly

- Each test is run **once**. `stress_test.py` refuses to run if a `*_stress_test_s201` run folder already exists.
- Results are reported in full, including any result where the model does worse than the rule, where the model degrades more, or where a pattern's recall falls to 0.
- No setting in this file is changed after the run, and no test is repeated with other settings or seeds to get a different answer. If a mistake in the code is found after the run, the first result is kept, and both results are reported with the reason for the rerun.
- **Output:** `ml/runs/<run_id>_stress_test_s201/` holds per-agent scores and flags, the metric tables, the transform counts, the Evasion B feature check and `run_info.json` with input hashes. The generated activation records are not saved; the seed and the script reproduce them.
- **Record:** `results/STRESS_TEST_RESULTS.md` (the write-up) and an entry in `results/CHANGES.md`. The transforms read the generated labels to choose which agents to change. That is by design for a stress test, it does not touch the frozen data, and it is disclosed there.

## Known limits

- One seed and one combined shift. Recall by pattern attributes most of the effect, since each shift targets one pattern (the night share targets honest agents, so its effect shows in precision), but the shifts are not separated.
- Pattern records are identified heuristically, because the generator does not mark them. The run reports the identified counts so the heuristic can be checked.
- **Evasion B:**
  - Drawing from the pooled honest distribution matches honest agents on average, not agent by agent. A single honest agent's hours are narrower than the pool, so evading agents may end with entropy somewhat above the honest mean. The feature check shows how close they get.
  - Evasion B tests one evasion of one feature. It does not hide ring agents' customer sharing (`collusion_score`), so ring recall under Evasion B mostly reflects that feature.
- Synthetic data only, like every other result in this repository.
