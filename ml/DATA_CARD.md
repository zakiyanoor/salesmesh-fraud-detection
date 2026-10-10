# Data card: SalesMesh synthetic activation data (v3)

**Status: FROZEN for good after label-aware change #4 (Step 1C, 2026-10-11).** This was the last change to `ml/data_generation.py`. The generator will not be changed again, whatever the models show. Every later step uses it unchanged.

**Generator:** `ml/data_generation.py`. The default dataset uses seed 42, 1000 agents and a fraud rate of 0.13.

**Frozen generation run:** `ml/runs/20261011-022249_datagen_s42/`, which holds:
- `run_info.json`: parameters, data file hashes, library versions, Python, OS, CPU, RAM and the git commit;
- `generation_summary.csv`;
- `rings.csv`;
- `data_checks.json`;
- `overlap_audit.csv`;
- `raw_descriptors_by_agent.csv`.

**Earlier generation runs, kept as superseded:**
- `20261011-004903_datagen_s42`: 6-digit customer ids.
- `20261011-005051_datagen_s42`: Step 1.
- `20261011-010944_datagen_s42`: first Step 1B pass, 600 agents.
- `20261011-015537_datagen_s42`: Step 1B, before change #4.
- `20261011-022151_datagen_s42`: change #4, first pass, before the fixed per-class pool sizes and pattern shares were randomised.

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
- **The data has customer ids only.** There are no names, phone numbers or addresses. Similarity between customer details is therefore measured on identifiers alone.
- The difficulty of the data was set by the author, in four changes made after seeing labelled summaries (see "Label-aware changes").
- Three fraud signatures separate their group from all legitimate agents on a single descriptor (see "Accepted separations").

## Independent units

The unit of analysis is the **agent**, not the activation record.
- Every feature is one value per agent per analysis period.
- The label is per agent.
- Splits, cross-validation and every metric are at agent level.

The 135,509 records are not independent observations. They are nested inside 1000 agents, and ring agents also depend on each other through shared customer pools. The effective sample size is therefore at most 1000 agents, of which 130 are fraud. For fraud it is smaller still: ring members are not independent of each other, and all fraud comes from six templates.

## Why 1000 agents

Agents are the independent units, so the agent count sets how much evidence each split holds.
- The smallest splits (validation and test, 15% each) must contain at least 15 fraud agents for precision and recall to be stable enough to report. Step 5 fails otherwise.
- At 1000 agents and a 13% fraud rate there are 130 fraud agents, so about 19–20 fall in each of validation and test.
- At 600 agents there would be 78 fraud agents and only about 11–12 per split, which is below the floor.
- Adding more records per agent, or more synthetic volume in general, adds no independent evidence. It only repeats the same assumptions.

## Time zone and observation window

- **Time zone:** all timestamps are naive local times in **Africa/Nairobi** (EAT, UTC+03:00, no daylight saving). The CSV files store them without an offset.
- **Observation window:** 2026-08-01 00:00:00 to 2026-08-30 23:59:59 local time (30 days; 31 August is not included). Seed 42 spans 2026-08-01 00:01:04 to 2026-08-30 23:57:49.
- **Registration timestamps:** 14 to 365 days before the window starts.

## Files and data dictionary

All files are in `ml/data/synthetic/`. No feature or model may read `labels.csv` or `rings.csv`. `region` is not a model feature. Record, activation, agent and other id columns are never model inputs; `ml/tests/test_no_id_inputs.py` enforces this.

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
| `daily_median` | float | the ring's median daily rate (each member's rate is drawn around it) |

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

### Common to every agent, legit or fraud

**County** (`COUNTY_POPULATION_THOUSANDS`, `COUNTY_MIN_AGENTS = 2`)
- Every county first gets 2 agents. The remaining agents are spread with probability proportional to rough 2019 census population.
- The resulting county list is shuffled and assigned independently of the label.
- `FORMER_PROVINCE_COUNTIES` maps counties to the 8 former regions.

**Clients** (`CLIENTS`, `CATEGORIES`)
- There are 20 clients across 12 categories, each with a popularity weight from 2 to 10.
- Each agent works with 1, 2 or 3 clients, with probabilities 0.45, 0.40 and 0.15. Each extra client comes from the first client's category with probability 0.6.
- Each agent has its own mix over its clients (Dirichlet, α = 2). The record's category is its client's category.

