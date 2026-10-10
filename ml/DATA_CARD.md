# Data card: SalesMesh synthetic activation data (v3)

**Status: FROZEN at the end of Step 1B (2026-10-11).** No further changes will be made to `ml/data_generation.py`. Every later step uses this generator unchanged. Any change would be recorded in this card and in `ml/results/CHANGES.md`.

**Generator:** `ml/data_generation.py`. The default dataset uses seed 42, 1000 agents and a fraud rate of 0.13.

**Frozen generation run:** `ml/runs/20261011-015537_datagen_s42/`, which holds:
- `run_info.json`: parameters, data file hashes, library versions, Python, OS, CPU, RAM and the git commit;
- `generation_summary.csv`;
- `rings.csv`;
- `data_checks.json`: all the checks below.

**Earlier runs, kept as superseded:**
- `20261011-004903_datagen_s42`: 6-digit customer ids.
- `20261011-005051_datagen_s42`: Step 1.
- `20261011-010944_datagen_s42`: first Step 1B pass, 600 agents.

**v2 data:** archived unchanged in `ml/data/archive_v2/`.

## Scope

This data supports one SalesMesh module: **U-CS 56, AI Fraud Detection**, which detects anomalies and flags suspicious activity. Other students own the other SalesMesh modules, and they are out of scope here:

- agent registration
- KYC
- training
- certification
- task allocation
- verification
- commission
- reputation
- analytics

The generator therefore models no client management, task volume limits, payouts or reputation. Clients exist only as a small reference list (`clients.csv`) that names which business a customer is being onboarded to.

## Limits of this data

The data is synthetic. Every pattern, rate, overlap and weight below is an assumption made by the author. The assumptions draw on the Concept Note, on Proposal Sections 2.4.1 and 2.6, and on rough 2019 census populations; none were measured from a real platform. Model results on this data show how the method behaves under these assumptions, not how it would perform on real SalesMesh agents. In particular:

- Fraud is drawn from six fixed templates.
- The hard legitimate groups cover only four kinds of overlap: night work, repeat customers, high volume, and shared popular customers.
- **The data has customer ids only.** There are no names, phone numbers or addresses. Any similarity between customer details is therefore measured on ids alone, and real near-duplicates such as the same person with a slightly different address cannot be represented.
- The difficulty of the data was set by the author, partly after seeing labelled summaries (see "Label-aware changes").

## Independent units

The unit of analysis is the **agent**, not the activation record.
- Every feature is one value per agent per analysis period.
- The label is per agent.
- Splits, cross-validation and every metric are at agent level.

The 138,756 records are not independent observations. They are nested inside 1000 agents, and ring agents also depend on each other through shared customer pools. The effective sample size is therefore at most 1000 agents, of which 130 are fraud. For fraud it is smaller still: ring members are not independent of each other, and all fraud comes from six templates.

## Why 1000 agents

Agents are the independent units, so the agent count sets how much evidence each split holds.
- The smallest splits (validation and test, 15% each) must contain at least 15 fraud agents for precision and recall to be stable enough to report. Step 5 fails otherwise.
- At 1000 agents and a 13% fraud rate there are 130 fraud agents, so about 19–20 fall in each of validation and test.
- At 600 agents there would be 78 fraud agents and only about 11–12 per split, which is below the floor.
- Adding more records per agent, or more synthetic volume in general, adds no independent evidence. It only repeats the same assumptions.
- 1000 is a round number that meets the floor with some margin, and keeps generation (about 6 s) and later repeated runs cheap.

## Time zone and observation window

- **Time zone:** all timestamps are naive local times in **Africa/Nairobi** (EAT, UTC+03:00, no daylight saving). The CSV files store them without an offset.
- **Observation window:** 2026-08-01 00:00:00 to 2026-08-30 23:59:59 local time (30 days; 31 August is not included). Seed 42 spans 2026-08-01 00:00:23 to 2026-08-30 23:58:35.
- **Registration timestamps:** 14 to 365 days before the window starts.

## Files and data dictionary

All files are in `ml/data/synthetic/`. No feature or model may read `labels.csv` or `rings.csv`. `region` is not a model feature.

