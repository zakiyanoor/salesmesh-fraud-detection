# Data card: SalesMesh synthetic activation data (v3, change #5)

**Status: final after data change #5 (2026-10-13).** Change #5 is a validity fix found by review: it enforces the platform's integrity rules (R1 to R6 below) in the generator and adds SalesMesh context fields. The data will not be changed again. Change #5 came after validation results on the earlier data had been seen, and before the test set had been read. The test set was read once, at Step 11 (2026-10-13, run `20261013-103859_final_evaluation_s42`; `results/FINAL_TEST_RESULTS.md`). See `results/CHANGES.md`, change 5.

**Generator:** `ml/data_generation.py`, seed 42, 1000 agents, fraud rate 0.13.

**One command regenerates everything in this card:**

```
cd ml && python data_generation.py
```

It writes the 7 data files to `ml/data/synthetic/` and a run folder `ml/runs/<timestamp>_datagen_s42/` with `run_info.json` (parameters, data file hashes, library versions, Python, OS, CPU, RAM, git commit), `generation_summary.csv`, `rings.csv`, `data_checks.json`, `overlap_audit.csv` and `raw_descriptors_by_agent.csv`. The checks run inside the generator.

**Current generation run:** `ml/runs/20261013-091128_datagen_s42/`. Freeze note: `ml/results/FREEZE.md` (sha256 of the data files, generator code and rules; checked by `ml/tests/test_freeze.py`).

**Archived, unchanged (nothing deleted):**
- the earlier v3 data (called v3a here): `ml/data/archive_v3a/`;
- every v3a run folder (generation, cleaning, EDA, split, features, models, selection, explanations, system checks): `ml/results/archive_v3a/runs/`;
- the v3a freeze record: `ml/results/archive_v3a/FREEZE_v3a.md`;
- the v3a data card, generator, checks and generator tests: `ml/results/archive_v3a/` (`DATA_CARD_v3a.md`, `code/`);
- the v2 data: `ml/data/archive_v2/`.

## Scope

This data supports one SalesMesh module: **U-CS 56, AI Fraud Detection**, which detects anomalies and flags suspicious activity. Agent registration, KYC, training, certification, task allocation, verification, commission, reputation and analytics belong to other modules and are out of scope.

Change #5 adds fields that those modules would own (identity, account status, certifications, quality score, commission). They are here so the data looks like SalesMesh data and so the integrity rules can be checked. They are illustrative, drawn independently of fraud, and **none of them is a model input**. The model input list stays the 4 chosen features (`feature_engineering.MODEL_FEATURES`).

## Files and data dictionary

All files are in `ml/data/synthetic/`. No feature or model may read `labels.csv` or `rings.csv`. After the split, labels are loaded only through `ml/labels_guard.py`, which refuses test labels until the Step 11 script unlocks them. Id columns are never model inputs (`ml/tests/test_no_id_inputs.py`). Identity columns are never model inputs and never in `labels.csv` (`ml/tests/test_integrity_rules.py`).

The "SRS" column names the section the field supports where the author has one; "none named" means the field is context only.

**`agents.csv`** (1000 rows; pipeline and backend)

| Column | Type | Meaning | SRS |
|---|---|---|---|
| `agent_id` | string | `A` followed by 5 random digits; unique; carries no label information | 3.1 |
| `registration_timestamp` | datetime (Africa/Nairobi) | when the agent registered; 14 to 365 days before the window | 3.1 |
| `region` | string | one of Kenya's 47 counties | section 2 (multi-region) |
| `account_status` | string | `active` (940) or `suspended` (60). A snapshot taken after the window, for administrative reasons unrelated to fraud. Not a label and not a model input | none named |

**`agent_identity.csv`** (1000 rows; new; kept separate from `agents.csv`)

| Column | Type | Meaning | SRS |
|---|---|---|---|
| `agent_id` | string | foreign key to `agents.csv`; one row per agent | 3.1.1 |
| `full_name` | string | first and last name, each drawn at random from lists of 70 common Kenyan first names and 70 last names; unique per agent | 3.1.1 |
| `phone_number` | string | `+2547` followed by 8 random digits; unique | 3.1.1 |
| `national_id_number` | string | 8 random digits (first digit 1 to 9); unique | 3.1.1 |

**All three identity fields are fictional and randomly generated.** Any match to a real person, phone number or ID number is coincidence. They are never used to contact anyone and never used for modelling. No fraud pattern uses them.

**`agent_categories.csv`** (1441 rows; new)