**Activity**
- Each agent has its own active-day probability, drawn from 0.75–0.95.
- **Daily count:** on an active day, the count is drawn from a negative binomial with dispersion 3. Its mean is the agent's rate, `group median × lognormal(0, 0.25)`. The distribution has a heavy right tail and no cap.

**Normal hours**
- Each agent sends a per-agent share of 1–6% of its normal submissions to a uniformly random hour (0–23).
- All other normal submissions come from Normal(13:00, 3 h), resampled until the hour falls inside 0–23. There is no clipping.

**Other common rules**
- **Popular customers:** each county has a pool of `max(20, 10 × agents in the county)` customers. Each agent is a pool user with probability 0.35. A pool user sends a share of 3–15% of its normal submissions to its own county's pool.
- **Same customer for a different client:** with probability 0.02, a normal submission by an agent with more than one client reuses one of that agent's earlier customers for a different client.
- **Status and registration:** the same distributions for every agent.

### Group medians and pattern rules

| Group | Daily median | Pattern |
|---|---|---|
| legit (plain) | 4.5 | – |
| legit_night | 4.5 | 10–25% of submissions at 00:00–04:59 |
| legit_repeat | 4.5 | 4–12 regular customers; 15–50% of submissions go to them |
| legit_busy | 10 | – |
| ring (strong) | per ring 5–12 | 55–85% of submissions from a shared pool (20–75 customers per member, no consecutive ids), inside the ring's own window of 2–5 hours; ring size 2–6 |
| weak_ring | per ring 2.5–5 | 8–20% of submissions from a small shared pool (5–15 customers per member) |
| sequential | 12 | 55–85% of submissions use incrementing customer ids, at 00:00–04:59 |
| duplicate | 10 | 55–85% of submissions resubmit the same customer for the same client, from a personal pool of 15–35 (customer, client) pairs, at 04:00–07:59 |
| weak | 4.5 × 1.15–1.6 (random per agent) | 10–25% of submissions reuse a personal pool of 5–15 (customer, client) pairs, at 04:00–07:59 |

## Counts (seed 42, frozen run)

1000 agents: 130 fraud (13.0%) and 870 legitimate. 135,509 activation records and 123,505 distinct customers. Fraud agents produce 19.5% of records.

| Class | Pattern | Agents | Records | Records per agent, mean (min–max) |
|---|---|---|---|---|
| fraud | ring (strong) | 41 | 8,522 | 207.9 (85–398) |
| fraud | weak_ring | 21 | 2,038 | 97.0 (41–149) |
| fraud | sequential | 21 | 6,337 | 301.8 (188–692) |
| fraud | duplicate | 21 | 5,379 | 256.1 (105–402) |
| fraud | weak | 26 | 4,176 | 160.6 (107–228) |
| legit | legit | 679 | 79,241 | 116.7 (35–315) |
| legit | legit_night | 70 | 8,308 | 118.7 (57–246) |
| legit | legit_repeat | 69 | 7,971 | 115.5 (58–215) |
| legit | legit_busy | 52 | 13,537 | 260.3 (122–437) |

**Rings:** 14 rings, 9 strong and 5 weak, with 62 agents in total.

| Ring | Strength | Agents | Pool | Hours | Daily median |
|---|---|---|---|---|---|
| ring_01 | strong | 5 | 310 | 22:00–00:59 | 7.09 |
| ring_02 | strong | 4 | 212 | 23:00–01:59 | 10.00 |
| ring_03 | strong | 3 | 159 | 18:00–20:59 | 5.74 |
| ring_04 | strong | 6 | 258 | 14:00–15:59 | 10.76 |
| ring_05 | strong | 6 | 282 | 13:00–14:59 | 6.03 |
| ring_06 | strong | 6 | 282 | 04:00–08:59 | 5.65 |
| ring_07 | strong | 6 | 144 | 11:00–15:59 | 6.50 |
| ring_08 | strong | 3 | 159 | 12:00–15:59 | 9.12 |
| ring_09 | strong | 2 | 120 | 13:00–17:59 | 9.09 |
| ring_10 | weak | 5 | 60 | 04:00–05:59 | 2.82 |
| ring_11 | weak | 5 | 60 | 15:00–16:59 | 4.24 |
| ring_12 | weak | 3 | 39 | 11:00–12:59 | 4.37 |
| ring_13 | weak | 3 | 33 | 03:00–04:59 | 4.00 |
| ring_14 | weak | 5 | 45 | 01:00–03:59 | 3.42 |