**`agents.csv`** (pipeline and backend)

| Column | Type | Meaning |
|---|---|---|
| `agent_id` | string | `A` followed by 5 random digits; unique; carries no label information |
| `registration_timestamp` | datetime (Africa/Nairobi) | when the agent registered |
| `region` | string | one of Kenya's 47 counties |

**`activation_records.csv`** (pipeline and backend)

| Column | Type | Meaning |
|---|---|---|
| `record_id` | string | `R` followed by an integer, assigned in timestamp order; unique |
| `agent_id` | string | the submitting agent (foreign key to `agents.csv`) |
| `timestamp` | datetime (Africa/Nairobi) | submission time, inside the observation window |
| `customer_id` | string | `CUST` followed by 8 digits |
| `activation_status` | string | `completed`, `pending` or `failed`; independent of fraud |
| `client_id` | string | `CL01`–`CL20`, the business the customer is onboarded to (foreign key to `clients.csv`) |
| `category` | string | the client's category (one of 12) |

**`clients.csv`** (reference list)

| Column | Type | Meaning |
|---|---|---|
| `client_id` | string | `CL01`–`CL20` |
| `name` | string | `Client 01`–`Client 20`; no real brand names |
| `category` | string | banking, mobile money, insurance, SACCO, e-commerce, fashion, telecom, healthcare, education, logistics, agritech or real estate |

**`labels.csv`** (evaluation and stratified splitting only)

| Column | Type | Meaning |
|---|---|---|
| `agent_id` | string | foreign key to `agents.csv` |
| `is_fraud` | bool | ground-truth label |
| `profile` | string | legit, legit_night, legit_repeat, legit_busy, ring, weak_ring, sequential, duplicate or weak |
| `ring_id` | string | `ring_NN` for ring and weak_ring agents, empty otherwise |

**`rings.csv`** (evaluation only)

| Column | Type | Meaning |
|---|---|---|
| `ring_id` | string | `ring_NN` |
| `strength` | string | `strong` or `weak` |
| `size` | int | number of member agents |
| `pool_size` | int | number of shared customer ids |
| `hour_start` | int | first hour of the ring's window (0–23) |
| `hour_width` | int | window width in hours |
| `daily_low` | int | lowest records per active day |
| `daily_high` | int | highest records per active day |

## Parameters

Each setting is a named constant at the top of `data_generation.py`. The CLI flags are `--n-agents` (default 1000, `DEFAULT_N_AGENTS`), `--fraud-rate` (default 0.13), `--seed` (default 42) and `--out-dir`.

The number of fraud agents is `round(n_agents × fraud_rate)`. Agents are divided among the patterns by largest-remainder rounding of these shares:

| Group | Pattern | Share |
|---|---|---|
| Fraud | ring (strong) | 0.32 |
| Fraud | weak_ring | 0.16 |
| Fraud | sequential | 0.16 |
| Fraud | duplicate | 0.16 |
| Fraud | weak | 0.20 |
| Legit | legit_night | 0.08 |
| Legit | legit_repeat | 0.08 |
| Legit | legit_busy | 0.06 |
| Legit | legit (plain) | remainder |

## Generator rules

**Counties** (`COUNTY_POPULATION_THOUSANDS`, `COUNTY_MIN_AGENTS = 2`)
- Every county first gets 2 agents. The remaining agents are spread with probability proportional to rough 2019 census population.
- The resulting county list is shuffled and assigned independently of the label, so fraud cannot depend on county.
- `FORMER_PROVINCE_COUNTIES` maps counties to the 8 former regions.
- For runs too small to give every county 2 agents, the floor drops to `n_agents // 47`.

**Clients and categories** (`CLIENTS`, `CATEGORIES`)
- There are 20 clients across 12 categories. Each client has a popularity weight, from 2 to 10.
- Each agent works with 1, 2 or 3 clients, with probabilities 0.45, 0.40 and 0.15.
- The first client is drawn by weight. Each extra client comes from the first client's category with probability 0.6, when that category has another client; otherwise it is drawn from all clients.
- Each agent has its own mix over its clients (Dirichlet, α = 2). Every record draws its client from that mix, and the record's category is the client's category.
- All of this is drawn the same way for every agent, independent of the label.

