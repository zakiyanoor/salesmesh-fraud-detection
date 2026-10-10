# Data card: SalesMesh synthetic activation data (v3)

**Generator:** `ml/data_generation.py`. The default dataset uses seed 42, 600 agents and a fraud rate of 0.13.

**Current generation run:** `ml/runs/20261011-010944_datagen_s42/`, which holds:
- `run_info.json`: parameters, file hashes, library versions, Python, OS, CPU, RAM and the git commit;
- `generation_summary.csv`;
- `rings.csv`.

**Earlier v3 runs, kept as superseded:**
- `20261011-004903_datagen_s42`: 6-digit customer ids.
- `20261011-005051_datagen_s42`: before Step 1B.

**v2 data:** archived unchanged in `ml/data/archive_v2/`.

## Limits of this data

The data is synthetic. Every pattern, rate, overlap and county weight below is an assumption made by the author. The assumptions draw on the Concept Note, on Proposal Sections 2.4.1 and 2.6, and on rough 2019 census populations; none were measured from a real platform. Model results on this data show how the method behaves under these assumptions, not how it would perform on real SalesMesh agents. In particular:

- Fraud is drawn from six fixed templates, so real fraud that matches none of them is not represented.
- The hard legitimate groups cover only four kinds of overlap: night work, repeat customers, high volume, and shared popular customers.
- The difficulty of the data was set by the author, partly after seeing labelled summaries (see Known issues).

## Independent units

The unit of analysis is the **agent**, not the activation record.
- Every feature is one value per agent, computed over the analysis period.
- The label is per agent.
- Splits, cross-validation and every metric are at agent level.

The 80,773 records are not independent observations. They are nested inside 600 agents, and ring agents also depend on each other through shared customer pools. The effective sample size is therefore at most 600 agents, of which 78 are fraud. For fraud it is smaller still: ring members are not independent of each other, and all fraud comes from six templates.

## Files

All files are written to `ml/data/synthetic/`.

| File | Contents | Who may read it |
|---|---|---|
| `agents.csv` | `agent_id`, `registration_timestamp`, `region` (county) | pipeline and backend |
| `activation_records.csv` | `record_id`, `agent_id`, `timestamp`, `customer_id`, `activation_status`, `client_id`, `category` | pipeline and backend |
| `labels.csv` | `agent_id`, `is_fraud`, `profile`, `ring_id` | evaluation and stratified splitting only |
| `rings.csv` | ring metadata (strength, size, pool size, hour window, daily volume) | evaluation only |

No feature or model may read `labels.csv` or `rings.csv`. `region` is not a model feature.

## Parameters

Each setting is a named constant at the top of `data_generation.py`. The CLI flags are `--n-agents` (default 600), `--fraud-rate` (default 0.13), `--seed` (default 42) and `--out-dir`.

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

All rings together, sequential and duplicate keep the v2 ratio of 3:1:1. The weak, weak_ring and popular-customer behaviours are new. The hard legitimate share rises from 16% of legit agents in v2 to 22%.

## Generator rules

**Common to all agents**
- The analysis window runs from 2026-08-01 to 2026-08-30.
- On each day, an agent is either inactive or submits a whole number of records drawn uniformly from its daily range.
- Every record gets a status (completed 0.85, pending 0.10, failed 0.05), a client and a category. All three are drawn independently of fraud.

**Identifiers**
- **Agent ids** are random 5-digit numbers (`A10000`–`A99999`). They are sorted alphabetically, so the id carries no label.
- **Registration dates** are drawn from one distribution for every agent, 14 to 365 days before the window. In v2, fraud agents were registered more recently, which leaked the label.
- **Customer ids** are `CUST` followed by 8 digits. Most ids are drawn at random from 90 million values, so a small number of chance collisions remain (see Checks).
- **Record ids** are assigned in timestamp order, after all records are generated.

**Region: Kenya's 47 counties** (`COUNTY_POPULATION_THOUSANDS`)
- Each agent's county is drawn with probability proportional to the county's rough 2019 census population.
- The draw is independent of the label, so the fraud rate does not depend on county, and ring members can sit in different counties.
- `FORMER_PROVINCE_COUNTIES` maps counties to the 8 former provinces. Step 11 uses this mapping for subgroup results.

**Popular customers, per county**
- Each county has a pool of popular customers, such as shops or families served by several agents. The pool size is `max(20, 10 × agents in the county)`.
- Each agent, legit or fraud, is a pool user with probability 0.35. A pool user sends a per-agent share of 3–15% of its normal-looking submissions to its own county's pool.
- This gives honest agents a non-zero `collusion_score`.
- Fraud agents use the pool on the same terms. A legit-only pool would have created a reverse shortcut.

