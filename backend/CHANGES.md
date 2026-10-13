# Backend changes

## Sprint 3: v3 database, frozen model and scheduler (issue #4, closes #12)

Branch `sprint-3/backend-database`. The backend now runs on the final v3 synthetic data and the frozen ML model `lof_v3_4f`. The v2 detector is retired.

### Database (`src/db.py`, `src/migrate.py`)

- **New columns:** `agents.account_status`; `activation_records.quality_score` and `commission_kes` (`client_id` and `category` already existed).
- **New tables:**
  - `clients` (with `commission_per_activation_kes`);
  - `agent_identity`: fictional name, phone and national ID, kept separate and never a model input;
  - `agent_categories`;
  - `agent_scores`: per run and agent, with anomaly score, cutoff, model flag, rule flag, `flag_source`, top features, reasons and created_at;
  - `duplicate_evidence`: agent, customer, client, other agent, reason, record ids;
  - `detection_runs`;
  - `data_loads`.
- **`python -m src.migrate`** creates the database and the missing tables, and adds columns with `ADD COLUMN IF NOT EXISTS`. It is safe to run twice; a test runs it twice and inspects the schema.
- **Existing tables are unchanged in shape:** `feature_vectors` and `fraud_flags` keep their columns and are still written each run, so review decisions keep working. `feature_vectors.time_of_day_dist` now holds the v3 `time_of_day_entropy` (same formula), and the API key is unchanged for the frontend.
- **DB settings come from the environment:** `DB_NAME`, `DB_USER`, `DB_HOST` and `DB_PORT`, with the old values as defaults.

### Data loader (`src/load_data.py`)

- **Reads exactly five files** from `ml/data/synthetic`: `clients.csv`, `agents.csv`, `agent_identity.csv`, `agent_categories.csv` and `activation_records.csv`. `labels.csv` and `rings.csv` are refused by name, and a test checks that no other file is opened.
- **Hash check:** each file's sha256 must match `ml/results/FREEZE.md`.
- **Count check:** expected counts are 1000 agents, 135,494 records, 20 clients, 12 categories, 1000 identity rows and 1441 category rows. They are checked on the files and again in the database before commit; a mismatch raises `DataLoadError` and rolls back.
- **One transaction:** an upsert, then removal of rows that are not in the files (for example the v2 agents) with their derived rows. If that would delete review decisions, the load stops unless `--allow-deleting-reviews` is given.
- **Idempotent:** a second run with the same files reports "unchanged"; `--force` reloads anyway.
- **On the development database:** the reload removed the 115 v2 agents with their 115 feature vectors and 115 fraud flags. There were no review decisions. All 16,341 v2 record ids also exist in v3 and were overwritten.

### Scoring (`src/ml_bridge.py`, `src/scoring_service.py`, `src/pipeline.py`)

- **Imported, not copied, from `ml/`:** `feature_engineering.compute_feature_vectors`, `scoring.score_agents` and `baselines.duplicate_activation_counts`.
- **Frozen bundle:** loaded from `ml/runs/20261013-100433_explain/scoring_bundle.joblib`.
  - Its sha256 must match `FREEZE.md`.
  - Its cutoff must match `ml/runs/20261013-093050_selection_s42/operating_point.json` (1.4447993633890617).
  - Its features must be the 4 model features.
- **Analysis period:** from the first record's day to the day after the last record. On the v3 data that is 2026-08-01 to 2026-08-31, the period the model was frozen on.
- **The duplicate activation rule runs beside the model.**
  - Every counted pair gets evidence rows: `shared customer` with the other agent, or `repeat after completed` with the record ids.
  - The evidence must reproduce `ml`'s per-agent counts, or the run fails.
- **`flag_source`** is `Both`, `ML`, `Rule` or `None`. The model flag stays the primary flag: `fraud_flags.flag_status` follows it alone.
- **Each run** writes `detection_runs`, `agent_scores` and `duplicate_evidence`, and updates `feature_vectors` / `fraud_flags` for the period.
- **On the v3 data:** 1000 agents scored; 145 flagged by the model and 102 by the rule; flag_source counts are Both 73, ML 72, Rule 29, None 826; 2334 evidence rows.
- **Parity:** scores match the frozen pipeline outputs for the 300 validation and test agents. The largest difference is 3.3e-15 (tolerance 1e-9), with identical flags and reasons (`tests/test_parity.py`, `tests/test_scoring_service.py`).
- **Retired:** `src/detector.py` (the v2 Isolation Forest, `ml/models/isolation_forest_v2.joblib`), the v2 feature functions in `src/pipeline.py`, and `tests/test_detector.py`. `src.pipeline.run_detection_cycle` now calls the scoring service.

### API (`src/api.py`; reference in `docs/API.md`)

- **`GET /api/agents/<id>`** adds:
  - `account_status`;
  - `identity`, masked;
  - `certifications`;
  - `score`: anomaly score, cutoff, model and rule flags, `flag_source`, top features and reasons;
  - `duplicate_evidence`.
