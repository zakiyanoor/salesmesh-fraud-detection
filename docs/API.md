# SalesMesh Fraud Detection API

Flask REST API in `backend/src/api.py`, served by `python -m src.api` from `backend/` (port 5000). The React frontend at `http://localhost:5173` is the only allowed CORS origin, with credentials.

## Conventions

- **Auth:** session cookie set by `POST /api/login`.
  - The account is re-read on every request, so a deactivation or role change takes effect at once.
  - Without a valid session the API returns `401` (`"Authentication required"` or `"Account is deactivated"`); with the wrong role it returns `403`.
  - An account whose role is not one of the three below is refused at login and on every request.
- **Rate limit:** `POST /api/login` is limited to 5 requests per minute per IP (`429` after that).
- **Scores:** `suspicion_score` and `anomaly_score` are Local Outlier Factor anomaly scores from the frozen model `lof_v3_4f`.
  - A typical agent scores about 1, and scores have no upper bound.
  - An agent is flagged when its score is at or above the cutoff (`threshold`, 1.444799), which was chosen on validation.
  - Scores are **not** probabilities.
  - `score_percentile` (issue #26) is reported beside the score on every agent payload. It is the share of agents in the same detection run with a strictly lower score, from 0 to 100, rounded to 1 decimal place; tied scores share a percentile.
    - With 1000 agents, the top agent is at 99.9.
    - It is a rank within the latest run, not a probability, and it can change when the scored population changes.
    - It is `null` for an agent the latest run did not score.
- **Flags:** the model flag is the primary flag (`fraud_flags`, `flag_status`). The duplicate activation rule is reported beside it.
  - `flag_source` is `ML` (model only), `Rule` (rule only), `Both` or `None`.
  - The rule flags an agent when one of its (customer, client) pairs is also used by another agent, or is repeated after a completed activation.
- **Personal data:** identities are fictional and never a model input.
  - **Phone and national ID numbers are masked everywhere, with only the last 3 digits visible.** Report downloads also mask names (initials only).
  - Audit entries store the request IP masked to its first two parts (`10.20.*.*`).
  - `backend/tests/test_masking.py` checks every GET route as every role.
- **Timestamps:** ISO 8601, naive local time (Africa/Nairobi) for data; UTC for audit and run times.
- **Example values** below were captured from the API on the v3 data; lists are shortened. The review-decision examples use illustrative ids, because no decisions existed when the examples were captured.

## Roles and permissions

Three roles, with separation of duties: whoever proposes a review decision cannot confirm it, and the admin who manages accounts and reports takes no part in reviews.

| Capability | fraud_analyst | compliance_officer | admin |
|---|---|---|---|
| Read agents, scores, analytics, clients, review decisions, run status | yes | yes | yes |
| Threat intelligence views | yes | yes | yes |
| Propose a review decision | **yes** | no | no |
| Confirm a review decision (proposed by someone else) | no | **yes** | no |
| Read the audit log | no | yes | yes |
| Download reports (CSV, PDF) | no | no | **yes** |
| List accounts, change roles, deactivate or reactivate accounts | no | no | **yes** |

**Account rules:**
- An admin cannot change the role of, or deactivate, their own account (`403`).
- The last active admin can never be demoted or deactivated (`409`). The check locks the active admin rows, so two admins cannot remove each other at the same moment.

## risk_band

Every agent payload (`/api/flagged-agents`, `/api/all-agents`, `/api/agent-scores`, `/api/agents/<id>`) carries `risk_band`. It replaces the frontend's fixed 0.8 / 0.5 tiers, which assumed 0 to 1 scores.

| risk_band | Meaning |
|---|---|
| `high` | flagged by the model: `flag_source` is `ML` or `Both` |
| `review` | flagged by the duplicate rule alone (`Rule`), or `anomaly_score` at or above **1.3** but below the cutoff |
| `low` | everything else |

It is `null` for an agent that has not been scored.

## Audit log

`admin_action_log` is **append only**:
- no endpoint updates or deletes entries;
- a PostgreSQL trigger refuses `UPDATE`, `DELETE` and `TRUNCATE`;
- only the schema migration's own backfill of the new columns may touch existing rows.

Each entry has:
- `actor`: an `admin_id`, `anonymous` (not logged in) or `system:lof_v3_4f`;
- `actor_type`: `user` or `system`;
- `category`, `action`, `target_agent_id`, `details` (JSON) and the masked `request_ip`.

| Category | Actions | Details |
|---|---|---|
| `authentication` | `login`, `login_failure`, `logout` | `username`, `role`; for failures `reason` (`invalid credentials`, `account deactivated`, `unknown role`); failures have actor `anonymous` |
| `authorization` | `access_denied` (every `401` and `403`, except a `401` on `GET /api/me` with no session) | `route`, `method`, `role`, `status`, `reason` |
| `review` | `propose_decision`, `confirm_decision` | `decision_id`, `flag_id`, `notes`, and `decision_outcome` (proposal) or `proposed_by` (confirmation) |
| `admin` | `role_change`, `account_deactivated`, `account_reactivated`, `password_reset` (local recovery, actor `local:<OS user>`) | `target_admin_id`, `target_username`, `old_role` / `new_role` or `role`; `channel` (`cli` or `local recovery`) |
| `report` | `report_download` | `report`, `filename`, `filters`, `row_count`, `bytes`, `sha256` of the file sent, plus `run_id`, `cap`, `load_id` or `data_hash` |
| `ai_decision` | `ai_detection_run` (one per run, also when it fails); `ai_flag` (per agent whose `flag_source` changed since the previous successful run, or newly flagged) | run: `run_id`, `status`, `trigger`, `model_version`, `threshold`, counts, `flag_changes`, `error`; flag: `change` (`newly flagged`, `cleared`, `flag source changed`), `previous_flag_source`, `flag_source`, `anomaly_score`, `threshold`, `top_features`, `reasons`, `model_version` |

## Endpoints

| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/api/login` | none | Start a session |
| POST | `/api/logout` | none | End the session |
| GET | `/api/me` | all | Username and role of the current session |
| GET | `/api/flagged-agents` | all | Agents the model flagged |
| GET | `/api/all-agents` | all | Every agent with status, features and `risk_band` |
| GET | `/api/agents/<agent_id>` | all | One agent: features, flag, score, rule evidence, identity (masked) |
| GET | `/api/agent-scores` | all | Latest run's scores, filterable by `flag_source` |
| GET | `/api/analytics` | all | Platform statistics |
| GET | `/api/clients` | all | Client reference list |
| GET | `/api/detection-runs/latest` | all | Status of the last detection run |
| GET | `/api/threat-intelligence/summary` | all | Counts, rates, commission and top features of flagged agents |
| GET | `/api/threat-intelligence/by-region` | all | Flagged agents per region; top 10 by flagged rate |
| GET | `/api/threat-intelligence/by-client` | all | Flagged agents' activations per client |
| GET | `/api/threat-intelligence/by-category` | all | Flagged agents' activations per category |
| GET | `/api/threat-intelligence/timeline` | all | Daily activations, flagged agents against others |
| GET | `/api/threat-intelligence/customer-sharing` | all | Customers shared by agents, and clusters of connected agents |
| GET | `/api/threat-intelligence/ring-candidates` | all | Groups of model-flagged agents that share at least 3 customers |
| POST | `/api/review-decisions` | fraud_analyst | Propose a review decision |
| POST | `/api/review-decisions/<decision_id>/confirm` | compliance_officer | Confirm someone else's decision |
| GET | `/api/review-decisions` | all | Review decisions, newest first |
| GET | `/api/audit-log` | admin, compliance_officer | Audit trail, filtered and paged |
| GET | `/api/reports/flagged-agents.csv` | admin | Flagged agents of the latest run (masked) |
| GET | `/api/reports/audit-log.csv` | admin | Audit entries as CSV (same filters) |
| GET | `/api/reports/detection-summary.pdf` | admin | One-page detection summary |
| GET | `/api/admin/accounts` | admin | List accounts |
| PATCH | `/api/admin/accounts/<admin_id>/role` | admin | Change an account's role |
| POST | `/api/admin/accounts/<admin_id>/deactivate` | admin | Deactivate an account |
| POST | `/api/admin/accounts/<admin_id>/reactivate` | admin | Reactivate an account |
| GET | `/api/health` | none | Health check |

### POST /api/login

Body: `{"username": "...", "password": "..."}`. Records a `login` entry (category `authentication`). A failure records `login_failure` with actor `anonymous`, the username tried and the reason.

```json
{"message": "Login successful", "role": "fraud_analyst", "username": "analyst_01"}
```

Errors: `400` (missing fields), `401` (wrong credentials, deactivated account or an account without a valid role), `429` (rate limit).

### POST /api/logout

Records a `logout` audit entry when a session exists.

```json
{"message": "Logged out successfully"}
```

### GET /api/me

The username and role of the logged-in account, read fresh on every request, so a role change shows at once. Nothing else is returned (no account id, no password hash). Not audited, like the other reads.

- **A `401` with no session at all** (nobody logged in, or after logout) writes **no** audit entry: the frontend calls this to ask whether anyone is logged in, which is not a security event.
- **A `401` for a deactivated account** is recorded as `access_denied` with that account as the actor, as on every protected route.
- Every other denied request, on every route, is recorded exactly as before.

```json
{"username": "analyst_01", "role": "fraud_analyst"}
```

Errors: `401` (`"Authentication required"` without a session, `"Account is deactivated"` for a deactivated account), `403` (an account without a valid role).

### GET /api/flagged-agents

The agents the **model** flagged in each agent's latest analysis period, highest score first. Agents flagged only by the rule are not listed here; see `/api/agent-scores?flag_source=Rule`.

```json
{
  "count": 145,
  "flagged_agents": [
    {"agent_id": "A63269", "analysis_period": "2026-08", "flag_id": "FL50ed0b2a", "flag_source": "ML", "risk_band": "high",
     "flag_status": "flagged", "model_version": "lof_v3_4f", "region": "Nairobi",
     "suspicion_score": 9.804, "score_percentile": 99.9, "threshold": 1.444799}
  ]
}
```

### GET /api/all-agents

Every agent once, with its latest features and status. `time_of_day_dist` holds the v3 `time_of_day_entropy`; the key is kept for the frontend.

```json
{
  "count": 1000,
  "agents": [
    {"agent_id": "A10053", "account_status": "active", "region": "Kericho", "status": "clear", "flag_source": "None", "risk_band": "low",
     "suspicion_score": 1.077, "score_percentile": 51.5, "submission_frequency": 12, "time_of_day_dist": 0.821,
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
  "risk_band": "high",
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
    "anomaly_score": 5.563827, "score_percentile": 98.9, "threshold": 1.444799, "flagged": true,
    "rule_flagged": true, "duplicate_pairs": 19, "flag_source": "Both", "risk_band": "high",
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
    {"agent_id": "A35485", "anomaly_score": 5.563827, "score_percentile": 98.9, "threshold": 1.444799, "flagged": true, "rule_flagged": true,
     "duplicate_pairs": 19, "flag_source": "Both", "risk_band": "high", "model_version": "lof_v3_4f", "run_id": "RUN202610131505039d5d93",
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

**Analyst only.** Body: `{"flag_id": "FL93b6b96d", "decision_outcome": "confirmed_fraud", "notes": "Shares customers with two agents in Kisumu."}`. Creates a decision in `pending_confirmation` and records a `propose_decision` audit entry whose details hold the notes.

**`decision_outcome` (required):** exactly `"confirmed_fraud"` or `"legitimate"` (case-sensitive, no surrounding spaces). Anything else returns `400` with "decision_outcome must be one of ['confirmed_fraud', 'legitimate'], got ..." and writes nothing (no decision, no audit entry).

**`notes` (required, issue #13):**
- a string, trimmed, 1 to 1000 characters after trimming;
- plain text: newlines and tabs are allowed, other control characters are refused, and a Windows line break (CR LF) is stored as LF. It is stored as written, never as HTML;
- seven or more digits in a row (single spaces allowed between them, and not straight after a letter or digit) are masked like phone numbers, keeping the last 3, so a phone or national ID typed into a note is never stored in full. Dates such as `2026-10-14` and ids such as `CUST12345678` are left alone.

```json
{"message": "Review decision proposed; awaiting compliance confirmation", "decision_id": "RD1a2b3c4d", "status": "pending_confirmation",
 "notes": "Shares customers with two agents in Kisumu."}
```

Errors: `400` (missing `flag_id` or `decision_outcome`; `decision_outcome` not one of the two values; `notes` missing or null: "notes is required: give a short plain-text reason for the decision"; "notes must not be empty"; "notes must be a string"; "notes must be at most 1000 characters (got N)"; "notes must be plain text ..."), `403` (wrong role), `404` (unknown flag).

### POST /api/review-decisions/<decision_id>/confirm

**Compliance only.** No body. Confirms a pending decision proposed by a different admin, and records a `confirm_decision` audit entry whose details repeat the proposal's notes.

```json
{"message": "Review decision confirmed", "decision_id": "RD1a2b3c4d", "status": "confirmed", "confirmed_by": "ADM_COMPLIANCE_01",
 "notes": "Shares customers with two agents in Kisumu."}
```

Errors: `403` (wrong role, or confirming your own proposal), `404` (unknown decision), `409` (already confirmed).

### GET /api/review-decisions

```json
{"count": 1, "decisions": [{"decision_id": "RD1a2b3c4d", "agent_id": "A35485", "reviewer_id": "ADM_ANALYST_01",
  "decision_outcome": "confirmed_fraud", "decision_timestamp": "2026-10-13T15:10:00", "status": "confirmed",
  "confirmed_by": "ADM_COMPLIANCE_01", "notes": "Shares customers with two agents in Kisumu."}]}
```

`notes` is `null` for decisions recorded before notes existed; `confirmed_by` is `null` until a decision is confirmed.

### GET /api/audit-log

**admin and compliance_officer.** Newest first. Event types are in "Audit log" above.

Query parameters (all optional):
- `category`: one of the six categories (anything else returns `400`);
- `actor`: exact actor, for example `ADM_ADMIN_01`, `anonymous` or `system:lof_v3_4f`;
- `agent_id`: the target agent;
- `date_from`, `date_to`: `YYYY-MM-DD` or an ISO datetime; a date in `date_to` includes that whole day;
- `limit`: default 100, maximum 1000;
- `offset`: default 0.

`admin_id` repeats `actor` for older clients.

```json
{
  "total": 1, "count": 1, "offset": 0, "limit": 2, "filters": {"category": "ai_decision"},
  "entries": [{
    "log_id": "AL4789db6c9d634e58bb2045d130c6876c", "timestamp": "2026-10-13T17:26:34.406792",
    "actor": "system:lof_v3_4f", "admin_id": "system:lof_v3_4f", "actor_type": "system",
    "category": "ai_decision", "action": "ai_detection_run", "target_agent_id": null, "request_ip": null,
    "details": {"run_id": "RUN20261013172621c4f8ca", "status": "succeeded", "trigger": "manual",
                "model_version": "lof_v3_4f", "threshold": 1.4447993633890617, "agents_scored": 1000,
                "flagged_count": 145, "rule_flagged_count": 102, "both_count": 73, "flag_changes": 0}
  }]
}
```

### Threat intelligence

**All roles.** Read only, from the latest successful detection run; no label is used.
- "Flagged" means flagged by the model (`flag_source` `ML` or `Both`). `rule_flagged` counts the duplicate rule.
- Every response starts with `"run": {"run_id", "model_version", "threshold", "finished_at"}`.
- Each view returns `404` until a successful run exists.

#### GET /api/threat-intelligence/summary

- `commission_kes`: commission on the records of flagged agents (`flagged_agents`), and of agents flagged by the model or the rule (`any_flag_agents`), with their shares of the total.
- `top_features`: counts each feature as the first of an agent's top features (`as_top_feature`) and anywhere in the top three (`in_top_three`), over flagged agents.

```json
{
  "agents_scored": 1000, "flagged": 145, "flagged_rate": 0.145, "rule_flagged": 102,
  "flag_sources": {"ML": 72, "Rule": 29, "Both": 73, "None": 826},
  "risk_bands": {"high": 145, "review": 89, "low": 766},
  "commission_kes": {"total": 17232310, "flagged_agents": 3701730, "flagged_share": 0.214813,
                     "any_flag_agents": 4283020, "any_flag_share": 0.248546},
  "top_features": {"as_top_feature": [{"feature": "collusion_score", "agents": 70}, {"feature": "customer_similarity", "agents": 47}],
                   "in_top_three": [{"feature": "time_of_day_entropy", "agents": 123}, {"feature": "submission_frequency", "agents": 117}]}
}
```

#### GET /api/threat-intelligence/by-region

All 47 regions, alphabetically. `top_by_flagged_rate` holds the 10 highest flagged rates among regions with at least 5 agents.

```json
{
  "regions": [{"region": "Baringo", "agents": 18, "flagged": 1, "rule_flagged": 1, "flagged_rate": 0.055556}],
  "top_by_flagged_rate": [{"region": "Lamu", "agents": 5, "flagged": 2, "rule_flagged": 1, "flagged_rate": 0.4}],
  "min_agents_for_top": 5
}
```

#### GET /api/threat-intelligence/by-client and /by-category

Per client (20) or per category (12):
- `activations`;
- `flagged_activations`: activations made by flagged agents;
- `flagged_agents`;
- `flagged_share_of_activations`;
- `share_of_all_flagged_activations`.

Clients also carry `name` and `category`.

```json
{"clients": [{"client_id": "CL01", "name": "Client 01", "category": "banking", "activations": 11577,
              "flagged_activations": 3081, "flagged_agents": 24, "flagged_share_of_activations": 0.266131,
              "share_of_all_flagged_activations": 0.111489}]}
```

#### GET /api/threat-intelligence/timeline

One entry per day from the first to the last record, including days without activity.

```json
{"first_day": "2026-08-01", "last_day": "2026-08-30",
 "days": [{"date": "2026-08-01", "flagged_agents": 965, "other_agents": 3534}]}
```

#### GET /api/threat-intelligence/customer-sharing

- `customers`: customers that more than one agent activated for the same client (from `duplicate_evidence`).
- `clusters`: groups of agents connected through such shared customers (connected components).
- Each list is capped at 50 (`limits`). `shared_customers` and `clusters_total` give the full counts.

```json
{
  "shared_customers": 279, "clusters_total": 12, "limits": {"customers": 50, "clusters": 50},
  "customers": [{"customer_id": "CUST23683207", "agent_count": 4, "agent_ids": ["A23396", "A62923", "A72493", "A88135"], "client_ids": ["CL01", "CL05"]}],
  "clusters": [{"size": 3, "agent_ids": ["A57819", "A80697", "A95717"], "client_ids": ["CL01", "CL02"],
                "customer_count": 33, "flagged_agents": 3}]
}
```

#### GET /api/threat-intelligence/ring-candidates

Ring candidates (issue #26), by the Step 11 rule in `ml/final_evaluation.py` (`ring_candidates`, `RING_MIN_SHARED_CUSTOMERS` 3), unchanged. No label is used.

**The rule:**
1. Start from the agents the model flagged in the latest run (`flag_source` `ML` or `Both`). Agents flagged by the rule alone are not included.
2. Two of them are linked when they share at least 3 distinct customers, across all their activation records and any client.
3. Linked agents are joined transitively into groups. Every group of 2 or more agents is a candidate.

A candidate is a lead for review, not a confirmed ring.

**Differences from `customer-sharing`:** that view links any agents, flagged or not, through a single shared (customer, client) pair from the duplicate rule's evidence.

**Fields:**
- `candidate_id`: numbered by size, then by the first agent ID. The numbers are not the ids in the Step 11 file.
- `shared_customers`: customers used by at least 2 members.
- `client_ids`: the clients of those shared activations.

**Check:** on the loaded v3 data, the groups are the same 14 as the Step 11 file `ml/runs/20261013-103859_final_evaluation_s42/ring_candidates.csv` (`tests/test_threat_intel.py`).

```json
{
  "rule": "Agents the model flagged (flag_source ML or Both) are linked when two of them share at least 3 customers, ...",
  "min_shared_customers": 3, "flagged_agents": 145, "candidates_total": 14,
  "candidates": [{"candidate_id": "cand_12", "size": 2, "agent_ids": ["A23833", "A65723"], "shared_customers": 4,
                  "client_ids": ["CL01", "CL02", "CL09"]}]
}
```

### Reports (admin only)

Every download is sent as an attachment with a dated file name (for example `flagged-agents_2026-10-13.csv`) and `Cache-Control: no-store`. Each is audited as `report_download` (category `report`) with the filters, row count, size and the sha256 of the file sent.

**Formula injection:** text cells that start with `=`, `+`, `-`, `@`, a tab or a carriage return get a leading apostrophe.

#### GET /api/reports/flagged-agents.csv

Agents flagged by the model or the rule in the latest run, highest score first. Names, phones and national IDs are masked. `404` before any successful run.

```
agent_id,region,account_status,anomaly_score,threshold,flag_source,risk_band,reasons,duplicate_pairs,masked_name,masked_phone,masked_national_id
A63269,Nairobi,active,9.803964,1.444799,ML,high,customer IDs look alike: similarity 0.485 vs typical 0.102 (...),0,V***** K****,**********486,*****900
```

#### GET /api/reports/audit-log.csv

The same filters as `GET /api/audit-log` (no paging), newest first, at most 50,000 rows. Columns: `timestamp, actor, actor_type, category, action, target_agent_id, request_ip, details`.

#### GET /api/reports/detection-summary.pdf

A one-page PDF built with reportlab. It contains:
- run status, model version and cutoff;
- counts by `flag_source` and `risk_band`;
- the top 10 regions by flagged rate.

The footer holds the generated time, the actor, the data load id and a data hash (sha256 over the loaded files' hashes). `404` before any successful run.

### Account administration (admin only)

| Method | Path | Body | Errors |
|---|---|---|---|
| GET | `/api/admin/accounts` | none | none |
| PATCH | `/api/admin/accounts/<admin_id>/role` | `{"role": "fraud_analyst" \| "compliance_officer" \| "admin"}` | `400` bad role, `403` own account, `404` unknown, `409` last active admin |
| POST | `/api/admin/accounts/<admin_id>/deactivate` | none | `403` own account, `404` unknown, `409` last active admin |
| POST | `/api/admin/accounts/<admin_id>/reactivate` | none | `403` own account, `404` unknown |

Changes are audited (category `admin`). A request that changes nothing returns `"changed": false` and is not audited. The second example below uses an illustrative account.

```json
{"count": 4, "accounts": [{"admin_id": "ADM_ADMIN_01", "username": "admin_01", "role": "admin", "is_active": true}]}
```

```json
{"message": "Account updated", "changed": true,
 "account": {"admin_id": "ADM_ANALYST_02", "username": "analyst_02", "role": "compliance_officer", "is_active": true}}
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
| `python -m src.auth` | Creates the demo accounts analyst_01, compliance_01 and admin_01. Only when `APP_ENV` is `development` or `test`; it refuses in production. The passwords come from `DEMO_ANALYST_PASSWORD`, `DEMO_COMPLIANCE_PASSWORD` and `DEMO_ADMIN_PASSWORD` (at least 12 characters), and none is in the code. Existing usernames are left unchanged. |
| `python -m src.manage_accounts deactivate <admin_id> --as <admin>` | Account changes from the command line (`deactivate`, `reactivate`, `role <admin_id> <role>`), as an active admin who gives a password; same rules and audit as the API |
| `python -m src.manage_accounts reset-password <admin_id or username> --new-password-env <VARIABLE>` | Local recovery for a forgotten password; needs direct database access, not an admin password (see below) |
| `pytest` | Runs the tests on `salesmesh_fraud_detection_test`, never on the development database |

### Account recovery (forgotten password)

`reset-password` is a **local recovery** command.

**Why it needs no admin password:** it runs on the server with the database credentials from `.env`, and anyone who can run it can already change the database directly. There is no API endpoint for it; the web app and the API cannot reset passwords.

**Steps** (PowerShell, from `backend/`):

1. Put the new password in an environment variable without echoing it:

   ```powershell
   $env:NEW_ACCOUNT_PASSWORD = [System.Net.NetworkCredential]::new("", (Read-Host "New password" -AsSecureString)).Password
   ```

2. Reset the account, by `admin_id` or username:

   ```powershell
   python -m src.manage_accounts reset-password analyst_01 --new-password-env NEW_ACCOUNT_PASSWORD
   ```

3. Remove the variable:

   ```powershell
   Remove-Item Env:NEW_ACCOUNT_PASSWORD
   ```

**Rules:**
- **Source of the password:** only the environment variable named by `--new-password-env`. There is no argument for the password itself, so it never lands in shell history or the process list. It is never printed.
- **Strength and storage:** the same rule as account creation (at least 12 characters, otherwise `Refused: Password must be at least 12 characters long`) and the same hashing (werkzeug `generate_password_hash`).
- **Audit:** an `admin` entry with action `password_reset`. The actor is `local:<operating-system user>`, and the details are `target_admin_id`, `target_username` and `"channel": "local recovery"`. Never the password or its hash.
- **Account state:** active or deactivated is unchanged. A deactivated account stays deactivated; reactivate it separately.
- **Lockouts:**
  - Accounts have no lockout or failed-attempt fields, so there is nothing to clear.
  - The only throttle is the API's login rate limit: 5 attempts per minute per IP, held in the API process's memory. It clears itself after a minute, or when the API restarts.
- **Errors:** an unknown account gives `Refused: Account not found`; an unset or empty variable is refused before anything changes.