**Agents per county**
- Minimum 5 (Lamu, Taita-Taveta, Tharaka-Nithi), median 20, maximum 89 (Nairobi).
- **0 counties have fewer than 5 agents.**
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
| mobile money | 184 | 22 | 0.120 |
| banking | 161 | 25 | 0.155 |
| telecom | 157 | 18 | 0.115 |
| e-commerce | 114 | 13 | 0.114 |
| insurance | 88 | 11 | 0.125 |
| SACCO | 85 | 10 | 0.118 |
| agritech | 57 | 8 | 0.140 |
| education | 57 | 9 | 0.158 |
| fashion | 30 | 5 | 0.167 |
| healthcare | 24 | 4 | 0.167 |
| real estate | 22 | 4 | 0.182 |
| logistics | 21 | 1 | 0.048 |

The rate differences between groups are sampling noise. None of the chi-square tests below is significant.

**Clients and categories per agent**

| Count | Agents with that many clients | Agents with that many categories |
|---|---|---|
| 1 | 450 | 674 |
| 2 | 413 | 294 |
| 3 | 137 | 32 |

**Share of records at 00:00–04:59, by pattern:**

| Pattern | Share |
|---|---|
| sequential | 0.714 |
| legit_night | 0.178 |
| duplicate | 0.174 |
| ring | 0.118 |
| weak_ring | 0.072 |
| weak | 0.056 |
| legit, legit_repeat, legit_busy | 0.011 each |

## Checks on the generated data

These checks come from the frozen run and are covered by `ml/tests/test_data_generation.py`, which has 34 tests.

**Fraud is independent of region, category and client**

Chi-square tests at agent level, fraud vs:

| Grouping | p |
|---|---|
| County (47 groups; many small cells, indicative only) | 0.649 |
| Former region (8) | 0.403 |
| Primary category (12) | 0.946 |
| Primary client (20) | 0.821 |

**Identifiers carry no label**

| Field | Test | p |
|---|---|---|
| Agent id number | Mann-Whitney | 0.286 |
| Registration date | Kolmogorov-Smirnov | 0.243 |
| Record id | Mann-Whitney | 0.938 |

**Determinism:** the same seed gives byte-identical frames, and a different seed gives different data.

**`sequential_score` by pattern**
- Every pattern except sequential has a maximum of 0.000.
- Sequential agents average 0.716 (max 0.843).

**`collusion_score` by group**

| Group | Agents | Min | Median | Max | Non-zero |
|---|---|---|---|---|---|
| Legitimate | 870 | 0.000 | 0.000 | 0.110 | 353 |
| Strong ring | 41 | 0.340 | 0.611 | 0.760 | 41 |
| Weak ring | 21 | 0.032 | 0.074 | 0.149 | 21 |
| Other fraud | 68 | 0.000 | 0.000 | 0.045 | 32 |

- 15 of the 21 weak-ring agents score at or below the highest legitimate agent.
- No legitimate agent reaches the lowest strong-ring score.

**Duplicates and cross-client repeats**
- More than 90% of the duplicate pattern's resubmitted customers stay with one client.
- 1,848 (agent, customer) pairs involve more than one client, under 5% of pairs.

## Overlap audit (before the final freeze)

Every raw per-agent descriptor is compared between legitimate agents (all four legitimate groups, 870 agents) and each fraud pattern. Each cell is min / median / max.
- **"No overlap"** marks a fraud group whose whole range lies outside the legitimate range.
- **"x% outside"** is the share of that group's agents outside the legitimate range.

Source: `overlap_audit.csv` in the frozen run, built by `data_checks.overlap_audit`. The test `test_only_accepted_signatures_have_zero_overlap_with_legit` fails if any other zero-overlap row appears.