- **`GET /api/flagged-agents`** (still model flags only) and **`GET /api/all-agents`** add `flag_source`.
- **New endpoints:** `GET /api/agent-scores` (latest run, `flag_source` filter, paging), `GET /api/clients` and `GET /api/detection-runs/latest`.
- **`GET /api/analytics`:** the score buckets used 0 to 1 ranges, but LOF scores are about 1 for typical agents and unbounded above, so every agent fell into the top bucket. The buckets are now placed around the cutoff, and the response adds `cutoff` and `flag_sources`.
- **Masking:** phone and national ID are masked in every response, with only the last 3 digits visible (data minimisation, ML change 5). `tests/test_masking.py` calls every GET route and login as both roles and fails on any full value.
- **`/api/detection-runs/latest`** returns only the final error line. The traceback, which contains server paths, stays in the database.

### Scheduler (`src/scheduler.py`, issue #12)

- **The bug:** the job was added with `next_run_time=None`, which APScheduler treats as paused, so it never ran.
- **The fix:** `build_scheduler()` gives the job a real first run (now, or after one interval when `DETECTION_RUN_ON_START=false`). The interval comes from `DETECTION_INTERVAL_MINUTES` (default 1440), with `max_instances=1` and `coalesce=True`.
- **Failures:** a failed run is stored with its error, and the scheduler continues.
- **`tests/test_scheduler.py`:**
  - checks that the job has a first run time;
  - runs a stub job;
  - runs the real detection job through APScheduler on the test database and checks the recorded run and the status endpoint;
  - checks that a failure is reported.

### Tests

- **Separate database:** tests run on `salesmesh_fraud_detection_test` (`DB_NAME`); conftest refuses any database name that does not end in `_test`. A session fixture migrates it, loads the five files, seeds the test accounts and runs one detection cycle.
- **Fixtures:** the hard-coded v2 agent `A1104` is replaced by the `known_agent_id` fixture (the session run's highest-scoring flagged agent).
- **The three named failures, and what changed:**
  - `test_failed_login_is_not_recorded_as_login`: it asserted that the analyst had no audit entries at all, so it failed on entries left by earlier runs (13 in the development database). It now checks that the failed attempt adds no entry.
  - `test_agent_detail_context_lists_only_known_clients_and_categories`: the database held v2 client names; it passes on the v3 data, unchanged except for the fixture.
  - `test_collusion_ring_agents_from_synthetic_data_score_above_every_legit_agent`: it required every strong-ring agent to score above a fixed 0.3, a value that described the v2 data. On v3 the lowest strong-ring agent scores 0.288 and the highest honest agent 0.100. The test now asserts the claim itself, that every strong-ring agent scores above every honest agent, and uses `ml`'s collusion code.
- **New test files:** `test_load_data.py`, `test_scoring_service.py`, `test_parity.py`, `test_masking.py`, `test_scheduler.py`.
- **Rewritten:** `test_pipeline.py`. Its v2 feature tests became the same checks on the imported `ml` collusion code.

### Dependencies

`requirements.txt` gains `python-dotenv` (already imported by `src/db.py`, but missing) and `pytest`.

### Stale files found (none loaded or used; none deleted)

In `ml/data/synthetic/`:

| File | What it is |
|---|---|
| `fraud_flags.csv`, `fraud_flags_lof.csv`, `train_test_split.csv` | v2 leftovers |
| `activation_records_clean.csv` | v3 output of the ML cleaning step (same rows as `activation_records.csv`; not v2) |
| `feature_vectors.csv` | the frozen v3 feature table, hashed in `ml/results/FREEZE.md` (not v2) |
| `split.csv` | the v3 70/15/15 split |
| `labels.csv`, `rings.csv` | ground truth; never read by the application |

Elsewhere: `ml/models/isolation_forest_v2.joblib` (v2 model, no longer used). The backend references none of these in code; `tests/test_scoring_service.py` checks that.

### Known follow-ups

- **Frontend:** `Dashboard.jsx` colours risk with fixed tiers (0.8 high, 0.5 medium) made for the old 0 to 1 scores. With LOF scores nearly every agent shows as high risk. It should use `threshold` and `flag_source` from the API instead.
- **Line endings (fixed in commit `e31f5eb`):** with `core.autocrlf=true`, checkout had rewritten three frozen ML markdown files with CRLF, so 4 ML freeze tests failed.
  - The root `.gitattributes` now pins each hashed file to the line ending it was frozen with: LF for `FREEZE.md`, `acceptance_criteria.md`, `selection_rule.md` and `selection_notes.md`; CRLF for the hashed data files (the CSVs, `operating_point.json` and `data_generation.py`).
  - Binary files (`*.joblib`, `*.png`) are never converted.
  - No stored content changed. All 17 frozen hashes match `FREEZE.md`, and all 185 ML tests pass.
- **Audit:** reading identity is not written to the audit log; consider it if identity becomes viewable beyond the masked form.