**Legitimate agents**
- They are active on a day with probability 0.85 and submit 1–8 records per active day.
- Submission hours follow a normal distribution with mean 13:00 and standard deviation 3 hours, clipped to 07:00–19:00.
- Each record goes to a fresh random customer, or a county popular customer as described above.

**Hard legitimate groups**
- **`legit_night`:** a per-agent share of 10–25% of submissions falls at 00:00–04:59.
- **`legit_repeat`:** each agent has 8 regular customers. A per-agent share of 15–50% of submissions goes to them.
- **`legit_busy`:** 6–14 records per active day.

**Fraud agents (all patterns)**
- They are active on a day with probability 0.90.
- The patterns below set what share of their submissions follows the fraud pattern. All other submissions look normal: a fresh or popular customer at a normal daytime hour.

**Strong ring**
- 70% of submissions follow the pattern.
- Ring members are grouped into rings of 2–6 agents. The last ring can absorb one leftover agent.
- Each ring has its own:
  - shared customer pool of 20–75 customers per member, with random ids and no two consecutive numbers;
  - hour window, starting at a random hour and 2–5 hours wide;
  - daily volume range, with a low end of 3–8 and a width of 5–12.

**Weak ring (new)**
- Only a per-agent share of 8–20% of submissions comes from the ring's pool.
- The pool is small, at 5–15 customers per member.
- Daily volume is legit-like: the low end is 1–3 and the width is 5–8.
- The hour window rules are the same as for strong rings.

**Sequential**
- 70% of submissions follow the pattern, using incrementing customer ids.
- They are submitted at 00:00–04:59, at 6–18 records per active day.

**Duplicate**
- 70% of submissions follow the pattern, reusing a personal pool of 25 customers.
- They are submitted at 04:00–07:59, at 5–15 records per active day.

**Weak**
- Only a per-agent share of 10–25% of submissions follows the pattern, reusing a personal pool of 10 customers.
- Pattern submissions fall at 04:00–07:59.
- Volume is 2–9 records per active day.

## Counts (seed 42)

600 agents: 78 fraud (13.0%) and 522 legitimate. 80,773 activation records and 74,321 distinct customers. Fraud agents produce 20.3% of records.

| Class | Pattern | Agents | Records | Records per agent, mean (min–max) |
|---|---|---|---|---|
| fraud | ring (strong) | 25 | 5,096 | 203.8 (133–295) |
| fraud | weak_ring | 13 | 1,809 | 139.2 (121–171) |
| fraud | sequential | 12 | 4,003 | 333.6 (279–366) |
| fraud | duplicate | 12 | 3,180 | 265.0 (236–306) |
| fraud | weak | 16 | 2,341 | 146.3 (122–174) |
| legit | legit | 407 | 46,986 | 115.4 (68–176) |
| legit | legit_night | 42 | 4,784 | 113.9 (80–149) |
| legit | legit_repeat | 42 | 4,818 | 114.7 (82–147) |
| legit | legit_busy | 31 | 7,756 | 250.2 (201–308) |

**Rings (seed 42):** 8 rings, 38 agents.

| Ring | Strength | Agents | Pool | Hours | Daily range |
|---|---|---|---|---|---|
| ring_01 | strong | 5 | 265 | 14:00–17:59 | 4–10 |
| ring_02 | strong | 6 | 138 | 17:00–19:59 | 3–9 |
| ring_03 | strong | 5 | 150 | 10:00–14:59 | 7–14 |
| ring_04 | strong | 6 | 390 | 18:00–22:59 | 3–11 |
| ring_05 | strong | 3 | 213 | 01:00–05:59 | 3–15 |
| ring_06 | weak | 3 | 39 | 14:00–17:59 | 2–7 |
| ring_07 | weak | 6 | 66 | 08:00–09:59 | 3–8 |
| ring_08 | weak | 4 | 56 | 02:00–03:59 | 3–9 |

Six of the 8 ring windows overlap the legitimate 07:00–19:00 working day (all except ring_05 and ring_08).

**Agents per county (seed 42)**
- Median 12 agents, minimum 0 (Lamu), maximum 43 (Nairobi).
- 46 of the 47 counties have at least one agent.
- **6 counties have fewer than 5 agents:** Lamu (0), Tharaka-Nithi (2), Isiolo (3), Embu (3), Taita-Taveta (4) and Laikipia (4).
- **Largest counties:** Nairobi 43, Kiambu 29, Nakuru 26, Bungoma 24, Kilifi 22 and Trans Nzoia 22.

