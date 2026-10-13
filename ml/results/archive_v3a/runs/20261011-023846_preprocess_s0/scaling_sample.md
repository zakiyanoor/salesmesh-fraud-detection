# Before and after scaling (seed 0; scaler fitted on 700 training agents)

| split | agent_id | values | submission_frequency | time_of_day_entropy | customer_similarity | collusion_score | volume_vs_peers |
|---|---|---|---|---|---|---|---|
| train | A46347 | raw | 14.0 | 0.769 | 0.102 | 0.0 | 1.216 |
| train | A46347 | scaled | -0.257 | -0.191 | -0.168 | -0.3 | 0.172 |
| train | A87397 | raw | 11.0 | 0.754 | 0.103 | 0.0 | 0.846 |
| train | A87397 | scaled | -0.703 | -0.46 | -0.159 | -0.3 | -0.525 |
| train | A15778 | raw | 15.0 | 0.77 | 0.102 | 0.008 | 1.215 |
| train | A15778 | scaled | -0.109 | -0.175 | -0.174 | -0.234 | 0.172 |
| train | A71644 | raw | 11.0 | 0.786 | 0.102 | 0.011 | 0.647 |
| train | A71644 | scaled | -0.703 | 0.105 | -0.164 | -0.207 | -0.9 |
| train | A12540 | raw | 22.0 | 0.89 | 0.103 | 0.024 | 1.004 |
| train | A12540 | scaled | 0.931 | 1.95 | -0.151 | -0.1 | -0.227 |
| validation | A77889 | raw | 11.0 | 0.812 | 0.101 | 0.0 | 0.546 |
| validation | A77889 | scaled | -0.703 | 0.574 | -0.201 | -0.3 | -1.091 |
| validation | A49824 | raw | 9.0 | 0.737 | 0.102 | 0.0 | 0.545 |
| validation | A49824 | scaled | -1.0 | -0.77 | -0.165 | -0.3 | -1.093 |
| validation | A35443 | raw | 24.0 | 0.737 | 0.118 | 0.0 | 2.235 |
| validation | A35443 | scaled | 1.228 | -0.761 | 0.188 | -0.3 | 2.096 |
| validation | A76307 | raw | 14.0 | 0.783 | 0.101 | 0.0 | 0.911 |
| validation | A76307 | scaled | -0.257 | 0.06 | -0.183 | -0.3 | -0.403 |
| validation | A16658 | raw | 10.0 | 0.889 | 0.104 | 0.02 | 0.813 |
| validation | A16658 | scaled | -0.852 | 1.939 | -0.13 | -0.129 | -0.587 |

## Scaler statistics

| feature | scaler_mean | train_mean | all_agents_mean | scaler_std | train_std_ddof0 | all_agents_std_ddof0 |
|---|---|---|---|---|---|---|
| submission_frequency | 15.7329 | 15.7329 | 15.685 | 6.7311 | 6.7311 | 6.7021 |
| time_of_day_entropy | 0.78 | 0.78 | 0.7803 | 0.0564 | 0.0564 | 0.055 |
| customer_similarity | 0.1097 | 0.1097 | 0.1095 | 0.0452 | 0.0452 | 0.0449 |
| collusion_score | 0.0358 | 0.0358 | 0.0352 | 0.1193 | 0.1193 | 0.1177 |
| volume_vs_peers | 1.1241 | 1.1241 | 1.1277 | 0.5299 | 0.5299 | 0.5507 |
