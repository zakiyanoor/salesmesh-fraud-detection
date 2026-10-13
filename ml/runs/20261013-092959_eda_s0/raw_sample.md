# Raw sample (seed 0)

## activation_records.csv (115001 rows, raw, before cleaning)

| record_id | agent_id | timestamp | customer_id | activation_status | client_id | category | quality_score | commission_kes |
|---|---|---|---|---|---|---|---|---|
| R16686 | A72616 | 2026-08-03 13:32:45 | CUST50556117 | completed | CL15 | education | 67 | 120 |
| R39146 | A65057 | 2026-08-08 12:56:39 | CUST52524387 | completed | CL14 | healthcare | 79 | 150 |
| R45318 | A52753 | 2026-08-09 17:05:48 | CUST33021740 | completed | CL05 | insurance | 82 | 300 |
| R48263 | A40340 | 2026-08-10 13:12:58 | CUST80428988 | completed | CL03 | mobile money | 82 | 60 |
| R51027 | A56898 | 2026-08-11 08:33:32 | CUST83606066 | completed | CL14 | healthcare | 63 | 150 |
| R59163 | A10726 | 2026-08-12 17:42:47 | CUST79969907 | completed | CL17 | logistics | 83 | 70 |
| R97054 | A42816 | 2026-08-21 11:08:47 | CUST69753794 | completed | CL08 | SACCO | 78 | 200 |
| R115878 | A72616 | 2026-08-25 13:04:17 | CUST68421630 | completed | CL15 | education | 64 | 120 |

## agents.csv (850 rows)

| agent_id | registration_timestamp | region | account_status |
|---|---|---|---|
| A33405 | 2026-04-11 23:30:03 | Kakamega | suspended |
| A41358 | 2025-11-17 04:46:07 | Narok | active |
| A36772 | 2025-10-13 20:52:31 | Baringo | active |
| A30635 | 2026-01-06 02:04:25 | Narok | active |
| A26683 | 2025-12-08 12:58:20 | Kilifi | active |

## clients.csv (20 rows, first 5)

| client_id | name | category | commission_per_activation_kes |
|---|---|---|---|
| CL01 | Client 01 | banking | 250 |
| CL02 | Client 02 | banking | 250 |
| CL03 | Client 03 | mobile money | 60 |
| CL04 | Client 04 | mobile money | 60 |
| CL05 | Client 05 | insurance | 300 |
