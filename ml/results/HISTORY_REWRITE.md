# History rewrite (24 October 2026)

On 24 October 2026 the commit history of this repository was rewritten to correct commit message metadata (issue #26).

## What changed

- **Commit messages:** in 64 commit messages, trailer lines that did not belong to the project were removed. The rest of each message is unchanged.
- **One file:** `ml/results/PR_DESCRIPTION.md` lost one line, and the blank line under it, in all of its history.
- **Nothing else:** the file contents of every branch are otherwise unchanged. At each branch tip and tag, the old and new trees differ only in that file. Every branch has the same number of commits as before.

## What did not change

The frozen model, data and results are therefore unchanged:
- every file hashed in `results/FREEZE.md`, and every run folder in `ml/runs/`, has the same bytes as before;
- `tests/test_freeze.py` and the ml, backend and frontend test suites pass on the rewritten history.

## Effect on commit hashes

- **Changed:** a rewritten commit gets a new hash, and so does every commit after it. 91 of 110 commits have new hashes.
- **Unchanged:** these branches keep their hashes, and the signatures GitHub added to their merge commits: `sprint-1/data-generation`, `sprint-2/model-comparison`, `sprint-5/testing-scheduler`, `sprint-6/collusion-detection`, `feature/collusion-detection`.
- **Rewritten branches:** `main`, `sprint-3/backend-database`, `sprint-4/frontend-dashboard`, `sprint-7/hybrid-hardening`, `feature/3-ml-three-way-split`.
- **Rewritten tags:** `ml-v3-evaluated` and `ml-v3-frozen`, with the same names and messages.
- **Records left as they are:** the documents and run records written before the rewrite still cite the old hashes. They were not edited:
  - `run_info.json` records the commit a run was made from;
  - a changelog records the history as it was.

  The table below maps each old hash cited in the repository to its new hash. A backup of the history before the rewrite is kept by the author.

## Old hashes cited in the repository

The table lists every old hash cited in the repository. It covers 6 short hashes in the documents (`backend/CHANGES.md`, `ml/results/CHANGES.md`, `ml/results/STRESS_TEST_RESULTS.md`), and the full hashes in the `git_commit` field of 48 run records (24 in `ml/runs/`, 24 in `ml/results/archive_v3a/runs/`). Hashes are shown with their first 7 characters.

| Old commit | New commit | Cited in |
|---|---|---|
| `e31f5eb` | `31546e4` | `backend/CHANGES.md` |
| `ac3df5d` | `85b4be7` | `ml/results/CHANGES.md`; `git_commit` in `ml/runs/<run>/run_info.json` for `20261013-091128_datagen_s42` |
| `bdcaca2` | `05230d9` | `ml/results/CHANGES.md`; `git_commit` in `ml/runs/<run>/run_info.json` for `20261013-092936_clean`, `20261013-092952_split_s42`, `20261013-092959_eda_s0`, `20261013-093008_features`, `20261013-093024_feature_checks`, `20261013-093031_preprocess_s0`, `20261013-093033_baselines`, `20261013-093036_models_default_s42`, `20261013-093050_selection_s42`, `20261013-093222_learning_curve`, `20261013-093225_explain`, `20261013-093236_system_checks_s101`, `20261013-093332_system_checks_s101` |
| `b6d69cc` | `541495e` | `ml/results/CHANGES.md`; `git_commit` in `ml/runs/<run>/run_info.json` for `20261013-094740_explain`, `20261013-094743_system_checks_s101`, `20261013-095040_cross_validation_s42`, `20261013-095059_union_reference`, `20261013-095135_retrain_s42`, `20261013-100433_explain`, `20261013-100436_system_checks_s101` |
| `19917bc` | `1aa8b63` | `ml/results/CHANGES.md`; `git_commit` in `ml/runs/<run>/run_info.json` for `20261013-103859_final_evaluation_s42`, `20261013-104305_stability` |
| `1f812e7` | `fb81ea0` | `ml/results/CHANGES.md`; `ml/results/STRESS_TEST_RESULTS.md`; `git_commit` in `ml/runs/<run>/run_info.json` for `20261022-185935_stress_test_s201` |
| `812bb05` | `1f01027` | `git_commit` in `ml/results/archive_v3a/runs/<run>/run_info.json` for `20261011-010944_datagen_s42` |
| `79237e1` | `fd5ad94` | `git_commit` in `ml/results/archive_v3a/runs/<run>/run_info.json` for `20261011-015537_datagen_s42` |
| `e070367` | `d8b9f97` | `git_commit` in `ml/results/archive_v3a/runs/<run>/run_info.json` for `20261011-020933_clean`, `20261011-021228_eda_s0`, `20261011-021303_eda_s0` |
| `adf590a` | `95285f8` | `git_commit` in `ml/results/archive_v3a/runs/<run>/run_info.json` for `20261011-022151_datagen_s42`, `20261011-022249_datagen_s42`, `20261011-022427_clean`, `20261011-022430_eda_s0` |
| `b5b9c4c` | `0c568b5` | `git_commit` in `ml/results/archive_v3a/runs/<run>/run_info.json` for `20261011-023607_split_s42`, `20261011-023639_features`, `20261011-023802_feature_checks`, `20261011-023846_preprocess_s0` |
| `f89d2f6` | `8690970` | `git_commit` in `ml/results/archive_v3a/runs/<run>/run_info.json` for `20261011-024811_baselines`, `20261011-024834_models_default_s42` |
| `8eceec5` | `46b59dd` | `git_commit` in `ml/results/archive_v3a/runs/<run>/run_info.json` for `20261011-025652_selection_s42`, `20261011-030156_learning_curve`, `20261011-030202_learning_curve` |
| `13fd8a0` | `726c9d2` | `git_commit` in `ml/results/archive_v3a/runs/<run>/run_info.json` for `20261011-031206_selection_s42`, `20261011-031554_explain`, `20261011-031637_explain` |
| `a1a6cda` | `e27f6f8` | `git_commit` in `ml/results/archive_v3a/runs/<run>/run_info.json` for `20261011-032329_explain`, `20261011-032400_explain`, `20261011-032454_system_checks_s101` |