| Column | Type | Meaning | SRS |
|---|---|---|---|
| `agent_id` | string | foreign key to `agents.csv` | 3.1 |
| `category` | string | one of the 12 categories | 3.1 |
| `certification_status` | string | `certified` for every category the agent works in during the window; `expired` for one extra category held by 80 agents (8%), with no activity in the window | 3.1 |
| `certified_at` | datetime (Africa/Nairobi) | certified: uniform between registration and the agent's first activity in that category; expired: uniform between registration and the window start | 3.1 |

**`activation_records.csv`** (135,494 rows; pipeline and backend)

| Column | Type | Meaning | SRS |
|---|---|---|---|
| `record_id` | string | `R` followed by an integer, assigned in timestamp order; unique | 4.3, 8.2 (audit trail) |
| `agent_id` | string | the submitting agent (foreign key to `agents.csv`) | 7.5 |
| `timestamp` | datetime (Africa/Nairobi) | submission time, inside the window | 7.5 |
| `customer_id` | string | `CUST` followed by 8 digits | 7.5 |
| `activation_status` | string | `completed`, `failed` or `pending`; pending only in the last 72 hours (R6); independent of fraud | 3.6 |
| `client_id` | string | `CL01` to `CL20` (foreign key to `clients.csv`) | 3.1, 8.4 |
| `category` | string | the client's category; each client has exactly one category | 3.1, 8.4 |
| `quality_score` | int 0 to 100 | per-record quality: agent mean (Normal(80, 5)) plus record noise (Normal(0, 8)), 15 points lower when failed, rounded and kept inside 0 to 100 | 2.2.4, 3.6 |
| `commission_kes` | int | the client's rate when `completed`, otherwise 0 | 3.7 |

**`clients.csv`** (20 rows; reference list)

| Column | Type | Meaning | SRS |
|---|---|---|---|
| `client_id` | string | `CL01` to `CL20` | 3.1 |
| `name` | string | `Client 01` to `Client 20`; no real brand names | 3.1 |
| `category` | string | banking, mobile money, insurance, SACCO, e-commerce, fashion, telecom, healthcare, education, logistics, agritech or real estate | 3.1, 8.4 |
| `commission_per_activation_kes` | int | set by category (illustrative): banking 250, mobile money 60, insurance 300, SACCO 200, e-commerce 80, fashion 50, telecom 40, healthcare 150, education 120, logistics 70, agritech 100, real estate 400 | 3.7 |

**`labels.csv`** (1000 rows; evaluation and stratified splitting only). Byte-identical to the v3a file.

| Column | Type | Meaning |
|---|---|---|
| `agent_id` | string | foreign key to `agents.csv` |
| `is_fraud` | bool | ground-truth label |
| `profile` | string | legit, legit_night, legit_repeat, legit_busy, ring, weak_ring, sequential, duplicate or weak |
| `ring_id` | string | `ring_NN` for ring and weak_ring agents, empty otherwise |

**`rings.csv`** (14 rows; evaluation only). Byte-identical to the v3a file. Columns: `ring_id`, `strength` (strong or weak), `size`, `pool_size`, `hour_start`, `hour_width`, `daily_median`.

## Generation rules R1 to R6 (enforced in the generator, not by filtering)

Each client has exactly one category, so a (customer, client) pair identifies the product. The platform rule is that one customer activates one client service once.

| Rule | Statement | How the generator enforces it |
|---|---|---|
| R1 | For every honest agent, each (customer, client) pair is used by no other agent. | A platform-wide set of taken pairs. Normal submissions only use free pairs. New customers are drawn from ids not used anywhere (ring pools and popular pools are reserved first). |
| R2 | An honest agent repeats a pair only as a retry after a failed or pending attempt, with at most one completed activation per pair. Cross sell (same customer, another client) is allowed. | 60% of failed or pending normal attempts (`RETRY_PROB`) are queued and resubmitted at the agent's first normal submission on a later active day. No other path reuses an own pair. |
| R3 | County popular pools stay (same settings), but a taken pair is skipped. Honest agents still share customers across different clients. | A popular pick tries up to 30 pool customers for a free pair, then falls back to a new customer. |
| R4 | Fraud agents may break R1 and R2; that is the planted behaviour. | Only the pattern submissions break the rules: ring members share pool customers for the same client; duplicate and weak agents resubmit pairs from their own pool. Their normal submissions follow R1 to R3 through the same code path as honest agents. |
| R5 | An agent activates only in categories where it is certified at that time; every activation is on or after `registration_timestamp` and `certified_at`. | Certifications are built from activity: `certified_at` lies between registration and the first activity in the category. Expired categories have no activity. |
| R6 | `pending` only in the last 72 hours of the window (from 2026-08-28 00:00). Older records are completed or failed. | In the last 72 hours a record is pending with probability 0.30; otherwise completed or failed at 0.85 to 0.05 (17:1). |

