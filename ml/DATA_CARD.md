# Data card: SalesMesh synthetic activation data (v3)

Generator: `ml/data_generation.py`. Default dataset: seed 42, 600 agents, fraud rate 0.13. Generation run: `ml/runs/20261011-005051_datagen_s42/`, which holds `run_info.json` (parameters, file hashes, library versions) and `generation_summary.csv`. The previous v2 data is archived unchanged in `ml/data/archive_v2/`.

## Limits of this data

The data is synthetic. Every pattern, rate and overlap below is an assumption made by the author, informed by the Concept Note and Proposal Sections 2.4.1 and 2.6, and not measured from a real platform. Any model result on this data shows how the method behaves on these assumptions. It does not show how the method would perform on real SalesMesh agents. In particular:

- Fraud strategies are drawn from five fixed templates, so real fraud that matches none of them is not represented.
- The hard legitimate groups cover only three kinds of overlap.
- The difficulty of the data was chosen by the author, so the results depend on that choice.

## Files

All files are written to `ml/data/synthetic/`.

| File | Contents | Who may read it |
|---|---|---|
| `agents.csv` | `agent_id`, `registration_timestamp`, `region` | pipeline and backend |
| `activation_records.csv` | `record_id`, `agent_id`, `timestamp`, `customer_id`, `activation_status`, `client_id`, `category` | pipeline and backend |
| `labels.csv` | `agent_id`, `is_fraud`, `profile`, `ring_id` | evaluation and stratified splitting only |
| `rings.csv` | ring metadata (size, pool size, hour window, daily volume) | evaluation only |

No feature or model may read `labels.csv` or `rings.csv`.

## Parameters

Each setting is a named constant at the top of `data_generation.py`. The CLI flags are `--n-agents` (default 600), `--fraud-rate` (default 0.13), `--seed` (default 42) and `--out-dir`.

The number of fraud agents is `round(n_agents × fraud_rate)`. Agents are divided among the patterns by largest-remainder rounding of these shares:

| Group | Pattern | Share |
|---|---|---|
| Fraud | ring | 0.48 |
| Fraud | sequential | 0.16 |
| Fraud | duplicate | 0.16 |
| Fraud | weak | 0.20 |
| Legit | legit_night | 0.08 |
| Legit | legit_repeat | 0.08 |
| Legit | legit_busy | 0.06 |
| Legit | legit (plain) | remainder |

Ring, sequential and duplicate keep the v2 ratio of 3:1:1. The weak pattern is new. The hard legitimate share rises from 16% of legit agents in v2 to 22%.

## Generator rules

**Common to all agents**
- The analysis window runs from 2026-08-01 to 2026-08-30.
- On each day, an agent is either inactive or submits a whole number of records drawn uniformly from its daily range.
- Every record gets a status (completed 0.85, pending 0.10, failed 0.05), a client and a category. All three are drawn independently of fraud.

**Identifiers**
- **Agent ids** are random 5-digit numbers (`A10000`–`A99999`). They are sorted alphabetically, so the id carries no label.
- **Registration dates** are drawn from one distribution for every agent, 14 to 365 days before the window. In v2, fraud agents were registered more recently, which leaked the label.
- **Customer ids** are `CUST` followed by 8 digits.
- **Record ids** are assigned in timestamp order, after all records are generated.

**Legitimate agents**
- They are active on a day with probability 0.85 and submit 1–8 records per active day.
- Submission hours follow a normal distribution with mean 13:00 and standard deviation 3 hours, clipped to 07:00–19:00.
- Each record goes to a fresh random customer.

**Hard legitimate groups**
- **`legit_night`:** a per-agent share of 10–25% of submissions falls at 00:00–04:59.
- **`legit_repeat`:** each agent has 8 regular customers. A per-agent share of 15–50% of submissions goes to them.
- **`legit_busy`:** 6–14 records per active day. Otherwise normal.

**Fraud agents (ring, sequential, duplicate)**
- They are active on a day with probability 0.90.
- 30% of their submissions look normal: a fresh customer at a normal daytime hour. The remaining 70% follow the pattern.

**Ring**
- Ring members are grouped into rings of 2–6 agents. The last ring can absorb one leftover agent.
- Each ring has its own:
  - shared customer pool of 20–75 customers per member;
  - hour window, starting at a random hour and 2–5 hours wide;
  - daily volume range, with a low end of 3–8 and a width of 5–12.
- Pattern submissions draw a customer from the ring's pool.
- Pool ids are random and contain no two consecutive numbers. In v2, pools were consecutive id blocks, which accidentally gave ring agents a sequential signal (mean `sequential_score` 0.394).

**Sequential**
- Pattern submissions use incrementing customer ids.
- They are submitted at 00:00–04:59, at 6–18 records per active day.

**Duplicate**
- Pattern submissions reuse a personal pool of 25 customers.
- They are submitted at 04:00–07:59, at 5–15 records per active day.

