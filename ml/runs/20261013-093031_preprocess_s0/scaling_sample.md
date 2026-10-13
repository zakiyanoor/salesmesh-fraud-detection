# Before and after scaling (seed 0; scaler fitted on 700 training agents)

| split | agent_id | values | submission_frequency | time_of_day_entropy | customer_similarity | collusion_score | volume_vs_peers |
|---|---|---|---|---|---|---|---|
| train | A46347 | raw | 14.0 | 0.789 | 0.101 | 0.037 | 1.215 |
| train | A46347 | scaled | -0.293 | 0.182 | -0.203 | 0.034 | 0.154 |
| train | A87397 | raw | 18.0 | 0.804 | 0.101 | 0.021 | 1.282 |
| train | A87397 | scaled | 0.313 | 0.458 | -0.195 | -0.107 | 0.281 |
| train | A15778 | raw | 10.0 | 0.777 | 0.105 | 0.0 | 0.63 |
| train | A15778 | scaled | -0.899 | -0.029 | -0.093 | -0.282 | -0.956 |
| train | A71644 | raw | 10.0 | 0.791 | 0.104 | 0.011 | 0.85 |
| train | A71644 | scaled | -0.899 | 0.221 | -0.116 | -0.192 | -0.539 |
| train | A12540 | raw | 31.0 | 0.873 | 0.102 | 0.0 | 1.147 |
| train | A12540 | scaled | 2.284 | 1.683 | -0.169 | -0.282 | 0.024 |
| validation | A77889 | raw | 25.0 | 0.792 | 0.102 | 0.0 | 1.3 |
| validation | A77889 | scaled | 1.374 | 0.246 | -0.17 | -0.282 | 0.315 |
| validation | A49824 | raw | 17.0 | 0.775 | 0.102 | 0.02 | 0.892 |
| validation | A49824 | scaled | 0.162 | -0.068 | -0.182 | -0.116 | -0.46 |
| validation | A35443 | raw | 28.0 | 0.587 | 0.135 | 0.018 | 2.304 |
| validation | A35443 | scaled | 1.829 | -3.418 | 0.623 | -0.133 | 2.22 |
| validation | A76307 | raw | 20.0 | 0.796 | 0.102 | 0.0 | 1.325 |
| validation | A76307 | scaled | 0.616 | 0.319 | -0.162 | -0.282 | 0.362 |
| validation | A16658 | raw | 12.0 | 0.816 | 0.102 | 0.026 | 1.013 |
| validation | A16658 | scaled | -0.596 | 0.661 | -0.176 | -0.063 | -0.23 |

## Scaler statistics

| feature | scaler_mean | train_mean | all_agents_mean | scaler_std | train_std_ddof0 | all_agents_std_ddof0 |
|---|---|---|---|---|---|---|
| submission_frequency | 15.9329 | 15.9329 | 15.811 | 6.598 | 6.598 | 6.6231 |
| time_of_day_entropy | 0.7785 | 0.7785 | 0.7782 | 0.0561 | 0.0561 | 0.0564 |
| customer_similarity | 0.1091 | 0.1091 | 0.1092 | 0.0413 | 0.0413 | 0.0428 |
| collusion_score | 0.0333 | 0.0333 | 0.0337 | 0.1178 | 0.1178 | 0.1185 |
| volume_vs_peers | 1.134 | 1.134 | 1.1292 | 0.5268 | 0.5268 | 0.5377 |