**`legit_repeat`, redefined.** Before change #5, a `legit_repeat` agent sent 15% to 50% of normal submissions to 4 to 12 regular customers, repeating the same customer for the same client many times. That broke R1 and R2. Now `legit_repeat` is **cross sell plus retries**: with the same per-agent share (15% to 50%), a normal submission sells an earlier customer of the agent to another client, if a free pair exists; due retries come first. A single-client `legit_repeat` agent gets one extra cross-sell client, from the same category when one exists, so that it can cross sell at all; this moved 26 agents from one client to two. Its repeated-customer share is 0.367 (before: 0.261), so it remains a hard honest case for `customer_similarity`; its same-pair repeat share fell from 0.223 to 0.044 (retries only).

**Duplicate fraud and `CROSS_CLIENT_REPEAT_PROB` are unchanged in definition.** Duplicate agents resubmit the same customer for the same client from a personal pool of 15 to 35 pairs. `CROSS_CLIENT_REPEAT_PROB = 0.02` still sends 2% of normal submissions of multi-client agents to an earlier customer for a different client, now only if that pair is free.

## Other generator rules (unchanged from v3a)

**Common to every agent, legit or fraud**
- **County:** 2 agents per county first, the rest by rough 2019 census population; assigned independently of the label.
- **Clients:** 20 clients in 12 categories; each agent works with 1, 2 or 3 clients (probabilities 0.45, 0.40, 0.15); extra clients from the first client's category with probability 0.6; per-agent Dirichlet (alpha 2) mix.
- **Activity:** active-day probability 0.75 to 0.95 per agent; daily count negative binomial (dispersion 3) around `group median x lognormal(0, 0.25)`; no cap.
- **Normal hours:** a 1% to 6% per-agent share at a uniformly random hour; the rest from Normal(13:00, 3 h), resampled inside 0 to 23.
- **Popular customers:** each county has a pool of `max(20, 10 x agents in the county)` customers; 35% of agents are pool users, sending 3% to 15% of normal submissions to their county's pool (subject to R3).

**Group medians and pattern rules**

| Group | Daily median | Pattern |
|---|---|---|
| legit (plain) | 4.5 | none |
| legit_night | 4.5 | 10% to 25% of submissions at 00:00 to 04:59 |
| legit_repeat | 4.5 | 15% to 50% of normal submissions cross sell an earlier customer to another client (see above) |
| legit_busy | 10 | none |
| ring (strong) | per ring 5 to 12 | 55% to 85% of submissions from a shared pool (20 to 75 customers per member, no consecutive ids), inside the ring's 2 to 5 hour window; ring size 2 to 6 |
| weak_ring | per ring 2.5 to 5 | 8% to 20% of submissions from a small shared pool (5 to 15 customers per member) |
| sequential | 12 | 55% to 85% of submissions use incrementing customer ids, at 00:00 to 04:59 |
| duplicate | 10 | 55% to 85% of submissions resubmit pairs from a personal pool of 15 to 35 (customer, client) pairs, at 04:00 to 07:59 |
| weak | 4.5 x 1.15 to 1.6 | 10% to 25% of submissions reuse a personal pool of 5 to 15 pairs, at 04:00 to 07:59 |

## Context fields: separate random streams, no label signal

The behaviour (agents, profiles, rings, activations, statuses) uses the same seeded `random` and `numpy` streams as before. All new context fields come from four separate generators spawned from the seed (`np.random.SeedSequence(42).spawn(4)`: identity, account_status, certifications, quality). They are drawn after the behaviour, so they cannot change any behaviour draw; `test_context_fields_do_not_change_behaviour` regenerates the activations without them and checks they are identical. Honest and fraud agents use the same distributions, and no fraud pattern reads them.

| Field | Distribution (seed 42 result) |
|---|---|
| `account_status` | exactly 6% suspended at random (60 agents), 94% active (940) |
| identity | names, phones and ID numbers drawn without replacement: 1000 unique of each |
| certifications | 1361 certified rows and 80 expired rows; rows per agent 1: 618, 2: 324, 3: 57, 4: 1; certified 0 to 351 days (median 71) before the first activity in the category |
| `quality_score` | mean 79.3, SD 9.9, range 31 to 100; completed 80.1, failed 65.2, pending 80.0; agent means 61.2 to 92.8 (SD 5.0); 2603 records (1.9%) sit at the cap of 100 |
| `commission_kes` | 124,271 completed records paid (KES 17,232,310 in total); 11,223 records at 0; per agent 1,980 to 105,250 (median 12,180) |
| status | completed 124,271 (91.7%), failed 7,204 (5.3%), pending 4,019 (3.0%); completed to failed 17.25 to 1; every pending record is on 28, 29 or 30 August (1340, 1363, 1316) |