**Popular customers, per county**
- Each county has a pool of `max(20, 10 × agents in the county)` popular customers.
- Each agent, legit or fraud, is a pool user with probability 0.35. A pool user sends a per-agent share of 3–15% of its normal-looking submissions to its own county's pool.

**Same customer for a different client**
- With probability 0.02, a normal-looking submission by an agent with more than one client reuses one of that agent's earlier customers for a different client.
- This is allowed but rare.

**Legitimate agents**
- They are active on a day with probability 0.85 and submit 1–8 records per active day.
- Submission hours follow a normal distribution with mean 13:00 and standard deviation 3 hours, clipped to 07:00–19:00.
- Each record goes to a fresh random customer, or a popular customer as described above.

**Hard legitimate groups**
- **`legit_night`:** a per-agent share of 10–25% of submissions falls at 00:00–04:59.
- **`legit_repeat`:** each agent has 8 regular customers. A per-agent share of 15–50% of submissions goes to them, for whichever client the record draws.
- **`legit_busy`:** 6–14 records per active day.

**Fraud agents (all patterns)**
- They are active on a day with probability 0.90.
- The pattern sets what share of their submissions is fraudulent. All other submissions look normal.

**Strong ring**
- 70% of submissions follow the pattern.
- Ring members are grouped into rings of 2–6 agents. The last ring can absorb one leftover agent.
- Each ring has its own:
  - shared pool of 20–75 customers per member, with random ids and no two consecutive numbers;
  - hour window, starting at a random hour and 2–5 hours wide;
  - daily range, with a low end of 3–8 and a width of 5–12.

**Weak ring**
- Only a per-agent share of 8–20% of submissions comes from the ring's pool.
- The pool is small, at 5–15 customers per member.
- Daily volume is legit-like: the low end is 1–3 and the width is 5–8.

**Sequential**
- 70% of submissions follow the pattern, using incrementing customer ids.
- They are submitted at 00:00–04:59, at 6–18 records per active day.

**Duplicate**
- 70% of submissions follow the pattern. They resubmit the same customer for the same client, drawn from a personal pool of 25 (customer, client) pairs.
- They are submitted at 04:00–07:59, at 5–15 records per active day.

**Weak**
- Only a per-agent share of 10–25% of submissions follows the pattern, reusing a personal pool of 10 (customer, client) pairs.
- Pattern submissions fall at 04:00–07:59.
- Volume is 2–9 records per active day.

**Identifiers**
- **Agent ids** are random.
- **Registration dates** are drawn from one distribution for every agent.
- **Record ids** follow timestamp order.

## Counts (seed 42, frozen run)

1000 agents: 130 fraud (13.0%) and 870 legitimate. 138,756 activation records and 124,170 distinct customers. Fraud agents produce 22.1% of records.

| Class | Pattern | Agents | Records | Records per agent, mean (min–max) |
|---|---|---|---|---|
| fraud | ring (strong) | 41 | 11,652 | 284.2 (214–422) |
| fraud | weak_ring | 21 | 2,798 | 133.2 (74–223) |
| fraud | sequential | 21 | 6,566 | 312.7 (258–371) |
| fraud | duplicate | 21 | 5,787 | 275.6 (238–304) |
| fraud | weak | 26 | 3,920 | 150.8 (135–186) |
| legit | legit | 679 | 78,491 | 115.6 (69–173) |
| legit | legit_night | 70 | 8,105 | 115.8 (73–147) |
| legit | legit_repeat | 69 | 7,873 | 114.1 (71–148) |
| legit | legit_busy | 52 | 13,564 | 260.8 (205–305) |

**Rings:** 14 rings, 9 strong and 5 weak, with 62 agents in total.

