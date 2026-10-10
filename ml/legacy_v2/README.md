# Legacy v2 scripts (kept for reference, not run)

These are the v2 pipeline scripts as they stood before the v3 rework: `model.py`, `model_lof.py`, `baseline.py`, `evaluate.py`, `run_experiments.py` and `metrics.py`. They were moved here at Step 7 of the v3 rework, and their contents are unchanged.

They were moved for two reasons:
- they read the test split directly, which the v3 test-set guard (`ml/labels_guard.py`) forbids before Step 11;
- they expect the v2 two-way split.

**Their v3 replacements:**
- Step 7: `ml/baselines.py`
- Step 8: `ml/detectors.py` and `ml/train_models.py`
- Step 11: final evaluation
- Step 12: repeated runs

**The deployed v2 artifact stays in place.** `ml/models/isolation_forest_v2.joblib` was produced by `model.py`, and the backend still loads it until Step 13.

The scripts are not importable from `ml/` without path changes, and they do not run against v3 data.