| Descriptor | legit | ring | weak_ring | sequential | duplicate | weak |
|---|---|---|---|---|---|---|
| Submissions in window | 35 / 116 / 437 | 85 / 201 / 398 | 41 / 97 / 149 | 188 / 244 / 692 (14% outside) | 105 / 236 / 402 | 107 / 160 / 228 |
| Max submissions in one day | 5 / 13 / 48 | 10 / 21 / 54 (2% outside) | 4 / 11 / 23 (5% outside) | 18 / 26 / 54 (10% outside) | 10 / 26 / 48 | 10 / 17 / 25 |
| Mean submissions per active day | 2.29 / 4.78 / 16.8 | 3.96 / 7.73 / 14.7 | 2.52 / 4.09 / 6.55 | 7.52 / 10.4 / 23.9 (14% outside) | 5 / 9.2 / 16.4 | 4.89 / 6.75 / 8.14 |
| Distinct hours used | 12 / 17 / 24 | 10 / 15 / 21 (5% outside) | 13 / 16 / 20 | 15 / 20 / 23 | 14 / 17 / 21 | 16 / 18 / 21 |
| Share of submissions 00:00–04:59 | 0 / 0.0108 / 0.319 | 0 / 0.0092 / 0.551 (10% outside) | 0 / 0.0794 / 0.208 | **0.548 / 0.727 / 0.85 (no overlap)** | 0.118 / 0.172 / 0.229 | 0.0256 / 0.0515 / 0.105 |
| Hour-of-day entropy (0–1) | 0.686 / 0.787 / 0.902 | 0.418 / 0.608 / 0.773 (73% outside) | 0.716 / 0.782 / 0.858 | 0.677 / 0.76 / 0.84 (19% outside) | 0.589 / 0.721 / 0.812 (19% outside) | 0.801 / 0.837 / 0.863 |
| Share of submissions on Sat/Sun | 0.11 / 0.333 / 0.57 | 0.201 / 0.35 / 0.441 | 0.15 / 0.328 / 0.512 | 0.165 / 0.333 / 0.444 | 0.216 / 0.326 / 0.416 | 0.166 / 0.309 / 0.505 |
| Distinct customers per client | 17.7 / 74.5 / 437 | 33.7 / 99 / 260 | 20.5 / 59 / 132 | 73.3 / 152 / 358 | 24 / 62.5 / 174 | 39.3 / 100 / 200 |
| Share repeating an earlier customer+client | 0 / 0 / 0.45 | 0.0278 / 0.143 / 0.341 | 0 / 0.0149 / 0.0556 | 0 / 0 / 0.0093 | 0.407 / 0.562 / 0.791 (86% outside) | 0.0148 / 0.114 / 0.216 |
| Clients per agent | 1 / 2 / 3 | 1 / 2 / 3 | 1 / 2 / 3 | 1 / 2 / 3 | 1 / 2 / 3 | 1 / 1.5 / 3 |
| Registration age (days) | 14 / 188 / 364 | 18 / 156 / 362 | 38 / 234 / 356 | 15 / 168 / 354 | 30 / 272 / 345 | 15 / 196 / 352 |
| Share of completed activations | 0.714 / 0.853 / 0.969 | 0.789 / 0.849 / 0.905 | 0.807 / 0.854 / 0.914 | 0.82 / 0.85 / 0.891 | 0.788 / 0.857 / 0.895 | 0.802 / 0.849 / 0.912 |
| Collusion score | 0 / 0 / 0.11 | **0.34 / 0.611 / 0.76 (no overlap)** | 0.0317 / 0.0741 / 0.149 (29% outside) | 0 / 0 / 0.0233 | 0 / 0 / 0.0444 | 0 / 0.003 / 0.0448 |
| Customer similarity (identifiers) | 0.0966 / 0.102 / 0.151 | 0.0989 / 0.103 / 0.108 | 0.098 / 0.102 / 0.105 | **0.281 / 0.404 / 0.52 (no overlap)** | 0.11 / 0.116 / 0.134 | 0.101 / 0.104 / 0.112 |

### Accepted separations (realistic fraud signatures, kept as known limitations)

Each of these follows from what the fraud pattern is, not from a limit placed on legitimate agents.

| Descriptor | Group | Separation | Why it is accepted |
|---|---|---|---|
| Collusion score | strong ring | none of the 41 overlap legitimate (0.34–0.76 vs at most 0.11) | A ring is defined by many accounts sharing a customer pool. Honest sharing exists (county popular customers) but stays small. Accepted by the author. |
| Customer similarity | sequential | none of the 21 overlap (0.28–0.52 vs at most 0.15) | Fabricated incrementing identifiers share their leading digits. That is the pattern itself. |
| Night share (00:00–04:59) | sequential | none of the 21 overlap (0.55–0.85 vs at most 0.32) | The pattern defines scripted night batches (55–85% of submissions). Even the lowest pattern share would exceed the busiest honest night worker. |
| Repeat share | duplicate | 86% outside | Resubmitting the same customer for the same client is the pattern. `legit_repeat` overlaps the lower end. |
| Hour entropy | strong ring | 73% outside | Coordinated rings submit inside a 2–5 hour window. |
| Collusion score | weak ring | 29% outside | 15 of 21 weak-ring agents are inside the legitimate range, by design. |