| Ring | Strength | Agents | Pool | Hours | Daily range |
|---|---|---|---|---|---|
| ring_01 | strong | 5 | 310 | 22:00–00:59 | 5–14 |
| ring_02 | strong | 4 | 212 | 23:00–01:59 | 8–19 |
| ring_03 | strong | 3 | 159 | 18:00–20:59 | 3–13 |
| ring_04 | strong | 6 | 156 | 04:00–08:59 | 5–17 |
| ring_05 | strong | 6 | 150 | 01:00–05:59 | 6–12 |
| ring_06 | strong | 6 | 198 | 14:00–15:59 | 4–16 |
| ring_07 | strong | 6 | 342 | 17:00–21:59 | 5–16 |
| ring_08 | strong | 3 | 180 | 13:00–17:59 | 5–17 |
| ring_09 | strong | 2 | 132 | 13:00–15:59 | 8–20 |
| ring_10 | weak | 3 | 24 | 14:00–18:59 | 1–6 |
| ring_11 | weak | 6 | 78 | 11:00–12:59 | 1–7 |
| ring_12 | weak | 3 | 18 | 03:00–06:59 | 3–11 |
| ring_13 | weak | 5 | 25 | 16:00–18:59 | 3–10 |
| ring_14 | weak | 4 | 36 | 11:00–14:59 | 1–8 |

10 of the 14 ring windows overlap the legitimate 07:00–19:00 working day.

**Agents per county**
- Minimum 5 (Lamu, Taita-Taveta, Tharaka-Nithi), median 20, maximum 89 (Nairobi).
- **0 counties have fewer than 5 agents.**
- **Largest counties:** Nairobi 89, Kiambu 56, Nakuru 50, Kakamega 43, Meru 32 and Bungoma 32.
- County-level results will still be too small to interpret.

**By former region**

| Former region | Agents | Fraud | Fraud rate |
|---|---|---|---|
| Central | 122 | 13 | 0.107 |
| Coast | 87 | 8 | 0.092 |
| Eastern | 148 | 21 | 0.142 |
| Nairobi | 89 | 9 | 0.101 |
| North Eastern | 51 | 4 | 0.078 |
| Nyanza | 115 | 16 | 0.139 |
| Rift Valley | 276 | 38 | 0.138 |
| Western | 112 | 21 | 0.188 |

