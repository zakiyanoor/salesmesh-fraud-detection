# EDA findings (run `20261011-021303_eda_s0`)

Inputs: cleaned activation records (138756 rows), 1000 agents, 20 clients, labels, and near-duplicate flags from cleaning run `20261011-020933_clean`.
EDA reads labels to describe groups and covers all agents, including those Step 5 will put in validation and test. The feature definitions were fixed in DATA_CARD.md before this EDA; nothing in later steps is chosen from it unless stated.

## Class balance
130 fraud of 1000 agents (13.0%). Fraud agents produce 22.1% of records.

| profile | agents |
|---|---|
| legit | 679 |
| legit_night | 70 |
| legit_repeat | 69 |
| legit_busy | 52 |
| ring | 41 |
| weak_ring | 21 |
| sequential | 21 |
| duplicate | 21 |
| weak | 26 |

## Volume by hour
Share of records at 00:00-04:59: legitimate 1.4%, fraud 25.7%. Per group: see fig02.

## Distributions by group (median [IQR])
| profile | agents | records | max_records_one_day | active_days | night_share | hour_entropy | distinct_customer_ratio | repeat_same_client_share | shared_customer_share | near_duplicates |
|---|---|---|---|---|---|---|---|---|---|---|
| legit | 679 | 115 [106-125] | 8 [8-8] | 26 [24-27] | 0 [0-0] | 0.751 [0.74-0.762] | 0.992 [0.98-1] | 0 [0-0] | 0 [0-0.0139] | 0 [0-0] |
| legit_night | 70 | 115 [104-129] | 8 [8-8] | 26 [25-27] | 0.175 [0.144-0.223] | 0.842 [0.828-0.853] | 1 [0.979-1] | 0 [0-0] | 0 [0-0.0109] | 0 [0-0] |
| legit_repeat | 69 | 115 [104-126] | 8 [8-8] | 26 [24-27] | 0 [0-0] | 0.751 [0.741-0.761] | 0.757 [0.67-0.829] | 0.181 [0.14-0.286] | 0 [0-0.0127] | 0 [0-0] |
| legit_busy | 52 | 261 [246-276] | 14 [14-14] | 26 [25-27] | 0 [0-0] | 0.759 [0.752-0.766] | 0.988 [0.98-1] | 0 [0-0.00335] | 0.00374 [0-0.0267] | 0 [0-0] |
| ring | 41 | 273 [257-298] | 16 [14-17] | 27 [26-28] | 0.117 [0-0.285] | 0.664 [0.624-0.742] | 0.733 [0.702-0.802] | 0.186 [0.152-0.247] | 0.59 [0.559-0.624] | 0 [0-0] |
| weak_ring | 21 | 122 [103-162] | 8 [7-10] | 27 [26-28] | 0 [0-0] | 0.748 [0.724-0.766] | 0.962 [0.932-0.973] | 0.0291 [0.0128-0.0473] | 0.0938 [0.0773-0.111] | 0 [0-0] |
| sequential | 21 | 307 [289-326] | 18 [18-18] | 26 [26-28] | 0.702 [0.694-0.717] | 0.767 [0.754-0.771] | 0.997 [0.993-1] | 0 [0-0] | 0 [0-0.0034] | 24 [18-33] |
| duplicate | 21 | 273 [263-289] | 15 [15-15] | 27 [26-28] | 0.185 [0.171-0.192] | 0.699 [0.693-0.717] | 0.389 [0.384-0.395] | 0.607 [0.596-0.616] | 0 [0-0.0194] | 2 [1-2] |
| weak | 26 | 150 [145-156] | 9 [9-9] | 27 [26.2-28] | 0.0375 [0.0213-0.0591] | 0.816 [0.803-0.826] | 0.899 [0.862-0.928] | 0.0937 [0.0653-0.132] | 0.00355 [0-0.0284] | 0 [0-0] |

Medians by class:

| is_fraud | records | max_records_one_day | active_days | night_share | hour_entropy | distinct_customer_ratio | repeat_same_client_share | shared_customer_share | near_duplicates |
|---|---|---|---|---|---|---|---|---|---|
| legit | 116.0 | 8.0 | 26.0 | 0.0 | 0.753 | 0.991 | 0.0 | 0.0 | 0.0 |
| fraud | 262.0 | 15.0 | 27.0 | 0.095 | 0.745 | 0.853 | 0.126 | 0.038 | 0.0 |

## Near-duplicate flags from cleaning, by group
| profile | agents_flagged | flags |
|---|---|---|
| legit | 0 | 0 |
| legit_night | 0 | 0 |
| legit_repeat | 6 | 7 |
| legit_busy | 0 | 0 |
| ring | 10 | 13 |
| weak_ring | 1 | 1 |
| sequential | 21 | 529 |
| duplicate | 18 | 38 |
| weak | 3 | 6 |

## Strongest correlations between descriptors (Spearman, all agents)
| descriptor_a | descriptor_b | rho |
|---|---|---|
| distinct_customer_ratio | repeat_same_client_share | -0.694 |
| records | max_records_one_day | 0.668 |
| records | active_days | 0.532 |
| max_records_one_day | near_duplicates | 0.486 |
| night_share | near_duplicates | 0.465 |
| max_records_one_day | night_share | 0.42 |

## Figures
- `fig01_class_balance.png`: Agents per pattern, coloured by class.
- `fig02_volume_by_hour.png`: Share of each group's records by hour of day.
- `fig03_distributions_by_group.png`: Box plots of nine per-agent descriptors by group.
- `fig04_correlations.png`: Spearman correlations between the descriptors.

Raw sample table: `raw_sample.md`.

## Short findings
1. **Class balance:** 130 of 1000 agents are fraud (13.0%), but they produce 22.1% of records. Strong-ring, sequential and duplicate agents submit about 2.3–2.7 times the plain-legitimate median of 115 records.
2. **Volume by hour:** fraud has 25.7% of its records at 00:00–04:59, against 1.4% for legitimate agents, almost all of it from `legit_night`. Duplicate and weak agents peak at 04:00–07:59. Strong rings spread across their own windows.
3. **Distributions by group:**
   - Shared customers separate strong rings (median 0.59) from everyone else.
   - The share of records repeating a customer for the same client separates duplicate agents (0.61). Rings (0.19) and the legitimate repeat-customer group (0.18) overlap there by design.
   - Hour entropy is weak overall (legitimate 0.753 vs fraud 0.745 at the median).
   - The sequential pattern shows up as near-duplicate one-digit flags: all 21 sequential agents are flagged, with a median of 24 flags.
4. **Correlations:** the strongest pair is distinct-customer ratio vs repeat share (rho -0.69). The other pairs are below 0.7 in absolute value, so no two descriptors are redundant.

## Surprising or weak: two generator shortcuts (found after the generator was frozen)
These counts come from this run's descriptors joined with the labels.

1. **Legitimate submission hours are hard-clipped.**
   - Plain legitimate hours are drawn as `clip(Normal(13, 3), 7, 19)`, and `legit_night` adds 00:00–04:59. As a result, 0 of 870 legitimate agents ever submit at 05:00–06:59 or 20:00–23:59.
   - The fraud agents with at least one record in those hours are: all 21 duplicate, all 26 weak, 30 of 41 strong ring and 3 of 21 weak ring, 80 of 130 in total.
   - The rule "any record at 05:00–06:59 or 20:00–23:59" would score 80 true positives with 0 false positives on all 1000 agents.
2. **Legitimate daily volume has a hard cap.**
   - Plain legitimate daily counts are uniform on 1–8, so no plain, night or repeat legitimate agent ever exceeds 8 records in a day (0 of 818). `legit_busy` agents are always 13–14.
   - Every weak fraud agent's busiest day is exactly 9 (min 9, max 9).
   - A busiest-day or busiest-24h volume feature can therefore separate weak fraud from plain legitimate agents by a single unit.

Both come from hard-bounded generator ranges, not from fraud behaviour. Real agents occasionally work early or late, and have uncapped busy days. Neither shortcut is in the model features as currently defined, but `submission_frequency` (busiest 24 hours) and `time_of_day_entropy` can pick part of them up. The Step 4 single-feature AUC table will measure how much.