### Hard limits and exact values checked in the generator

| Constant (before change #4) | Applied to | Kind | Change #4 |
|---|---|---|---|
| Normal hours `clip(Normal(13, 3), 7, 19)` | normal submissions of all agents; legitimate agents had nothing else | clip (artefact: no legitimate agent at 05–06 or 20–23) | Fixed: resampling instead of clipping, and a 1–6% per-agent share at any hour |
| Legitimate daily count uniform 1–8 (busy 6–14) | legitimate only | hard cap (artefact: no non-busy legitimate agent above 8 per day) | Fixed: negative binomial around an agent rate, for every group |
| Weak fraud daily count uniform 2–9 | weak only | cap and exact value (every busiest day was 9) | Fixed: rate = 4.5 × 1.15–1.6 per agent; busiest days now 10–25 |
| Pattern daily ranges (ring, sequential, duplicate) | fraud only | caps | Fixed: same negative binomial mechanism, with group medians |
| Active-day probability 0.85 (legitimate) vs 0.90 (fraud) | class-specific constants | exact value per class | Fixed: 0.75–0.95 per agent, for every agent |
| Pattern share fixed at 0.70 (ring, sequential, duplicate) | fraud only | exact value | Fixed: 0.55–0.85 per agent |
| Duplicate pool 25, weak pool 10, `legit_repeat` pool 8 | one group each | exact values | Fixed: 15–35, 5–15 and 4–12 per agent |
| Pattern hour windows (00:00–04:59, 04:00–07:59, ring windows) | fraud patterns and `legit_night` | pattern definitions | Kept: they define the signatures. Legitimate agents now have activity at every hour |
| Hour range 0–23 | all agents | physical bound | Kept |

## Split (Step 5)

The split is done at agent level: 70% train, 15% validation and 15% test.
- **Seed:** `SPLIT_SEED = 42`, a constant in `split.py`.
- **Stratification:** by pattern (legit plus the five fraud patterns), so every split holds every pattern. Labels are used only to stratify.
- **Safety check:** the split fails if validation or test has fewer than 15 fraud agents.
- **Saved to:** run `ml/runs/20261011-023607_split_s42/split.csv` (`agent_id`, `split`), with a copy at `data/synthetic/split.csv`.

| | Train | Validation | Test |
|---|---|---|---|
| Agents | 700 | 150 | 150 |
| Fraud agents (share) | 91 (0.130) | 20 (0.133) | 19 (0.127) |
| ring | 29 | 6 | 6 |
| weak_ring | 14 | 4 | 3 |
| sequential | 15 | 3 | 3 |
| duplicate | 15 | 3 | 3 |
| weak | 18 | 4 | 4 |
| legit (plain) | 475 | 107 | 97 |
| legit_night | 50 | 7 | 13 |
| legit_repeat | 51 | 8 | 10 |
| legit_busy | 33 | 8 | 11 |

The hard legitimate groups are not strata, so they are spread less evenly than the fraud patterns.

**Rings can span splits.** 13 of the 14 rings have members in more than one split; for example, `ring_05` has 4 members in train, 1 in validation and 1 in test.

This is not label leakage. No model is trained on labels, so nothing about a ring's label is learned from its training members.

Two features are platform-wide: `collusion_score` and `volume_vs_peers`. `collusion_score` needs other agents' records, and it is computed from customer overlap across all agents on the platform in the period, whatever their split. `volume_vs_peers` compares the agent with all agents' volumes in the same way. **This is how the features work in deployment:** the live system sees every agent's activity for the period. As a result, a test agent's `collusion_score` reflects its ring partners in train. The features use no labels.

## Feature definitions (Step 4)

These are implemented in `feature_engineering.py`, without labels or splits.

**Analysis period:** `compute_feature_vectors(activations, agents, period_start, period_end)` uses records with `period_start <= timestamp < period_end`. The default is [2026-08-01 00:00, 2026-08-31 00:00) Africa/Nairobi. Every output row carries `analysis_period_start` and `analysis_period_end`.

The output has one row per agent. Model comparison uses this one row per agent, and the split is at agent level.

Notation for agent *a* in the period:
- *T_a* is its submission timestamps.
- *C_a* is its set of distinct customer ids.
- *V_a* = |*T_a*| is its volume, in submissions.

| Feature | Formula | Window / parameters | Units, range |
|---|---|---|---|
| `submission_frequency` | max over t of \|{ s in T_a : t <= s < t + 24 h }\| | Sliding window `SUBMISSION_WINDOW_HOURS = 24`, chosen before any model run. The maximum is reached by a window starting at a submission. | submissions per 24 h; integer >= 0 |
| `time_of_day_entropy` | -sum_h p_h log2 p_h / log2 24, where p_h is the share of T_a in hour h (0–23) | whole period | unitless, 0 (one hour) to 1 (even over 24 hours); 0 when there are no submissions |
| `customer_similarity` (similarity of identifiers) | sum over i < j of (1/8) sum_k [digit_k(i) = digit_k(j)], divided by n(n - 1)/2, over all n submissions | whole period; the 8 digits of the customer id | unitless, 0–1; about 0.1 for random ids, 1 for identical ids; 0 when n < 2 |
| `collusion_score` | \|{ c in C_a : c in C_b for some other agent b }\| / \|C_a\| | whole period; platform-wide | unitless, 0–1 |
| `volume_vs_peers` | V_a / max(1, median{ V_b : b in P(a), b != a }) | whole period. P(a) is the agents with the same primary category (the most frequent category in the period, ties broken alphabetically) and the same former region. If that group, the agent included, has fewer than `PEER_MIN_GROUP = 15` agents, P(a) is the same category in all regions; if that is still fewer than 15, all agents. | ratio, unitless; 1 = the peers' median |

The model input is `FEATURE_COLUMNS`, the five features above. Id columns, `volume` and `peer_group` are never inputs; `test_no_id_inputs.py` enforces this.

**Peer group levels used:** 578 agents got category + former region, and 422 got category only. No agent fell back to all agents.

**Hand-calculated tests:** `ml/tests/test_feature_engineering.py`.

## Single-feature AUC on training agents (Step 4)

The table uses the 700 training agents, 91 of them fraud. Validation and test labels were not read.

Each cell is a ROC AUC, with the feature value used as the score (higher = more suspicious); values below 0.5 mean the feature is lower for fraud. Columns compare the named fraud agents against all training legitimate agents.

Source: run `ml/runs/20261011-023802_feature_checks/`.

| Feature | All fraud | ring | weak_ring | sequential | duplicate | weak |
|---|---|---|---|---|---|---|
| `submission_frequency` | 0.764 | 0.811 | 0.336 | **0.951** | 0.912 | 0.743 |
| `time_of_day_entropy` | 0.321 | **0.017** | 0.460 | 0.326 | 0.092 | 0.892 |
| `customer_similarity` | 0.788 | 0.747 | 0.460 | **1.000** | **0.965** | 0.784 |
| `collusion_score` | 0.724 | **1.000** | **0.971** | 0.404 | 0.473 | 0.564 |
| `volume_vs_peers` | 0.780 | 0.831 | 0.300 | **0.964** | 0.929 | 0.794 |

**Near-perfect single features (separation = max(AUC, 1 - AUC) >= 0.95), listed as shortcut-risk limitations:**
- **ring:** `collusion_score` 1.000 and `time_of_day_entropy` 0.983 (lower for fraud).
- **weak_ring:** `collusion_score` 0.971. Weak-ring agents score low in absolute terms, but most legitimate agents score exactly 0.
- **sequential:** `customer_similarity` 1.000, `volume_vs_peers` 0.964 and `submission_frequency` 0.951.
- **duplicate:** `customer_similarity` 0.965.
- **weak:** no feature is near-perfect. The best is `time_of_day_entropy` at 0.892.

**Decision rule for `volume_vs_peers`** (written to `decision_rule.md` before the AUC table was computed): keep it only if its training AUC (all fraud) is above 0.55 and its absolute Spearman correlation with every base feature is at most 0.85.

**Result: KEEP.** Its AUC is 0.780, and its highest correlation is 0.807, with `submission_frequency`. That correlation is close to the limit: the two features largely measure volume twice. Step 9 still compares models with and without it, on validation only.

## Requirements traceability

SRS rows are limited to the sections named by the author. Other rows are the fraud behaviours described in Chapters 1–3, which have no SRS section number.

| Source | Requirement | Generator pattern | Feature | Known limitation |
|---|---|---|---|---|
| SRS 2.2.4 | Quality scoring and anomaly detection | All fraud patterns and hard legitimate groups | All features → one anomaly score per agent | Scores are not calibrated probabilities; synthetic data only |
| SRS 7.5 | Detect anomalies | All fraud patterns | All features | Fraud comes from six templates only |
| SRS 7.5 | Flag collusion | ring, weak_ring; honest sharing through county popular pools | `collusion_score` | Strong rings fully separable; 15 of 21 weak-ring agents inside the legitimate range |
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
| Chapters 1–3 | Odd timing and volume | sequential (night), duplicate and weak (early morning), ring hour windows; legit_night, legit_busy and the off-hours tail (hard legitimate cases) | `time_of_day_entropy`, `submission_frequency`, `volume_vs_peers` | Entropy measures how spread out the hours are, not when they fall |
| Chapters 1–3 | Multiple accounts working together | ring, weak_ring | `collusion_score` | Ring members' counties are independent, so rings are not local |

## Label-aware changes, in order (final; no further changes)

These changes to the generator were made after seeing labelled summaries. None involved a model, a split or a test set.

1. **v2, before this rework.** A feature review showed that `customer_similarity` separated the classes perfectly, so the legitimate repeat-customer share was widened.
2. **v3 Step 1.** A per-pattern review showed legitimate `collusion_score` up to 0.17, caused by chance collisions between 6-digit customer ids. Customer ids were widened to 8 digits.
3. **v3 Step 1B, first pass (a realism change).** A per-pattern review showed that `collusion_score` separated rings from all legitimate agents perfectly (rings 0.43–0.67, legitimate agents at most 0.016). Two things were added:
   - per-county popular customers, used by legitimate and fraud agents on the same terms;
   - weak rings.
4. **v3 Step 1C (a realism change; the last one).** The Step 3 EDA found two shortcuts caused by hard limits:
   - no legitimate agent submitted at 05:00–06:59 or 20:00–23:59, while 80 of 130 fraud agents did;
   - legitimate daily volume was capped at 8, while every weak fraud agent's busiest day was exactly 9.

   The fixes:
   - legitimate hours got an off-hours tail, with no clipping;
   - every group's daily volume now comes from one heavy-tailed mechanism;
   - weak fraud got a random elevated rate;
   - class-specific exact values were randomised per agent (active-day probability, pattern share and pool sizes);
   - an overlap audit was added, whose test locks in the three accepted signatures.

**Changes made without looking at labels, from the author's specification:**
- 47 counties instead of 5 cities (realism);
- 1000 agents;
- a county floor of 2;
- a client and category reference list, with 1–3 clients per agent;
- the duplicate pattern defined as the same customer for the same client;
- rare same-customer, different-client repeats.

## Known issues and caveats

1. **The generator was changed four times after seeing labels.** See the list above.
2. **Accepted separations remain** (see "Accepted separations"). A model can detect strong rings and sequential agents from one feature each. Results on those patterns say little about harder real cases.
3. **`collusion_score` uses all agents, including test agents.** No labels are used, but the partitions are not independent at the feature level.
4. **The earlier (v2) deployment choice used test results.** v2 had no validation set, so switching the live detector to Isolation Forest v2 was decided after seeing test results.
5. **Weak fraud and weak rings are deliberately close to legitimate agents.** Low recall on them is the expected result.
6. **The backend database still holds v2 data.** One backend test (`test_agent_detail_context_lists_only_known_clients_and_categories`) fails until the database is reloaded at Step 13. The API tests also hard-code agent `A1104`, which does not exist in v3.
7. **Out-of-date files in `ml/data/synthetic/`:** `train_test_split.csv` and `fraud_flags*.csv` are from v2. The v3 files are `split.csv` (Step 5) and `feature_vectors.csv` (Step 4). The flag files are regenerated at Steps 8–13.
8. **Single features are near-perfect on some patterns** (training AUC table above): strong rings, sequential and duplicate, and weak rings on `collusion_score`. Model results on those patterns mostly reflect these signatures. Weak fraud is the honest hard case.
9. **Two platform-wide features use all agents' records, across splits:** `collusion_score` and `volume_vs_peers`. This matches deployment, and no labels are involved.
10. **The backend still computes the v2 features.** It counts total volume rather than the 24-hour window, uses max(repetition, sequential) rather than similarity of identifiers, and stores the entropy column as `time_of_day_dist`. Backend parity is a Step 13 task.
