# SalesMesh Fraud Detection API

Flask REST API in `backend/src/api.py`, served by `python -m src.api` from `backend/` (port 5000). The React frontend at `http://localhost:5173` is the only allowed CORS origin, with credentials.

## Conventions

- **Auth:** session cookie set by `POST /api/login`.
  - **Login** means any logged-in administrator (roles `fraud_analyst` or `compliance_officer`).
  - **Analyst** means `fraud_analyst` only; **Compliance** means `compliance_officer` only.
  - Without a session the API returns `401 {"error": "Authentication required"}`; with the wrong role it returns `403`.
- **Rate limit:** `POST /api/login` is limited to 5 requests per minute per IP (`429` after that).
- **Scores:** `suspicion_score` and `anomaly_score` are Local Outlier Factor anomaly scores from the frozen model `lof_v3_4f`.
  - A typical agent scores about 1, and scores have no upper bound.
  - An agent is flagged when its score is at or above the cutoff (`threshold`, 1.444799), which was chosen on validation.
  - Scores are **not** probabilities.
- **Flags:** the model flag is the primary flag (`fraud_flags`, `flag_status`). The duplicate activation rule is reported beside it.
  - `flag_source` is `ML` (model only), `Rule` (rule only), `Both` or `None`.
  - The rule flags an agent when one of its (customer, client) pairs is also used by another agent, or is repeated after a completed activation.
