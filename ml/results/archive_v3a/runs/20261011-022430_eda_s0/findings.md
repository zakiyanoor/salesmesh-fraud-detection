# EDA findings (run `20261011-022430_eda_s0`)

Inputs: cleaned activation records (135509 rows), 1000 agents, 20 clients, labels, and near-duplicate flags from cleaning run `20261011-022427_clean`.
EDA reads labels to describe groups and covers all agents, including those Step 5 will put in validation and test. The feature definitions were fixed in DATA_CARD.md before this EDA; nothing in later steps is chosen from it unless stated.

## Class balance
130 fraud of 1000 agents (13.0%). Fraud agents produce 19.5% of records.

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
Share of records at 00:00-04:59: legitimate 2.4%, fraud 25.9%. Per group: see fig02.

## Distributions by group (median [IQR])
| profile | agents | records | max_records_one_day | active_days | night_share | hour_entropy | distinct_customer_ratio | repeat_same_client_share | shared_customer_share | near_duplicates |
|---|---|---|---|---|---|---|---|---|---|---|
| legit | 679 | 112 [91-136] | 12 [10-15] | 24 [22-26] | 0.01 [0-0.0175] | 0.784 [0.766-0.799] | 1 [0.979-1] | 0 [0-0] | 0 [0-0.0149] | 0 [0-0] |
| legit_night | 70 | 120 [94-144] | 14 [10-16] | 24 [23-25] | 0.168 [0.135-0.217] | 0.861 [0.842-0.873] | 1 [0.983-1] | 0 [0-0] | 0 [0-0.0141] | 0 [0-0] |
| legit_repeat | 69 | 109 [89-134] | 12 [10-15] | 24 [22-26] | 0.0108 [0.00599-0.0156] | 0.781 [0.767-0.794] | 0.758 [0.653-0.833] | 0.226 [0.123-0.28] | 0 [0-0.00847] | 0 [0-0] |
| legit_busy | 52 | 257 [205-302] | 25 [19.8-29] | 25 [24-27] | 0.00957 [0.00679-0.0142] | 0.801 [0.786-0.808] | 0.987 [0.973-1] | 0 [0-0] | 0.00366 [0-0.013] | 0 [0-0] |
| ring | 41 | 201 [154-249] | 21 [15-24] | 26 [24-28] | 0.00917 [0-0.141] | 0.608 [0.551-0.688] | 0.802 [0.741-0.845] | 0.143 [0.0941-0.208] | 0.611 [0.504-0.663] | 0 [0-0] |
| weak_ring | 21 | 97 [68-123] | 11 [8-13] | 23 [21-25] | 0.0794 [0.00694-0.129] | 0.782 [0.736-0.828] | 0.978 [0.952-1] | 0.0149 [0-0.0222] | 0.0741 [0.0568-0.113] | 0 [0-0] |
| sequential | 21 | 244 [215-333] | 26 [22-35] | 26 [24-27] | 0.727 [0.65-0.788] | 0.76 [0.709-0.8] | 0.996 [0.993-1] | 0 [0-0] | 0 [0-0.00455] | 23 [16-30] |
| duplicate | 21 | 236 [219-308] | 26 [22-34] | 25 [24-27] | 0.172 [0.158-0.192] | 0.721 [0.7-0.768] | 0.438 [0.361-0.521] | 0.562 [0.471-0.633] | 0 [0-0.0118] | 3 [1-3] |
| weak | 26 | 160 [138-177] | 17 [15-18.8] | 25 [22.2-26] | 0.0515 [0.0455-0.0607] | 0.837 [0.825-0.85] | 0.875 [0.832-0.92] | 0.114 [0.0777-0.153] | 0.00299 [0-0.0174] | 0 [0-0] |

Medians by class:

| is_fraud | records | max_records_one_day | active_days | night_share | hour_entropy | distinct_customer_ratio | repeat_same_client_share | shared_customer_share | near_duplicates |
|---|---|---|---|---|---|---|---|---|---|
| legit | 115.5 | 13.0 | 24.0 | 0.011 | 0.787 | 0.992 | 0.0 | 0.0 | 0.0 |
| fraud | 188.5 | 19.5 | 25.0 | 0.107 | 0.74 | 0.868 | 0.106 | 0.032 | 0.0 |

## Near-duplicate flags from cleaning, by group
| profile | agents_flagged | flags |
|---|---|---|
| legit | 1 | 1 |
| legit_night | 0 | 0 |
| legit_repeat | 13 | 16 |
| legit_busy | 0 | 0 |
| ring | 9 | 15 |
| weak_ring | 0 | 0 |
| sequential | 21 | 541 |
| duplicate | 18 | 55 |
| weak | 6 | 6 |

## Strongest correlations between descriptors (Spearman, all agents)
| descriptor_a | descriptor_b | rho |
|---|---|---|
| records | max_records_one_day | 0.827 |
| distinct_customer_ratio | repeat_same_client_share | -0.696 |
| records | active_days | 0.52 |
| night_share | hour_entropy | 0.409 |
| repeat_same_client_share | near_duplicates | 0.342 |
| records | near_duplicates | 0.311 |

## Figures
- `fig01_class_balance.png`: Agents per pattern, coloured by class.
- `fig02_volume_by_hour.png`: Share of each group's records by hour of day.
- `fig03_distributions_by_group.png`: Box plots of nine per-agent descriptors by group.
- `fig04_correlations.png`: Spearman correlations between the descriptors.

Raw sample table: `raw_sample.md`.

## Short findings (after label-aware change #4)
1. **Class balance:** 130 of 1000 agents are fraud (13.0%). They produce 19.5% of records (22.1% before change #4).
2. **Volume by hour:** fraud has 25.9% of its records at 00:00–04:59, against 2.4% for legitimate agents. Every legitimate group now has a small share of records at every hour of the day (1–6% of submissions per agent fall at a random hour), so night submissions alone no longer identify a group, except the sequential pattern (see 4).
3. **Daily volume:** busiest days are now heavy-tailed for every group. Legitimate agents (all four groups) range from 5 to 48 records on their busiest day (median 13). Weak fraud agents' busiest days range from 10 to 25 across 12 distinct values.
4. **What still separates by design** (the overlap audit in the generation run): strong rings on shared customers, and sequential agents on identifier similarity and night share. Duplicate agents are mostly, but not completely, separated on customer reuse. Strong rings are mostly separated on hour entropy.
5. **Correlations:** records and busiest day (rho 0.83) are now the most correlated pair, as expected once daily volume varies. Distinct-customer ratio and repeat share follow at rho -0.70.

## Shortcut check (the two Step 3 shortcuts)
These counts come from this data joined with the labels.

- **Hours:** the rule "any record at 05:00–06:59 or 20:00–23:59" now flags 120 fraud agents and 846 of 870 legitimate agents (before: 80 and 0). The shortcut is gone.
- **Daily volume:** 711 of 818 non-busy legitimate agents have a day above 8 records (before: 0). Weak fraud busiest days take 12 different values (before: always 9). The shortcut is gone.