## Counts (seed 42, run `20261013-091128_datagen_s42`)

1000 agents: 130 fraud (13.0%) and 870 legitimate. 135,494 activation records and 117,949 distinct customers. Fraud agents produce 19.1% of records. Timestamps run from 2026-08-01 00:01:04 to 2026-08-30 23:58:43, Africa/Nairobi (window 2026-08-01 00:00 to 2026-08-31 00:00; naive local times, UTC+03:00).

| Class | Pattern | Agents | Records | Records per agent, mean (min to max) |
|---|---|---|---|---|
| fraud | ring (strong) | 41 | 8,252 | 201.3 (72 to 481) |
| fraud | weak_ring | 21 | 2,060 | 98.1 (43 to 160) |
| fraud | sequential | 21 | 6,307 | 300.3 (177 to 448) |
| fraud | duplicate | 21 | 5,331 | 253.9 (151 to 409) |
| fraud | weak | 26 | 3,988 | 153.4 (86 to 221) |
| legit | legit | 679 | 79,760 | 117.5 (32 to 316) |
| legit | legit_night | 70 | 7,970 | 113.9 (48 to 200) |
| legit | legit_repeat | 69 | 8,566 | 124.1 (52 to 232) |
| legit | legit_busy | 52 | 13,260 | 255.0 (116 to 465) |

**Rings, counties and former regions are identical to v3a**, because `agents.csv` (first three columns), `labels.csv` and `rings.csv` are drawn before any activation and did not change: 14 rings (9 strong, 5 weak, 62 agents), agents per county 5 to 89 (median 20, 0 counties under 5). The ring and region tables are in `results/archive_v3a/DATA_CARD_v3a.md` and still apply.

**Clients and categories per agent:** clients 1: 424, 2: 439, 3: 137 (v3a: 450, 413, 137; the 26 agents that moved are single-client `legit_repeat` agents using their cross-sell client). Categories 1: 671, 2: 297, 3: 32.

