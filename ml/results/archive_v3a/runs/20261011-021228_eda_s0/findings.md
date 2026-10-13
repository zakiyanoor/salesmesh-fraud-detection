# EDA findings (run `20261011-021228_eda_s0`)

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
| level_0 | level_1 | rho |
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
