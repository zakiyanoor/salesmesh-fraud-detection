# Architecture

Moved from the root `README.md` (issue #26). Setup and commands: `SETUP.md`.

## Components

- **Data:** PostgreSQL.
  - The v3 data: agents, agent_identity (fictional, masked in the API), agent_categories, clients and activation records.
  - Detection results: agent_scores, duplicate_evidence, detection_runs, and feature_vectors / fraud_flags for the review workflow.
  - Review decisions and their corrections (write once: database triggers refuse edits and deletes), the admin audit log and administrators.
- **Backend:** Flask REST API with session-based auth, roles and an audit log; SQLAlchemy ORM.
  - **Detection uses the frozen v3 model `lof_v3_4f`:** the scoring bundle from `ml/runs/20261013-100433_explain`, checked against `ml/results/FREEZE.md`, at the validation cutoff of 1.445.
  - The feature code is imported from `ml/`, not copied, and backend scores match the ML pipeline within 1e-9.
  - The duplicate activation rule runs beside the model; each agent gets a `flag_source` of ML, Rule, Both or None, and a `risk_band` of high, review or low.
  - The APScheduler job runs on a configurable interval and reports its status.
  - **Append-only audit log** (a database trigger refuses changes). It records logins, failures, every 401 and 403, account changes, review actions, report downloads and every AI decision (`system:lof_v3_4f`).
  - **Review workflow** (`src/review.py`, issue #28): an analyst proposes an outcome on any flagged agent (model, rule or both); a compliance officer other than the proposer agrees or overrules it; the analyst may withdraw an open proposal; a final decision changes only through a correction, which is a new row. One open proposal per flag (a partial unique index). Overdue after 3 days, never decided automatically. No decision changes a score or a flag.
  - Read-only threat intelligence views, computed once per detection run; admin-only CSV and PDF reports with masked identities and protection against formula injection.
  - Endpoints: `API.md`; changes: `../backend/CHANGES.md`.
- **Frontend:** React and MUI dashboard. It shows each agent's `risk_band` and `flag_source`, and the raw score with its rank in the latest run. Details: `FRONTEND.md`.
- **Deployment** (issue #20, `DEPLOYMENT.md`): Docker Compose on one Linux server. Caddy serves the built frontend and forwards `/api/*` to the API on one origin with automatic HTTPS; the API runs under Gunicorn (one worker, four threads, `TRUST_PROXY=true`); the scheduler runs as its own single process from the same image; PostgreSQL 17 runs in its own container, or a managed database is used instead. The API image holds only the `ml/` files read at run time and never `ml/data`.

## Roles and permissions

| Capability | fraud_analyst | compliance_officer | admin |
|---|---|---|---|
| Read agents, scores, analytics, threat intelligence, run status | yes | yes | yes |
| Propose a review decision; withdraw their own open proposal | yes | no | no |
| Agree with or overrule a proposal; correct a final decision (never their own proposal) | no | yes | no |
| Read the audit log | no | yes | yes |
| Download reports; manage accounts and roles | no | no | yes |

An admin cannot change or deactivate their own account, and the last active admin cannot be removed. Details: `API.md`.

## Repository layout

- `ml/`: synthetic data, the ML pipeline, results (`ml/results/`) and run folders (`ml/runs/`); docs `ml/README.md`, `ml/DATA_CARD.md`, `ml/MODEL_CARD.md`
- `backend/`: Flask API (`src/api.py`), the review rules (`src/review.py`), settings (`src/config.py`), auth, database layer (`src/db.py`, `src/migrate.py`, `src/load_data.py`), detection (`src/scoring_service.py`, `src/ml_bridge.py`, `src/pipeline.py`) and the scheduler (`src/scheduler.py`)
- `docs/`: `API.md` (API reference), `FRONTEND.md`, `SETUP.md`, `DEPLOYMENT.md`, `OPERATIONS.md`, this file, and `screenshots/`
- `deploy/`: the proxy image, the Caddyfile, the production env example and the smoke test; `docker-compose.yml` and `backend/Dockerfile` belong to the same deployment
- `frontend/`: React dashboard
- `.github/workflows/ci.yml`: the ml, backend and frontend tests on every push, the parity and freeze tests inside the built API image, and the Compose stack with the smoke test