**By primary category** (the category with most of the agent's activations)

| Primary category | Agents | Fraud | Fraud rate |
|---|---|---|---|
| mobile money | 184 | 19 | 0.103 |
| banking | 157 | 27 | 0.172 |
| telecom | 154 | 14 | 0.091 |
| e-commerce | 121 | 18 | 0.149 |
| insurance | 93 | 12 | 0.129 |
| SACCO | 92 | 11 | 0.120 |
| agritech | 53 | 5 | 0.094 |
| education | 50 | 8 | 0.160 |
| fashion | 32 | 7 | 0.219 |
| healthcare | 28 | 4 | 0.143 |
| real estate | 19 | 4 | 0.211 |
| logistics | 17 | 1 | 0.059 |

The differences are sampling noise: chi-square p for fraud vs county 0.649, former region 0.403, primary category 0.421, primary client 0.652.

## Checks on the generated data (`data_checks.json`)

**Rules** (counts of violations; honest must be 0; the fraud side shows the planted behaviour)

| Rule | Measure | Honest | Fraud |
|---|---|---|---|
| R1 | (customer, client) pairs used by 2+ agents (honest if any user is honest) | 0 | 290 |
| R2 | repeats of an own pair after a completed attempt | 0 | 4,887 |
| R3 | customers shared by 2+ honest agents (allowed, across clients) / pairs shared by 2+ honest agents | 356 / 0 | not applicable |
| R5 | activations before registration or without a certification in force | 0 | 0 |
| R6 | pending records before the last 72 hours | 0 | 0 |

R5 and R6 are platform rules that fraud does not break, so the fraud side is 0 by design. Pairs shared between an honest and a fraud agent: 0 (v3a: 10).

**Referential integrity:** every `agent_id` in activations, identity, certifications and labels exists in `agents.csv`; one identity row per agent; every `client_id` exists; every record's category equals its client's category; no activation in an expired category; no certification after the first activity or before registration. All counts are 0.

**Ranges:** `quality_score` outside 0 to 100: 0. `commission_kes` non-zero when not completed: 0. Commission different from the client rate when completed: 0. Client rates outside 40 to 400: 0.

**Identity:** 1000 rows; duplicate names, phone numbers and ID numbers: 0, 0, 0; malformed names, phone numbers and ID numbers: 0, 0, 0.

**Independence table** (single-field ROC AUC against `is_fraud`, all 1000 agents; a data audit only, never modelling)

| Field | AUC | Strength max(AUC, 1 - AUC) | Inside 0.35 to 0.65 |
|---|---|---|---|
| `account_status` (suspended) | 0.496 | 0.504 | yes |
| number of categories (certification rows) | 0.515 | 0.515 | yes |
| registration age | 0.515 | 0.515 | yes |
| mean quality score | 0.524 | 0.524 | yes |
| completed share | 0.516 | 0.516 | yes |
| commission total | 0.679 | 0.679 | **no** |
| commission mean per record (extra) | 0.550 | 0.550 | yes |

**Commission total is outside the range.** The per-record commission is independent of fraud, but the total is the number of completed activations times the rate, and fraud agents submit more (for example sequential 300 records against plain legit 118). The total therefore carries volume, which the behaviour already carries. The mean per record (0.550) shows the field itself is independent. Commission is not a model input.

## Overlap audit

Every raw per-agent descriptor is compared between legitimate agents (870) and each fraud pattern. Cells are min / median / max. "No overlap" marks a fraud group whose whole range lies outside the legitimate range; "x% outside" is the share of that group outside it. Source: `overlap_audit.csv` in the run folder.

| Descriptor | legit | ring | weak_ring | sequential | duplicate | weak |
|---|---|---|---|---|---|---|
| Submissions in window | 32 / 117 / 465 | 72 / 175 / 481 (2% outside) | 43 / 91 / 160 | 177 / 307 / 448 | 151 / 249 / 409 | 86 / 145 / 221 |
| Max submissions in one day | 4 / 13 / 43 | 8 / 18 / 47 (2% outside) | 5 / 11 / 19 | 20 / 28 / 47 (10% outside) | 16 / 23 / 45 (10% outside) | 12 / 16.5 / 27 |
| Mean submissions per active day | 1.6 / 4.8 / 16 | 3.13 / 7.12 / 16.6 (2% outside) | 2.47 / 4.06 / 6.36 | 7.38 / 12.1 / 20.4 (10% outside) | 7.38 / 10.3 / 17.8 (5% outside) | 4.3 / 6.41 / 8.5 |
| Distinct hours used | 11 / 17 / 23 | 7 / 15 / 20 (7% outside) | 13 / 16 / 20 | 18 / 20 / 22 | 13 / 16 / 19 | 16 / 18 / 22 |
| Share of submissions 00:00 to 04:59 | 0 / 0.0103 / 0.306 | 0 / 0.0096 / 0.522 (12% outside) | 0 / 0.0625 / 0.203 | **0.537 / 0.709 / 0.842 (no overlap)** | 0.136 / 0.177 / 0.24 | 0.0233 / 0.0585 / 0.0899 |
| Hour-of-day entropy (0 to 1) | 0.662 / 0.785 / 0.908 | 0.385 / 0.595 / 0.794 (78% outside) | 0.71 / 0.797 / 0.872 | 0.688 / 0.768 / 0.84 | 0.587 / 0.694 / 0.754 (43% outside) | 0.805 / 0.838 / 0.88 |
| Share of submissions on Sat/Sun | 0.116 / 0.328 / 0.605 | 0.196 / 0.341 / 0.473 | 0.133 / 0.33 / 0.532 | 0.232 / 0.31 / 0.454 | 0.267 / 0.333 / 0.48 | 0.133 / 0.309 / 0.506 |
| Distinct customers per client | 10.3 / 67.8 / 318 | 36 / 89 / 253 | 20.5 / 49.7 / 145 | 68 / 156 / 446 (10% outside) | 23.5 / 46 / 155 | 35.3 / 88.5 / 191 |
| Share repeating an earlier customer+client | 0 / 0.0402 / 0.125 | 0.04 / 0.144 / 0.326 (63% outside) | 0.0123 / 0.0508 / 0.0878 | 0.0032 / 0.0104 / 0.0224 | **0.447 / 0.621 / 0.787 (no overlap)** | 0.0465 / 0.153 / 0.237 (73% outside) |
| Clients per agent | 1 / 2 / 3 | 1 / 2 / 3 | 1 / 2 / 3 | 1 / 2 / 3 | 1 / 2 / 3 | 1 / 1.5 / 3 |
| Registration age (days) | 14 / 188 / 364 | 18 / 156 / 362 | 38 / 234 / 356 | 15 / 168 / 354 | 30 / 272 / 345 | 15 / 196 / 352 |
| Share of completed activations | 0.802 / 0.919 / 1 | 0.86 / 0.923 / 0.968 | 0.846 / 0.915 / 0.967 | 0.878 / 0.924 / 0.968 | 0.885 / 0.921 / 0.945 | 0.844 / 0.917 / 0.974 |
| Collusion score | 0 / 0 / 0.1 | **0.288 / 0.581 / 0.814 (no overlap)** | 0.0296 / 0.09 / 0.164 (38% outside) | 0 / 0 / 0.0256 | 0 / 0 / 0.0387 | 0 / 0 / 0.0455 |
| Customer similarity (identifiers) | 0.0973 / 0.102 / 0.124 | 0.1 / 0.104 / 0.109 | 0.0989 / 0.103 / 0.109 | **0.257 / 0.398 / 0.506 (no overlap)** | 0.108 / 0.119 / 0.146 (24% outside) | 0.101 / 0.105 / 0.108 |

**Accepted separations** (`test_only_accepted_signatures_have_zero_overlap_with_legit` fails if any other zero-overlap row appears)

| Descriptor | Group | Why it is accepted |
|---|---|---|
| Collusion score | strong ring | A ring is many accounts sharing a customer pool. Honest sharing exists (popular customers, across clients) but stays small (at most 0.100). |
| Customer similarity | sequential | Incrementing identifiers share leading digits; that is the pattern. |
| Night share | sequential | The pattern defines scripted night batches. |
| Repeat share (same customer and client) | duplicate | **New with change #5.** Under R2 an honest agent repeats its own pair only as a retry (at most 12.5% of records), so resubmitting the same pair is outside the honest range by definition. This is a raw descriptor, not a model feature. The model feature `customer_similarity` still overlaps: 76% of duplicate agents lie inside the honest range. |

Weak rings remain the designed hard case: 13 of 21 weak-ring agents score inside the honest `collusion_score` range.

## Independent units

The unit of analysis is the **agent**. Features, labels, the split and every metric are at agent level.

**135,494 rows are not 135,494 independent examples.** Records are nested inside agents, and ring members depend on each other through shared pools. The independent units are at most the **1000 agents**, and for collusion the **14 rings** are the units: 62 ring agents form 14 groups, so ring evidence is 14 rings, not 62 agents. Fraud comes from five fixed templates, which narrows the evidence further.

## Split (Step 5)

The split was re-run on 2026-10-13 (run `20261013-092952_split_s42`) with the same design: 70/15/15 at agent level, stratified by pattern, `SPLIT_SEED = 42`, at least 15 fraud agents in validation and test. `labels.csv` is byte-identical to v3a, so `split.csv` is byte-identical too: 700 / 150 / 150 agents, 91 / 20 / 19 fraud.

**13 of the 14 rings have members in more than one split.** This is acceptable here: the detector is unsupervised, so no ring label is learned from training members, and `collusion_score` is computed from unlabelled records of all agents in the period, which is exactly what the live system has at detection time. The cost is that train, validation and test are not independent at the feature level, which is stated as a limitation below.

## Feature definitions (Step 4; unchanged)

`feature_engineering.compute_feature_vectors(activations, agents, period_start, period_end)` uses records with `period_start <= timestamp < period_end` (default 2026-08-01 to 2026-08-31 00:00). It reads only `agent_id`, `timestamp`, `customer_id`, `category` and the agent's `region`; it ignores every context column (`test_feature_vectors_carry_no_context_or_identity_column`).

| Feature | Formula | Units |
|---|---|---|
| `submission_frequency` | max submissions in any 24-hour sliding window | submissions per 24 h |
| `time_of_day_entropy` | Shannon entropy of submission hours / log2(24) | 0 to 1 |
| `customer_similarity` | mean over all pairs of submissions of the share of matching digit positions of the 8-digit customer id | 0 to 1 (about 0.1 for random ids) |
| `collusion_score` | share of the agent's distinct customers also used by another agent in the period (platform-wide) | 0 to 1 |
| `volume_vs_peers` (candidate) | volume / median volume of peers (same primary category and former region, widened below 15 agents) | ratio |

**Model input list:** `MODEL_FEATURES` = `submission_frequency`, `time_of_day_entropy`, `customer_similarity`, `collusion_score` (the chosen model `lof_v3_4f`, run `20261013-093050_selection_s42`; v3a chose `if_v3_4f` with the same inputs). `test_model_input_list_is_exactly_the_four_features` checks it, and that no context or identity column is in it.

**Peer group levels used:** 533 agents at category + former region, 467 at category only.

## Single-feature AUC on training agents (Step 4, run `20261013-093024_feature_checks`)

700 training agents (91 fraud); validation and test labels were not read. Cells are raw ROC AUC (strength max(AUC, 1 - AUC)); columns compare the named fraud agents with all 609 training legitimate agents.

| Feature | All fraud | ring | weak_ring | sequential | duplicate | weak |
|---|---|---|---|---|---|---|
| `submission_frequency` | 0.740 (0.740) | 0.746 (0.746) | 0.315 (0.685) | 0.955 (**0.955**) | 0.906 (0.906) | 0.742 (0.742) |
| `time_of_day_entropy` | 0.346 (0.654) | 0.044 (**0.956**) | 0.512 (0.512) | 0.420 (0.580) | 0.023 (**0.977**) | 0.912 (0.912) |
| `customer_similarity` | 0.809 (0.809) | 0.708 (0.708) | 0.658 (0.658) | 1.000 (**1.000**) | 0.997 (**0.997**) | 0.773 (0.773) |
| `collusion_score` | 0.712 (0.712) | 1.000 (**1.000**) | 0.981 (**0.981**) | 0.436 (0.564) | 0.452 (0.548) | 0.485 (0.515) |
| `volume_vs_peers` | 0.760 (0.760) | 0.780 (0.780) | 0.346 (0.654) | 0.974 (**0.974**) | 0.956 (**0.956**) | 0.705 (0.705) |

Bold marks strength 0.95 or above (shortcut risk, listed as limitations). Compared with v3a, `customer_similarity` on duplicate rose from 0.965 to 0.997 and `time_of_day_entropy` on duplicate from 0.908 to 0.977: honest agents no longer repeat pairs, so duplicate agents stand out more. **`volume_vs_peers` decision: KEEP** (AUC 0.760 > 0.55; max Spearman 0.803 with `submission_frequency`, at most 0.85). The v3a table is in `results/archive_v3a/DATA_CARD_v3a.md`.

## Requirements traceability

| Source | Requirement | Generator | Feature or field | Known limitation |
|---|---|---|---|---|
| SRS 2.2.4 | Quality scoring and anomaly detection | all patterns; `quality_score` per record | all features give one anomaly score per agent; `quality_score` is context only | scores are not calibrated; quality is not modelled |
| SRS 7.5 | Detect anomalies; flag collusion; flag fake activations | ring, weak_ring, sequential, duplicate, weak | the 4 features | five templates only |
| SRS 3.6 | Flag suspicious or low-quality onboardings | `activation_status`, `quality_score` (independent of fraud) | none | low quality is not modelled separately from fraud |
| SRS 3.1 | Agents, categories and certification | `agents.csv`, `agent_categories.csv`, R5 | none | certification is another module; values are illustrative |
| SRS 3.1.1 | Agent identity | `agent_identity.csv` (fictional) | none, never a model input | no real personal data; identity checks for fraud (shared phones, for example) are not modelled |
| SRS 3.7 | Commission per completed activation | `commission_per_activation_kes`, `commission_kes` | none | rates are illustrative; payout is another module |
| SRS 3.1, 8.4 | Categories; benchmarking across categories and clients | 20 clients, 12 categories, one category per client | `volume_vs_peers` (candidate) | category and client are independent of fraud by design |
| SRS 4.3, 8.2 | Decisions and scores logged | `record_id`, run folders with hashes | score output schema (Step 9 criteria) | logging is done by the backend |
| SRS 5.1, 5.3 | Near real time; growth | `--n-agents` | scoring time checks | per-period scoring, not streaming |
| SRS section 2 | Auditable, configurable, multi-region | seeds, named constants, `run_info.json`, 47 counties | threshold as config | county results too small to interpret |

## Mapping to the course material

| Course item | What it asks | Where this card answers it |
|---|---|---|
| ML Fundamentals Deep Dive, Lesson 8.2: correctness | data follows the domain's rules | R1 to R6 enforced in the generator; rule and integrity checks all 0 on the honest side |
| Lesson 8.2: relevance | fields match the task | the 4 behaviour features; context fields kept out of the model |
| Lesson 8.2: coverage | the cases the model will meet | 5 fraud patterns, 3 hard honest groups, 47 counties, 20 clients, 12 categories, every hour of the day |
| Lesson 8.2: balance | class shares and how they are handled | 13% fraud (130 of 1000); stratified agent-level split; PR AUC reported; no oversampling |
| Lesson 8.2: independence | units are independent; no leakage | agents and rings as units; labels only in `labels.csv` and `rings.csv`; context fields from separate streams; independence table |
| Lesson 9.3: risks | what can go wrong with synthetic data | Limitations below; accepted separations; the four label-aware changes and the integrity fix listed in order |
| Lesson 9.4: record the generator, rules and filtering | reproducibility | `data_generation.py` with named constants; rules R1 to R6 (enforced, not filtered; nothing is filtered out after generation); `run_info.json` with hashes; `FREEZE.md` |
| Build Phase Sprint I: data source | where the data comes from | synthetic, from `data_generation.py`, seed 42; no SalesMesh data |
| Build Phase Sprint I: preparation steps | how data is prepared | generation with checks, then `clean_data.py` (Step 2), features (Step 4), split (Step 5), scaling (Step 6) |
| Build Phase Sprint I: ethics | no real personal data | identity is fictional and random, never used for contact or modelling; masking required in the analyst interface (see CHANGES.md, change 5) |
| Build Phase Sprint I: reproducibility | one command regenerates | `cd ml && python data_generation.py` |

## Limitations

1. **Synthetic only.** Every pattern, rate and weight is an assumption by the author. Results on this data cannot prove real-world performance on SalesMesh agents.
2. **Context fields are independent of fraud by design.** Account status, identity, certifications, quality and commission carry no fraud signal (except that commission totals follow volume). Real fraud may well show in these fields, for example shared phone numbers or low quality; this data cannot test that.
3. **Rings span splits** (13 of 14). Acceptable because the detector is unsupervised and features use only unlabelled records available at detection time, but the partitions are not independent at the feature level.
4. **Accepted separations remain:** strong rings on `collusion_score`; sequential agents on customer similarity and night share; duplicate agents on the same-pair repeat share (a raw descriptor).
5. **Customer ids only.** There are no customer names, phones or addresses, so customer similarity is measured on identifiers.
6. **`quality_score` is capped at 100** (1.9% of records sit at the cap), for every agent alike.
7. **The generator was changed after seeing labelled summaries: four label-aware changes, plus the integrity fix (change 5)** (list below). The integrity fix came after validation results had been seen.
8. **The backend database and backend features are still v2.** Reload and parity are Step 13 and backend sprint tasks (see CHANGES.md, change 5).

## Generator changes after seeing labelled summaries, in order (final): four label-aware changes plus the integrity fix

1. **v2.** The legitimate repeat-customer share was widened after `customer_similarity` separated the classes perfectly.
2. **v3 Step 1.** Customer ids were widened to 8 digits after chance collisions raised honest `collusion_score`.
3. **v3 Step 1B.** Per-county popular customers and weak rings were added after `collusion_score` separated rings perfectly.
4. **v3 Step 1C.** Hard limits were removed (honest hours and daily caps), and the overlap audit was added.

**Plus the integrity fix, change 5 (2026-10-13): a validity fix found by review, not tuned to improve metrics.** Honest agents shared (customer, client) pairs (33 pairs on seed 42), which the platform rule allows only in fraud, and the data lacked SalesMesh context. R1 to R6 are now enforced, `legit_repeat` is cross sell plus retries, and context fields were added from separate streams. Made after validation results on the earlier data had been seen; the test set was never read; the selection rule (with its amendment) and the acceptance criteria apply unchanged.

## Known issues

1. Steps 2 to 10 were re-run on this data on 2026-10-13 with every setting unchanged (CHANGES.md, "Pipeline rerun"). The chosen model is `lof_v3_4f`. Step 11 (test, read once) and Step 12 (seeds 101 to 110) followed; results are in `results/FINAL_TEST_RESULTS.md`. The v3a results are archived and describe the earlier data.
2. The fictional name lists give at most 70 x 70 = 4,900 unique full names, so `generate_dataset` refuses more than 4,900 agents. The S4 scaling check therefore generates behaviour only (agents and activations).
3. `duplicate_activation_rule` (a reported baseline) has precision 1.000 on training, validation, test and all 10 stability seeds, because R1 and R2 forbid honest shared or post-completion repeated pairs by construction. It shows how strong the integrity rules are in this data, not what a rule would achieve on real records.
4. Backend test `test_pipeline.py::test_collusion_ring_agents_from_synthetic_data_score_above_every_legit_agent` asserts a fixed floor of 0.3 for strong-ring `collusion_score`; the lowest is now 0.288. Separation still holds (0.288 against an honest maximum of 0.100). The backend was not touched.
5. `ml/data/synthetic/train_test_split.csv` and `fraud_flags*.csv` are v2 leftovers, not used by v3.
