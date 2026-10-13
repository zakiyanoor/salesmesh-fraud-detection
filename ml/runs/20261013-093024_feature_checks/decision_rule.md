# Decision rule for volume_vs_peers (written before any AUC was computed)

Written: 2026-10-13T09:30:24

Keep `volume_vs_peers` as a model feature only if both hold, on TRAINING agents only:
1. its single-feature ROC AUC against the fraud label (all fraud patterns vs legitimate, value = score,
   higher = more suspicious) is above 0.55;
2. its absolute Spearman correlation with each of submission_frequency, time_of_day_entropy, customer_similarity, collusion_score is at most 0.85.

Otherwise drop it. Validation and test labels are not used. Models with and without it are
still compared on validation at Step 9, and both results are reported.
