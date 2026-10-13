# EDA findings (run `20261013-092959_eda_s0`)

Inputs: cleaned activation records (115001 rows), 850 agents, 20 clients, labels, and near-duplicate flags from cleaning run `20261013-092936_clean`.
EDA reads labels to describe groups. Test agents are left out (their labels were never read); descriptors use every agent's unlabelled records. The feature definitions were fixed in DATA_CARD.md before this EDA; nothing in later steps is chosen from it unless stated.

## Class balance
111 fraud of 850 agents (13.1%). Fraud agents produce 19.2% of records.

| profile | agents |
|---|---|
| legit | 582 |
| legit_night | 57 |
| legit_repeat | 59 |
| legit_busy | 41 |
| ring | 35 |
| weak_ring | 18 |
| sequential | 18 |
| duplicate | 18 |
| weak | 22 |

## Volume by hour
Share of records at 00:00-04:59: legitimate 2.3%, fraud 25.7%. Per group: see fig02.

## Distributions by group (median [IQR])
| profile | agents | records | max_records_one_day | active_days | night_share | hour_entropy | distinct_customer_ratio | repeat_same_client_share | shared_customer_share | near_duplicates |
|---|---|---|---|---|---|---|---|---|---|---|
| legit | 582 | 114 [92-136] | 13 [10-15] | 24 [22-26] | 0.00909 [0-0.0165] | 0.782 [0.764-0.798] | 0.951 [0.932-0.966] | 0.0391 [0.0265-0.0534] | 0 [0-0.0103] | 0 [0-0] |
| legit_night | 57 | 110 [88-124] | 12 [10-14] | 24 [22-25] | 0.182 [0.154-0.22] | 0.86 [0.835-0.873] | 0.955 [0.935-0.969] | 0.042 [0.0268-0.0539] | 0 [0-0.012] | 0 [0-0] |
| legit_repeat | 59 | 117 [99-154] | 14 [11-17.5] | 25 [23-26] | 0.0099 [0.00506-0.0174] | 0.785 [0.766-0.804] | 0.615 [0.552-0.689] | 0.043 [0.0282-0.056] | 0 [0-0.012] | 0 [0-0] |
| legit_busy | 41 | 245 [202-306] | 26 [21-30] | 26 [24-27] | 0.0101 [0.0069-0.0161] | 0.795 [0.786-0.806] | 0.94 [0.927-0.962] | 0.0475 [0.0327-0.0556] | 0 [0-0] | 0 [0-0] |
| ring | 35 | 173 [148-222] | 18 [14-25] | 25 [23-27] | 0.00877 [0-0.166] | 0.581 [0.528-0.627] | 0.837 [0.731-0.867] | 0.14 [0.0908-0.172] | 0.573 [0.527-0.665] | 0 [0-1] |
| weak_ring | 18 | 91 [66-136] | 11 [8.25-13] | 23 [21.2-25.8] | 0.0525 [0.0107-0.134] | 0.797 [0.759-0.826] | 0.937 [0.927-0.952] | 0.0489 [0.0385-0.0638] | 0.0862 [0.0577-0.121] | 0 [0-0] |
| sequential | 18 | 310 [274-324] | 28.5 [24.5-32.5] | 24 [23.2-26.8] | 0.697 [0.651-0.762] | 0.774 [0.742-0.805] | 0.986 [0.981-0.99] | 0.0105 [0.00517-0.0175] | 0 [0-0.00242] | 20.5 [18-32.2] |
| duplicate | 18 | 264 [204-292] | 23.5 [20-34] | 25 [23.2-27] | 0.174 [0.145-0.205] | 0.698 [0.65-0.728] | 0.381 [0.304-0.444] | 0.618 [0.552-0.69] | 0 [0-0.0121] | 3 [1.25-4] |
| weak | 22 | 144 [124-178] | 17.5 [15-21] | 24.5 [21.2-26] | 0.054 [0.045-0.0777] | 0.835 [0.816-0.847] | 0.843 [0.814-0.869] | 0.153 [0.121-0.182] | 0 [0-0] | 0 [0-0] |

Medians by class:

| is_fraud | records | max_records_one_day | active_days | night_share | hour_entropy | distinct_customer_ratio | repeat_same_client_share | shared_customer_share | near_duplicates |
|---|---|---|---|---|---|---|---|---|---|
| legit | 117.0 | 13.0 | 24.0 | 0.01 | 0.785 | 0.948 | 0.04 | 0.0 | 0.0 |
| fraud | 177.0 | 19.0 | 24.0 | 0.099 | 0.748 | 0.859 | 0.121 | 0.03 | 0.0 |

## Near-duplicate flags from cleaning, by group
| profile | agents_flagged | flags |
|---|---|---|
| legit | 0 | 0 |
| legit_night | 0 | 0 |
| legit_repeat | 0 | 0 |
| legit_busy | 0 | 0 |
| ring | 10 | 12 |
| weak_ring | 0 | 0 |
| sequential | 18 | 488 |
| duplicate | 16 | 55 |
| weak | 2 | 2 |

## Strongest correlations between descriptors (Spearman, 850 agents)
| descriptor_a | descriptor_b | rho |
|---|---|---|
| records | max_records_one_day | 0.812 |
| distinct_customer_ratio | repeat_same_client_share | -0.77 |
| records | active_days | 0.512 |
| night_share | hour_entropy | 0.417 |
| records | near_duplicates | 0.351 |
| max_records_one_day | near_duplicates | 0.339 |

## Figures
- `fig01_class_balance.png`: Agents per pattern, coloured by class.
- `fig02_volume_by_hour.png`: Share of each group's records by hour of day.
- `fig03_distributions_by_group.png`: Box plots of nine per-agent descriptors by group.
- `fig04_correlations.png`: Spearman correlations between the descriptors.

Raw sample table: `raw_sample.md`.