**Weak (new)**
- Weak agents behave like legitimate agents, except for three changes:
  - their volume is slightly higher, at 2–9 records per day;
  - a per-agent share of only 10–25% of their submissions are fraudulent;
  - those fraudulent submissions reuse a personal pool of 10 customers at 04:00–07:59.
- They are active on a day with probability 0.90.

## Counts (seed 42)

600 agents: 78 fraud (13.0%) and 522 legitimate. 83,588 activation records and 75,299 distinct customers.

| Class | Pattern | Agents | Records | Records per agent, mean (min–max) |
|---|---|---|---|---|
| fraud | ring | 37 | 9,694 | 262.0 (153–367) |
| fraud | sequential | 13 | 4,234 | 325.7 (288–359) |
| fraud | duplicate | 12 | 3,321 | 276.8 (235–323) |
| fraud | weak | 16 | 2,381 | 148.8 (117–187) |
| legit | legit | 407 | 46,326 | 113.8 (75–163) |
| legit | legit_night | 42 | 4,962 | 118.1 (89–148) |
| legit | legit_repeat | 42 | 4,890 | 116.4 (91–142) |
| legit | legit_busy | 31 | 7,780 | 251.0 (188–298) |

Fraud agents produce 23.5% of all records.

**Rings (seed 42):** 10 rings, 37 agents.

| Ring | Agents | Pool | Hours | Daily range |
|---|---|---|---|---|
| ring_01 | 5 | 250 | 06:00–08:59 | 8–17 |
| ring_02 | 4 | 256 | 08:00–10:59 | 7–13 |
| ring_03 | 3 | 201 | 18:00–20:59 | 7–15 |
| ring_04 | 4 | 248 | 16:00–18:59 | 3–11 |
| ring_05 | 2 | 52 | 13:00–16:59 | 3–15 |
| ring_06 | 4 | 252 | 04:00–05:59 | 3–10 |
| ring_07 | 2 | 122 | 15:00–19:59 | 6–14 |
| ring_08 | 4 | 160 | 09:00–10:59 | 5–11 |
| ring_09 | 5 | 280 | 07:00–08:59 | 8–15 |
| ring_10 | 4 | 292 | 05:00–06:59 | 6–17 |

Eight of the 10 ring windows overlap the legitimate 07:00–19:00 working day (all except ring_06 and ring_10), so most rings have little off-hours signal.

**Share of records at 00:00–04:59, by pattern:**

| Pattern | Share |
|---|---|
| sequential | 0.687 |
| duplicate | 0.171 |
| legit_night | 0.159 |
| weak | 0.048 |
| ring | 0.023 |
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
| Record id | Mann-Whitney | 0.021 |

The record id result is not a leak. Record ids follow timestamp order, so they carry no information beyond the timestamp, which is a legitimate input.

**`sequential_score` by pattern (max)**
- Every pattern except sequential is at most 0.004.
- Sequential agents average 0.687 (max 0.739).

**`collusion_score` by pattern** (computed with the `feature_engineering.py` formula)
- Ring agents score 0.427–0.672.
- Every other pattern is at most 0.016.
- With 6-digit customer ids, chance collisions at this scale gave legitimate agents up to 0.17. That is why the id length was widened to 8 digits (see Known issues).

## Known issues and caveats

1. **The generator has been adjusted after reviews that saw labels.**
   - **In v2:** `customer_similarity` separated the classes perfectly, so the legitimate repeat-customer share was widened.
   - **In v3 (this version):** the first generated dataset (run `20261011-004903_datagen_s42`, kept) was reviewed per pattern. The review showed legitimate `collusion_score` up to 0.17, caused by chance collisions between 6-digit customer ids. Customer ids were widened to 8 digits.
   - **Effect:** neither change involved a model, a split or any test set. Both were still informed by labels, so the data's difficulty is not independent of the author's knowledge of the classes.
2. **`collusion_score` uses all agents, including test agents.** It compares each agent's customers with every other agent's customers across all partitions. No labels are used, but the train, validation and test partitions are not independent at the feature level: a test ring agent's score depends on its ring partners, wherever they sit.
3. **The earlier deployment choice used test results.** In v2 there was no validation set, so switching the live detector to Isolation Forest v2 was decided after seeing test-set results (the seed-42 test split and the seeds 1–5 test splits).
4. **`collusion_score` still separates ring agents from everyone else on this data** (0.427 vs at most 0.016). That is a consequence of the ring assumption: every ring shares a pool, and legitimate agents essentially never share customers. Real platforms will have legitimate customer sharing, such as households or agent handovers, which this data does not model.
5. **Weak fraud agents are deliberately close to legitimate agents.** About 10–25% of their activity is fraudulent, they have no shared customers and their volume is only slightly elevated. Low recall on them is the expected result, not a bug.
6. **Derived files in `ml/data/synthetic/` are out of date until Steps 2–5 regenerate them.** These are `activation_records_clean.csv`, `feature_vectors.csv`, `train_test_split.csv` and `fraud_flags*.csv`. They still describe the v2 agents. The backend database has not been reloaded.