- **Personal data:** identities are fictional and never a model input. **Phone and national ID numbers are masked in every response; only the last 3 digits are visible.** `backend/tests/test_masking.py` checks every GET route.
- **Timestamps:** ISO 8601, naive local time (Africa/Nairobi) for data; UTC for audit and run times.
- **Example values** below were captured from the API on the v3 data; lists are shortened. The review-decision examples use illustrative ids, because no decisions existed when the examples were captured.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/login` | none | Start a session |
| POST | `/api/logout` | none | End the session |
| GET | `/api/flagged-agents` | Login | Agents the model flagged |
| GET | `/api/all-agents` | Login | Every agent with its status and features |
| GET | `/api/agents/<agent_id>` | Login | One agent: features, flag, score, rule evidence, identity (masked) |
| GET | `/api/agent-scores` | Login | Latest run's scores, filterable by `flag_source` |
| GET | `/api/analytics` | Login | Platform statistics |
| GET | `/api/clients` | Login | Client reference list |
| GET | `/api/detection-runs/latest` | Login | Status of the last detection run |
| POST | `/api/review-decisions` | Analyst | Propose a review decision |
| POST | `/api/review-decisions/<decision_id>/confirm` | Compliance | Confirm someone else's decision |
| GET | `/api/review-decisions` | Login | Review decisions, newest first |
| GET | `/api/audit-log` | Login | Admin action audit trail |
| GET | `/api/health` | none | Health check |

### POST /api/login

Body: `{"username": "...", "password": "..."}`. Records a `login` audit entry; a failed login records nothing.

```json
{"message": "Login successful", "role": "fraud_analyst", "username": "analyst_01"}
```

Errors: `400` (missing fields), `401` (wrong credentials), `429` (rate limit).

### POST /api/logout

Records a `logout` audit entry when a session exists.

```json
{"message": "Logged out successfully"}
```

### GET /api/flagged-agents

The agents the **model** flagged in each agent's latest analysis period, highest score first. Agents flagged only by the rule are not listed here; see `/api/agent-scores?flag_source=Rule`.

```json
{
  "count": 145,
  "flagged_agents": [
    {"agent_id": "A63269", "analysis_period": "2026-08", "flag_id": "FL50ed0b2a", "flag_source": "ML",
     "flag_status": "flagged", "model_version": "lof_v3_4f", "region": "Nairobi",
     "suspicion_score": 9.804, "threshold": 1.444799}
  ]
}
```

### GET /api/all-agents

Every agent once, with its latest features and status. `time_of_day_dist` holds the v3 `time_of_day_entropy`; the key is kept for the frontend.

```json
{
  "count": 1000,
  "agents": [
    {"agent_id": "A10053", "account_status": "active", "region": "Kericho", "status": "clear", "flag_source": "None",
     "suspicion_score": 1.077, "submission_frequency": 12, "time_of_day_dist": 0.821,
     "customer_similarity": 0.102, "collusion_score": 0.0}
  ]
}
```

### GET /api/agents/<agent_id>

Path parameter: `agent_id` (for example `A35485`). `404` if the agent does not exist.

- `features`: the 4 model inputs.
- `score`: the latest successful run's model and rule result.
- `duplicate_evidence`: one entry per (customer, client) pair behind the rule, with the agent's record ids.
- `context`: clients and categories the agent worked in.
- `identity`: fictional; phone and national ID masked.

```json
{
  "agent_id": "A35485",
  "region": "Elgeyo-Marakwet",
  "account_status": "active",
  "registration_timestamp": "2026-06-11T20:56:24",
  "identity": {"full_name": "Agnes Omondi", "phone_number": "**********067", "national_id_number": "*****291"},
  "certifications": [
    {"category": "e-commerce", "certification_status": "certified", "certified_at": "2026-08-01T01:24:24"},
    {"category": "education", "certification_status": "certified", "certified_at": "2026-06-14T03:08:46"}
  ],
  "features": {"submission_frequency": 21, "time_of_day_dist": 0.788, "customer_similarity": 0.103, "collusion_score": 0.464},
  "flag": {"flag_id": "FL93b6b96d", "flag_status": "flagged", "model_version": "lof_v3_4f", "suspicion_score": 5.564},
  "score": {
    "run_id": "RUN202610131505039d5d93", "model_version": "lof_v3_4f",
    "anomaly_score": 5.563827, "threshold": 1.444799, "flagged": true,
    "rule_flagged": true, "duplicate_pairs": 19, "flag_source": "Both",
    "top_features": ["collusion_score", "submission_frequency", "customer_similarity"],
    "reasons": "46% of customers also used by other agents vs typical 0% (higher than 96 percent of training agents); busiest 24 hours: 21 submissions vs typical 14 (higher than 82 percent of training agents)",
    "scored_at": "2026-10-13T15:05:11.267904"
  },
  "duplicate_evidence": [
    {"customer_id": "CUST16131148", "client_id": "CL09", "other_agent_id": null,
     "reason": "repeat after completed", "record_ids": ["R9941", "R100690"]}
  ],
  "context": {"client_ids": ["CL09", "CL15"], "categories": ["e-commerce", "education"]}
}
```

`reason` in `duplicate_evidence` is `shared customer` (with `other_agent_id`) or `repeat after completed`.

### GET /api/agent-scores

Scores from the latest successful detection run, highest first.

Query parameters:
- `flag_source`: `ML`, `Rule`, `Both` or `None` (optional; anything else returns `400`);
- `limit`: default 100, maximum 1000;
- `offset`: default 0.

```json
{
  "run_id": "RUN202610131505039d5d93", "model_version": "lof_v3_4f", "threshold": 1.444799,
  "total": 73, "count": 2, "offset": 0,
  "scores": [
    {"agent_id": "A35485", "anomaly_score": 5.563827, "threshold": 1.444799, "flagged": true, "rule_flagged": true,
     "duplicate_pairs": 19, "flag_source": "Both", "model_version": "lof_v3_4f", "run_id": "RUN202610131505039d5d93",
     "top_features": ["collusion_score", "submission_frequency", "customer_similarity"],
     "reasons": "46% of customers also used by other agents vs typical 0% (...)", "scored_at": "2026-10-13T15:05:11.267904"}
  ]
}
```

### GET /api/analytics

- **Score buckets** are placed around the cutoff, because LOF scores are not 0 to 1: `< 1.1`, `1.1-1.3`, `1.3-cutoff`, `cutoff (1.445)-2.0`, `>= 2.0`.
- **`flag_sources`** counts the latest run's agents by `flag_source`.

```json
{
  "cutoff": 1.444799,
  "flag_sources": [{"flag_source": "ML", "count": 72}, {"flag_source": "Rule", "count": 29},
                   {"flag_source": "Both", "count": 73}, {"flag_source": "None", "count": 826}],
  "score_distribution": [{"bucket": "< 1.1", "count": 572}, {"bucket": "1.1-1.3", "count": 210}],
  "region_breakdown": [{"region": "Kericho", "flagged": 6, "total": 25}],
  "platform_averages": {"submission_frequency": 15.8, "time_of_day_dist": 0.778, "customer_similarity": 0.109}
}
```

### GET /api/clients

```json
{"count": 20, "clients": [{"client_id": "CL01", "name": "Client 01", "category": "banking", "commission_per_activation_kes": 250}]}
```

### GET /api/detection-runs/latest

Status of the most recent detection run, whatever its outcome (scheduler, manual or test). `error` is the final error line only; the full traceback stays in the `detection_runs` table. `{"run": null}` if no run exists.

```json
{
  "run": {
    "run_id": "RUN20261013150708e4c311", "trigger": "manual", "status": "succeeded",
    "started_at": "2026-10-13T15:07:08.208079", "finished_at": "2026-10-13T15:07:16.636720",
    "model_version": "lof_v3_4f", "threshold": 1.444799,
    "agents_scored": 1000, "flagged_count": 145, "rule_flagged_count": 102, "both_count": 73, "error": null
  }
}
```

`status` is `running`, `succeeded` or `failed`. A failed run has, for example, `"error": "RuntimeError: no activation records to score; load the data first"`.

### POST /api/review-decisions

**Analyst only.** Body: `{"flag_id": "FL93b6b96d", "decision_outcome": "confirmed_fraud"}`. Creates a decision in `pending_confirmation` and records a `propose_decision` audit entry.

```json
{"message": "Review decision proposed; awaiting compliance confirmation", "decision_id": "RD1a2b3c4d", "status": "pending_confirmation"}
```

Errors: `400` (missing fields), `403` (wrong role), `404` (unknown flag).

### POST /api/review-decisions/<decision_id>/confirm

**Compliance only.** Confirms a pending decision proposed by a different admin, and records a `confirm_decision` audit entry.

```json
{"message": "Review decision confirmed", "decision_id": "RD1a2b3c4d", "status": "confirmed", "confirmed_by": "ADM_COMPLIANCE_01"}
```

Errors: `403` (wrong role, or confirming your own proposal), `404` (unknown decision), `409` (already confirmed).

### GET /api/review-decisions

```json
{"count": 1, "decisions": [{"decision_id": "RD1a2b3c4d", "agent_id": "A35485", "reviewer_id": "ADM_ANALYST_01",
  "decision_outcome": "confirmed_fraud", "decision_timestamp": "2026-10-13T15:10:00", "status": "confirmed",
  "confirmed_by": "ADM_COMPLIANCE_01"}]}
```

### GET /api/audit-log

Newest first.

```json
{"count": 1, "entries": [{"log_id": "AL8d4c1a70...", "admin_id": "ADM_ANALYST_01", "action": "login",
  "target_agent_id": null, "timestamp": "2026-10-13T15:07:57.579492"}]}
```

### GET /api/health

```json
{"status": "ok"}
```

## Operations

All commands run from `backend/`.

| Command | What it does |
|---|---|
| `python -m src.migrate` | Creates the database and tables if missing and adds new columns; safe to run any number of times |
| `python -m src.load_data` | Reloads the five v3 files from `ml/data/synthetic`. Checks their hashes against `ml/results/FREEZE.md` and the row counts (1000 / 135,494 / 20 clients / 12 categories); reports "unchanged" when nothing changed; never reads `labels.csv` or `rings.csv` |
| `python -m src.pipeline` | One detection run with the frozen model |
| `python -m src.scheduler` | Runs detection now and then every `DETECTION_INTERVAL_MINUTES` (default 1440); set `DETECTION_RUN_ON_START=false` to wait one interval first |
| `python -m src.auth` | Creates the demo accounts (demo and test only) |
| `pytest` | Runs the tests on `salesmesh_fraud_detection_test`, never on the development database |