County-level results will be too small to interpret.

| Former province | Agents | Fraud | Fraud rate |
|---|---|---|---|
| Central | 69 | 9 | 0.130 |
| Coast | 55 | 7 | 0.127 |
| Eastern | 78 | 11 | 0.141 |
| Nairobi | 43 | 7 | 0.163 |
| North Eastern | 38 | 5 | 0.132 |
| Nyanza | 91 | 10 | 0.110 |
| Rift Valley | 164 | 21 | 0.128 |
| Western | 62 | 8 | 0.129 |

Fraud is independent of province (chi-square p = 0.997) and of county (p = 0.702, indicative only because many cells are small).

**Share of records at 00:00–04:59, by pattern:**

| Pattern | Share |
|---|---|
| sequential | 0.693 |
| duplicate | 0.173 |
| legit_night | 0.170 |
| ring | 0.088 |
| weak | 0.048 |
| weak_ring | 0.040 |
| other legit groups | 0.000 |

## Checks on the generated data

These checks come from a real run on seed 42 and are covered by `ml/tests/test_data_generation.py`.

**Determinism**
- The same seed gives byte-identical frames.
- A different seed gives different data.

**Identifiers carry no label**

| Field | Test | p |
|---|---|---|
| Agent id number | Mann-Whitney | 0.434 |
| Registration date | Kolmogorov-Smirnov | 0.655 |
| Record id | Mann-Whitney | 0.367 |

Record ids follow timestamp order, so they carry no information beyond the timestamp.

**`sequential_score` by pattern**
- Every pattern except sequential has a maximum of 0.000.
- Sequential agents average 0.692 (max 0.728).

**`collusion_score` by group** (computed with the `feature_engineering.py` formula)

| Group | Agents | Min | Median | Max | Non-zero |
|---|---|---|---|---|---|
| Legitimate | 522 | 0.000 | 0.000 | 0.074 | 188 |
| Strong ring | 25 | 0.507 | 0.563 | 0.661 | 25 |
| Weak ring | 13 | 0.043 | 0.095 | 0.173 | 13 |
| Other fraud | 40 | 0.000 | 0.000 | 0.032 | 17 |

- 2 of the 13 weak-ring agents score at or below the highest legitimate agent.
- No legitimate agent reaches the lowest strong-ring score.

**Chance collisions:** 225 customers are shared by two or more legitimate agents. 89.8% of them are within one county, from the popular pools. The remaining 10.2% are coincidental collisions between random 8-digit ids.

## Known issues and caveats

1. **The generator has been adjusted three times after reviews that saw labels.**
   - **In v2:** `customer_similarity` separated the classes perfectly, so the legitimate repeat-customer share was widened.
   - **In v3 Step 1:** legitimate `collusion_score` reached 0.17 through chance collisions between 6-digit customer ids, so customer ids were widened to 8 digits.
   - **In v3 Step 1B (a realism change):** the per-pattern review showed that `collusion_score` separated rings from all legitimate agents perfectly (rings 0.43–0.67, legitimate agents at most 0.016). Shared popular customers per county and weak rings were added to make that separation more realistic. Regions were changed to 47 counties at the same time.
   - **Effect:** none of these changes involved a model, a split or a test set. All were made after seeing labelled summaries, so the data's difficulty is not independent of the author's knowledge of the classes.
2. **Regions changed from 5 cities to 47 counties.** v2 used five cities (Nairobi, Mombasa, Kisumu, Nakuru, Eldoret); Eldoret is a town, not a county. v3 uses all 47 Kenyan counties, weighted by population, for realism. Counties also give a natural unit for the per-county popular-customer pools. Region is not a model feature, and fraud is drawn independently of it.
3. **`collusion_score` uses all agents, including test agents.** It compares each agent's customers with every other agent's customers across all partitions. No labels are used, but the partitions are not independent at the feature level.
4. **The earlier deployment choice used test results.** In v2 there was no validation set, so switching the live detector to Isolation Forest v2 was decided after seeing test-set results.
5. **Strong rings are still separable on `collusion_score` alone** (0.507 vs at most 0.074). Weak rings are only partly hidden: 2 of 13 fall inside the legitimate range.
6. **Weak fraud and weak rings are deliberately close to legitimate agents.** Low recall on them is the expected result, not a bug.
7. **Derived files in `ml/data/synthetic/` are out of date until Steps 2–5 regenerate them.** These are `activation_records_clean.csv`, `feature_vectors.csv`, `train_test_split.csv` and `fraud_flags*.csv`. They still describe the v2 agents. The backend database has not been reloaded.