**By primary category** (the category with most of the agent's activations)

| Primary category | Agents | Fraud | Fraud rate |
|---|---|---|---|
| mobile money | 182 | 20 | 0.110 |
| banking | 162 | 25 | 0.154 |
| telecom | 156 | 14 | 0.090 |
| e-commerce | 116 | 16 | 0.138 |
| insurance | 85 | 10 | 0.118 |
| SACCO | 85 | 10 | 0.118 |
| agritech | 58 | 9 | 0.155 |
| education | 57 | 8 | 0.140 |
| fashion | 32 | 7 | 0.219 |
| healthcare | 28 | 3 | 0.107 |
| logistics | 20 | 3 | 0.150 |
| real estate | 19 | 5 | 0.263 |

The rate differences between groups are sampling noise from random assignment. None of the chi-square tests below is significant.

**Clients and categories per agent**

| Count | Agents with that many clients | Agents with that many categories |
|---|---|---|
| 1 | 450 | 674 |
| 2 | 412 | 294 |
| 3 | 138 | 32 |

## Checks on the generated data

These checks come from the frozen run (`data_checks.json`) and are covered by `ml/tests/test_data_generation.py`, which has 30 tests.

**Fraud is independent of region, category and client**

Chi-square tests at agent level, fraud vs:

| Grouping | p |
|---|---|
| County (47 groups; many small cells, indicative only) | 0.649 |
| Former region (8) | 0.403 |
| Primary category (12) | 0.547 |
| Primary client (20) | 0.702 |

The tests are run at agent level because records are not independent.

**Identifiers carry no label**

| Field | Test | p |
|---|---|---|
| Agent id number | Mann-Whitney | 0.286 |
| Registration date | Kolmogorov-Smirnov | 0.243 |
| Record id | Mann-Whitney | 0.001 |

The record id result is not a leak. Record ids are a deterministic function of timestamp order (ties broken by agent id, then customer id), so they carry no information beyond the timestamp. Fraud agents submit at different hours, which is what the test picks up. Record ids must not be used as a feature.

**Determinism:** the same seed gives byte-identical frames, and a different seed gives different data.

**`sequential_score` by pattern**
- Every pattern except sequential has a maximum of 0.000.
- Sequential agents average 0.707 (max 0.744).

**`collusion_score` by group**

| Group | Agents | Min | Median | Max | Non-zero |
|---|---|---|---|---|---|
| Legitimate | 870 | 0.000 | 0.000 | 0.074 | 359 |
| Strong ring | 41 | 0.387 | 0.590 | 0.674 | 41 |
| Weak ring | 21 | 0.056 | 0.094 | 0.125 | 21 |
| Other fraud | 68 | 0.000 | 0.000 | 0.061 | 33 |

- 4 of the 21 weak-ring agents score at or below the highest legitimate agent.
- No legitimate agent reaches the lowest strong-ring score.

**Duplicates and cross-client repeats**
- More than 90% of the duplicate pattern's resubmitted customers stay with one client.
- 2,150 (agent, customer) pairs involve more than one client. That is under 5% of pairs, which counts as rare.

## Planned feature definitions (implemented in Step 4)

These definitions are fixed now, before any model is run. They are recorded here because they decide how the data is read.

**Analysis period**
- Every feature function takes `period_start` and `period_end` arguments.
- Every output row carries `analysis_period_start` and `analysis_period_end`.
- Model comparison uses one row per agent, for the whole observation window, split at agent level.

**`submission_frequency`**
- The agent's submission count in its busiest 24-hour sliding window inside the period: the maximum, over all start times t, of submissions in [t, t + 24 h).
- The window length is a named constant (`SUBMISSION_WINDOW_HOURS = 24`).

**`customer_similarity`**
- The mean pairwise similarity of the agent's customer identifiers, taken over all unordered pairs of the agent's submissions in the period.
- The similarity of two ids is the fraction of the 8 digit positions that match. Identical ids score 1, ids from one sequential run share their leading digits, and two random ids score about 0.1.
- **To confirm against the wording in Chapter 3 before Step 4.**

**`time_of_day_entropy`**
- Normalised Shannon entropy of submission hours. The current column name is `time_of_day_dist`.

**`collusion_score`**
- The fraction of the agent's distinct customers that also appear in any other agent's records in the period.
- It uses other agents' customers and no labels.

**`volume_vs_peers`** (fifth candidate)
- The agent's submission volume divided by the median volume of its peers.
- Peers are agents with the same primary category in the same former region.
- If that group has fewer than `PEER_MIN_GROUP = 15` agents, peers are the same category across all regions. If that is still fewer than 15, peers are all agents.
- It is kept only if it passes the same checks as the other four features.
- Models with and without it are compared on validation only, and both results are reported.

## Requirements traceability

SRS rows are limited to the sections named by the author. Other rows are the fraud behaviours described in Chapters 1–3, which have no SRS section number.

| Source | Requirement | Generator pattern | Feature | Known limitation |
|---|---|---|---|---|
| SRS 2.2.4 | Quality scoring and anomaly detection | All fraud patterns and hard legitimate groups | All features → one anomaly score per agent | Scores are not calibrated probabilities; synthetic data only |
| SRS 7.5 | Detect anomalies | All fraud patterns | All features | Fraud comes from six templates only |
| SRS 7.5 | Flag collusion | ring, weak_ring; honest sharing through county popular pools | `collusion_score` | Strong rings are easy to separate; weak rings only partly hidden (4 of 21 inside the legitimate range) |
| SRS 7.5 | Flag fake activations | sequential, duplicate, weak | `customer_similarity`, `submission_frequency` | Customer ids only, no names or addresses |
| SRS 7.5 | Admin review of flagged events | Labels kept separate, for evaluation only | Top contributing features per flagged agent (Step 10) | The review workflow is in the backend; this module supplies scores and reasons |
| SRS 3.6 | Flag suspicious or low-quality onboardings | All fraud patterns; `activation_status` independent of fraud | All features | Low quality is not modelled separately from fraud |
| SRS 3.1, 8.4 | Categories; benchmarking across categories and clients | `clients.csv` (20 clients, 12 categories); agents with 1–3 clients | `volume_vs_peers` (peers by category and former region) | Benchmarking covers volume only; category and client are independent of fraud by design |
| SRS 4.3, 8.2 | AI decisions and scoring outcomes logged | – | Every score output carries `agent_id`, `analysis_period`, `score`, `flag`, `threshold`, `model_version`, `top_features` (Step 9 criterion) | Storage and logging are done by the backend |
| SRS 5.1 | Near real time | – | Scoring time per agent and for the whole table (Steps 9 and 11) | Scoring is per analysis period, not streaming |
| SRS 5.3 | Growth in the number of agents and clients | `--n-agents`; the client list is a constant | Scoring time at 500, 1000, 5000 and 10000 agents (timing only) | The client count is fixed at 20 in the generator |
| SRS section 2 (constraints) | AI models auditable and configurable | Seeds, named constants, `run_info.json` with hashes | Threshold as a config value; versioned models | – |
| SRS section 2 (constraints) | Multi-region | 47 counties, 8 former regions | Region is used only for `volume_vs_peers` peer groups, not as a feature | County-level results are too small to interpret |
| Chapters 1–3 | Fake or duplicate activations | duplicate, weak (same customer for the same client) | `customer_similarity` | Ids only |
| Chapters 1–3 | Repeated or sequential customer details | sequential, duplicate; legit_repeat (hard legitimate case) | `customer_similarity` | Ids only; repeat customers also occur legitimately |
| Chapters 1–3 | Odd timing and volume | sequential (night), duplicate and weak (early morning), ring hour windows; legit_night and legit_busy (hard legitimate cases) | `time_of_day_entropy`, `submission_frequency`, `volume_vs_peers` | Entropy measures how spread out the hours are, not when they fall |
| Chapters 1–3 | Multiple accounts working together | ring, weak_ring | `collusion_score` | Ring members' counties are independent, so rings are not local |

## Label-aware changes, in order

These changes to the generator were made after seeing labelled summaries. None involved a model, a split or a test set.

1. **v2, before this rework.** A feature review showed that `customer_similarity` separated the classes perfectly, so the legitimate repeat-customer share was widened.
2. **v3 Step 1.** A per-pattern review showed legitimate `collusion_score` up to 0.17, caused by chance collisions between 6-digit customer ids. Customer ids were widened to 8 digits.
3. **v3 Step 1B, first pass (a realism change).** A per-pattern review showed that `collusion_score` separated rings from all legitimate agents perfectly (rings 0.43–0.67, legitimate agents at most 0.016). Two things were added:
   - per-county popular customers, used by legitimate and fraud agents on the same terms;
   - weak rings.

   The weak-ring parameters were set once and not re-tuned after their scores were seen (0.043–0.173 at 600 agents).

**Changes made without looking at labels, from the author's specification:**
- 47 counties instead of 5 cities (realism);
- 1000 agents;
- a county floor of 2;
- a client and category reference list, with 1–3 clients per agent;
- the duplicate pattern defined as the same customer for the same client;
- rare same-customer, different-client repeats.

## Known issues and caveats

1. **The generator was changed after seeing labels.** See the three changes above.
2. **`collusion_score` uses all agents, including test agents.** No labels are used, but the partitions are not independent at the feature level.
3. **The earlier (v2) deployment choice used test results.** v2 had no validation set, so switching the live detector to Isolation Forest v2 was decided after seeing test results.
4. **Strong rings remain separable on `collusion_score` alone** (0.387 vs at most 0.074).
5. **Weak fraud and weak rings are deliberately close to legitimate agents.** Low recall on them is the expected result.
6. **The backend database still holds v2 data.** One backend test (`test_agent_detail_context_lists_only_known_clients_and_categories`) fails until the database is reloaded with this data. The API tests also hard-code agent `A1104`, which does not exist in v3.
7. **Derived files in `ml/data/synthetic/` are out of date until Steps 2–5 regenerate them.** These are `activation_records_clean.csv`, `feature_vectors.csv`, `train_test_split.csv` and `fraud_flags*.csv`.
