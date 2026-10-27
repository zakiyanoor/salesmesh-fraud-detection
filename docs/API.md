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

Three roles, with separation of duties: an analyst proposes, a compliance officer decides, and the admin who manages accounts and reports takes no part in reviews. Whoever proposed a decision can never agree with, overrule or correct it, even after a role change. Every rule is enforced on the server (see "Review workflow").

| Capability | fraud_analyst | compliance_officer | admin |
|---|---|---|---|
| Read agents, scores, analytics, clients, review decisions, run status | yes | yes | yes |
| Threat intelligence views | yes | yes | yes |
| Propose a review decision on a flagged agent (model, rule or both) | **yes** | no | no |
| Withdraw their own open proposal | **yes** | no | no |
| Agree with or overrule a proposal (made by someone else) | no | **yes** | no |
| Correct a final decision (not their own proposal) | no | **yes** | no |
| Open a customer from the duplicate evidence (audited) | yes | yes | no |
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
| `review` | `propose_decision`, `withdraw_decision`, `agree_decision`, `overrule_decision`, `correct_decision`, `review_refused`; older entries also have `confirm_decision` (an agreement before issue #28) | all: `decision_id`, `flag_id`, `notes` (the actor's note). Propose: `decision_outcome`, `run_id`, `flag_source`. Withdraw: `decision_outcome`. Agree and overrule: `proposed_by`, `decision_outcome`, `final_outcome`, `proposal_notes`. Correct: `correction_id`, `previous_outcome`, `new_outcome`. Refused (a `409`): `route`, `reason` and the `flag_id` or `decision_id`. `customer_viewed` (every open of a customer, target agent = the page it was opened from, if valid): `customer_ref`, `role`, `opened_from`, `run_id`, `agent_count`, `client_count`, `activations_total`; never the customer ID |
| `admin` | `role_change`, `account_deactivated`, `account_reactivated`, `password_reset` (local recovery, actor `local:<OS user>`) | `target_admin_id`, `target_username`, `old_role` / `new_role` or `role`; `channel` (`cli` or `local recovery`) |
| `report` | `report_download` | `report`, `filename`, `filters`, `row_count`, `bytes`, `sha256` of the file sent, plus `run_id`, `cap`, `load_id` or `data_hash` |
| `ai_decision` | `ai_detection_run` (one per run, also when it fails); `ai_flag` (per agent whose `flag_source` changed since the previous successful run, or newly flagged) | run: `run_id`, `status`, `trigger`, `model_version`, `threshold`, counts, `flag_changes`, `error`; flag: `change` (`newly flagged`, `cleared`, `flag source changed`), `previous_flag_source`, `flag_source`, `anomaly_score`, `threshold`, `top_features`, `reasons`, `model_version` |

## Review workflow

Issue #28. A flag is a request for human review, and a decision never changes a score, a flag or a detection run.

| Status | Meaning | Next |
|---|---|---|
| `pending_confirmation` | Proposed by an analyst, waiting for a compliance officer | the proposer withdraws it, or an officer agrees or overrules it |
| `withdrawn` | Withdrawn by its proposer, with a note | none; a new proposal on the flag is allowed |
| `agreed` | An officer kept the proposed outcome (note optional) | corrections only |
| `overruled` | An officer chose the other outcome, with a note | corrections only |

**Rules, enforced on the server:**
- **What can be reviewed:** the latest analysis period's flag of an agent whose `flag_source` in the latest successful run is `ML`, `Rule` or `Both`. Every agent has a `fraud_flags` row (its `flag_status` follows the model alone, as before), so `review.reviewable` in `GET /api/agents/<id>` says whether it can be reviewed now. The proposal stores the `run_id` and `flag_source` it was made on.
- **One open proposal per flag,** and none once the flag has a final decision: only a correction changes a final decision. The flag row is locked while proposing, and a partial unique index (`ux_review_decisions_one_open`) refuses a second open proposal even under concurrent requests.
- **Write once:** a proposal is closed once (withdrawn, agreed or overruled), setting only `final_outcome`, `closed_by`, `closed_at` and `close_note`. A database trigger refuses any other `UPDATE` and every `DELETE` or `TRUNCATE` on `review_decisions` and `review_corrections`. Only a transaction that sets `salesmesh.review_maintenance` is let through: the loader's `allow_deleting_reviews` path and test cleanup.
- **Corrections:** a correction is a new `review_corrections` row (previous and new outcome, note, who and when). The outcome in force (`effective_outcome`) is the newest correction's, else `final_outcome`.
- **Overdue:** an open proposal is `overdue` after 72 hours by the server clock (UTC). Nothing decides a proposal automatically; a detection run leaves review decisions alone.
- **Refusals:** a broken role rule is a `403` (logged as `access_denied`), a broken workflow rule a `409` (logged as `review_refused`), invalid input a `400`.
- **Migration** (`python -m src.migrate`, idempotent): adds the columns and `review_corrections`, renames `confirmed` to `agreed` (with `closed_by` from `confirmed_by` and `closed_at` from the `confirm_decision` audit entry), then adds the checks, the index and the triggers. It stops, changing nothing, if a flag has more than one open proposal.

## Endpoints

| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/api/login` | none | Start a session |
| POST | `/api/logout` | none | End the session |
| GET | `/api/me` | all | Username and role of the current session |
| GET | `/api/flagged-agents` | all | Agents the model flagged |
| GET | `/api/all-agents` | all | Every agent with status, features and `risk_band` |
| GET | `/api/agents/<agent_id>` | all | One agent: features, flag, score, rule evidence, identity (masked) |
| GET | `/api/agents/<agent_id>/activity` | all | One agent's activations per day and per hour of day |
| GET | `/api/customers/<customer_ref>` | fraud_analyst, compliance_officer | One customer from the latest run's duplicate evidence; every open is audited |
| GET | `/api/agent-scores` | all | Latest run's scores, filterable by `flag_source` |
| GET | `/api/analytics` | all | Platform statistics |
| GET | `/api/clients` | all | Client reference list |
| GET | `/api/model-info` | all | The cutoff and the test results, read from the frozen results files |
| GET | `/api/detection-runs/latest` | all | Status of the last detection run |
| GET | `/api/threat-intelligence/summary` | all | Counts, rates, commission and top features of flagged agents |
| GET | `/api/threat-intelligence/by-region` | all | Flagged agents per region; top 10 by flagged rate |
| GET | `/api/threat-intelligence/by-client` | all | Flagged agents' activations per client |
| GET | `/api/threat-intelligence/by-category` | all | Flagged agents' activations per category |
| GET | `/api/threat-intelligence/timeline` | all | Daily activations, flagged agents against others |
| GET | `/api/threat-intelligence/customer-sharing` | all | Customers shared by agents, and clusters of connected agents |
| GET | `/api/threat-intelligence/ring-candidates` | all | Groups of model-flagged agents that share at least 3 customers |
| GET | `/api/threat-intelligence/ring-candidates/<candidate_id>` | all | One ring candidate as a graph: members, shared-customer counts per pair, counties, activations per day |
| POST | `/api/review-decisions` | fraud_analyst | Propose a review decision on a flagged agent |
| POST | `/api/review-decisions/<decision_id>/withdraw` | fraud_analyst | Withdraw your own open proposal |
| POST | `/api/review-decisions/<decision_id>/agree` | compliance_officer | Agree with someone else's proposal |
| POST | `/api/review-decisions/<decision_id>/overrule` | compliance_officer | Overrule someone else's proposal |
| POST | `/api/review-decisions/<decision_id>/corrections` | compliance_officer | Correct a final decision |
| GET | `/api/review-decisions` | all | Review decisions, newest first, with their history |
| GET | `/api/audit-log` | admin | Audit trail, filtered and paged |
| GET | `/api/reports/flagged-agents.csv` | admin | Flagged agents of the latest run (masked) |
| GET | `/api/reports/audit-log.csv` | admin | Audit entries as CSV (same filters) |
| GET | `/api/reports/detection-summary.pdf` | admin | One-page detection summary |
| GET | `/api/admin/accounts` | admin | List accounts |
| PATCH | `/api/admin/accounts/<admin_id>/role` | admin | Change an account's role |
| POST | `/api/admin/accounts/<admin_id>/deactivate` | admin | Deactivate an account |
| POST | `/api/admin/accounts/<admin_id>/reactivate` | admin | Reactivate an account |
| GET | `/api/health` | none | Health check |

### POST /api/login

Body: `{"username": "...", "password": "..."}`. Records a `login` entry (category `authentication`). A failure records `login_failure` with actor `anonymous` and the reason, with the username tried only when it belongs to an account; a username that matches no account is stored as "unknown username".

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
- `flag`: every agent has one per analysis period; `flag_status` follows the model alone (`flagged` or `clear`).
- `review` (issue #28): whether the flag can be reviewed now (`reviewable`, and `reason` when not), its `flag_source`, the open proposal (`open_decision_id`, `open_proposed_by`, and `open_is_mine` for the viewer) and the final decision (`final_decision_id`, `effective_outcome`). The screen uses this, not the presence of `flag`.

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
  "context": {"client_ids": ["CL09", "CL15"], "categories": ["e-commerce", "education"]},
  "review": {"reviewable": true, "reason": null, "flag_id": "FL93b6b96d", "flag_source": "Both", "open_decision_id": null,
             "open_proposed_by": null, "open_is_mine": false, "final_decision_id": null, "effective_outcome": null}
}
```

`reason` in `duplicate_evidence` is `shared customer` (with `other_agent_id`) or `repeat after completed`. Each entry also has `customer_ref` (issue #28), the reference that opens the customer view.

### GET /api/agents/<agent_id>/activity

Same roles as agent detail (any signed-in account); reads are not audited. `404` if the agent does not exist. Issue #28.

- `days`: one row per day of the data window, which runs from the first to the last day in `activation_records` for all agents, so every agent covers the same days. Each row has `activations`, `completed` and `duplicate_evidence`: whether the day holds a record in this agent's duplicate evidence for the latest successful run.
- `hours`: activations per hour of day, 0 to 23.
- Days and hours are as recorded in the data (naive local timestamps, never converted). The flag belongs to the agent for the whole run, so no day is called flagged.
- No customer IDs and no identity data. Counted in SQL on the `agent_id` index (about 35 ms for the agent with the most records).

```json
{
  "agent_id": "A32962", "run_id": "RUN20261013172621c4f8ca", "first_day": "2026-08-01", "last_day": "2026-08-30",
  "days": [{"date": "2026-08-01", "activations": 18, "completed": 17, "duplicate_evidence": true}],
  "hours": [{"hour": 0, "activations": 3}],
  "totals": {"activations": 481, "completed": 439},
  "note": "Days and hours are as recorded in the data."
}
```

### GET /api/customers/<customer_ref>

**fraud_analyst and compliance_officer** (issue #28). One customer from the latest successful run's duplicate evidence: the agents who used it, the clients and the dates.

- **`customer_ref`** is `c_` plus 24 hex characters: an HMAC-SHA256 of the customer ID under `CUSTOMER_REF_KEY`. The URL and the audit log carry it instead of the customer ID. The response shows the customer ID as the evidence table does.
- **`CUSTOMER_REF_KEY`** (`src/config.py`, listed empty in `backend/.env.example`): at least 32 characters, required in production. In development and test a random key is made per process when it is empty, so references change when the server restarts. It is never logged or returned.
- **Scope:** only customers in the latest run's duplicate evidence. Any other reference, or anything not shaped like one, is a `404` and is not audited.
- **`from_agent`** (optional query parameter): the agent page the view was opened from. It is untrusted: it is kept only if it has the agent ID format (`A` and 5 digits) and the agent exists; otherwise it is recorded as `null`.
- **Audit:** every successful open writes `customer_viewed` (category `review`, actor the account, with its role), committed before the response. If it cannot be written, the response is a `500` with only an error message, and nothing about the customer is shown.
- **Activations:** the latest 200, newest first; `activations_total` is the full count. Record ids are not returned.

```json
{
  "customer": {"customer_ref": "c_3f9a1b2c4d5e6f708192a3b4", "customer_id": "CUST16131148"},
  "run_id": "RUN20261013172621c4f8ca",
  "agent_count": 2, "client_count": 2, "client_ids": ["CL04", "CL09"],
  "first_seen": "2026-08-03T10:12:00", "last_seen": "2026-08-27T16:40:00",
  "agents": [{"agent_id": "A35485", "flag_source": "Both", "risk_band": "high", "activations": 2,
              "client_ids": ["CL09"], "first_seen": "2026-08-03T10:12:00", "last_seen": "2026-08-27T16:40:00"}],
  "activations_total": 3, "activations_limit": 200,
  "activations": [{"timestamp": "2026-08-27T16:40:00", "agent_id": "A35485", "client_id": "CL09", "status": "completed"}]
}
```

Errors: `401` (no session), `403` (admin; recorded as `access_denied`), `404` (unknown reference), `500` (the audit entry could not be written).

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
- **`review`** (issue #28) counts proposals by status, overdue ones and corrections. `overrule_rate` = overruled ÷ (agreed + overruled): the share of compliance decisions that overruled the analyst. Withdrawn and open proposals are left out, corrections are counted separately, and it is `null` until an officer has decided something.

```json
{
  "cutoff": 1.444799,
  "flag_sources": [{"flag_source": "ML", "count": 72}, {"flag_source": "Rule", "count": 29},
                   {"flag_source": "Both", "count": 73}, {"flag_source": "None", "count": 826}],
  "score_distribution": [{"bucket": "< 1.1", "count": 572}, {"bucket": "1.1-1.3", "count": 210}],
  "region_breakdown": [{"region": "Kericho", "flagged": 6, "total": 25}],
  "platform_averages": {"submission_frequency": 15.8, "time_of_day_dist": 0.778, "customer_similarity": 0.109},
  "review": {"proposals": 6, "open": 2, "overdue": 1, "withdrawn": 1, "agreed": 2, "overruled": 1, "corrections": 1,
             "overrule_rate": 0.3333, "overdue_hours": 72}
}
```

### GET /api/model-info

Any signed-in role; not audited (issue #28). The figures for the Detection guide page, read from the frozen results files on every request and never retyped:

- `ml/runs/20261013-093050_selection_s42/operating_point.json` (hashed in `ml/results/FREEZE.md`): `model_version`, `features`, `cutoff`, `cutoff_rule`, `cutoff_chosen_on`;
- `ml/runs/20261013-103859_final_evaluation_s42/summary.json`: `test_agents`, `test_fraud_agents`;
- `ml/runs/20261013-103859_final_evaluation_s42/test_metrics.csv`: under `results`, the model, the duplicate rule and the system (model or rule), each with `precision`, `recall`, `pr_auc`, `roc_auc`, their 95% intervals (`*_ci`) and the counts `flagged`, `tp`, `fp`, `fn`, `tn`.

`measured_on` says the figures come from the 150 held-out test agents and are not a promise for other data. `detection_interval_minutes` is the scheduler's interval (`DETECTION_INTERVAL_MINUTES`, default 1440). `sources` lists the three files. `backend/tests/test_model_info.py` checks that the response equals the files.

```json
{
  "model_version": "lof_v3_4f", "cutoff": 1.4447993633890617, "cutoff_rule": "min expected cost 5:1", "cutoff_chosen_on": "validation",
  "test_agents": 150, "test_fraud_agents": 19,
  "results": {"model": {"precision": 0.6, "recall": 0.7894736842105263, "pr_auc": 0.84536680072518, "roc_auc": 0.9533949377259944,
                        "pr_auc_ci": [0.6842170081902225, 0.9603234989648033], "flagged": 25, "tp": 15, "fp": 10, "fn": 4, "tn": 121}},
  "measured_on": "the 150 held-out test agents, scored once with the frozen model; not a promise for other data",
  "detection_interval_minutes": 1440
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

**Analyst only.** Body: `{"flag_id": "FL93b6b96d", "decision_outcome": "confirmed_fraud", "notes": "Shares customers with two agents in Kisumu."}`. Creates a decision in `pending_confirmation` with the latest run's `run_id` and the agent's `flag_source`, and records a `propose_decision` audit entry whose details hold the notes. The agent must be flagged (`ML`, `Rule` or `Both`) in the latest run; see "Review workflow".

**`decision_outcome` (required):** exactly `"confirmed_fraud"` or `"legitimate"` (case-sensitive, no surrounding spaces). Anything else returns `400` with "decision_outcome must be one of ['confirmed_fraud', 'legitimate'], got ..." and writes nothing (no decision, no audit entry).

**`notes` (required, issue #13):**
- a string, trimmed, 1 to 1000 characters after trimming;
- plain text: newlines and tabs are allowed, other control characters are refused, and a Windows line break (CR LF) is stored as LF. It is stored as written, never as HTML;
- seven or more digits in a row (single spaces allowed between them, and not straight after a letter or digit) are masked like phone numbers, keeping the last 3, so a phone or national ID typed into a note is never stored in full. Dates such as `2026-10-14` and ids such as `CUST12345678` are left alone.

```json
{"message": "Review decision proposed; awaiting compliance confirmation", "decision_id": "RD1a2b3c4d", "status": "pending_confirmation",
 "notes": "Shares customers with two agents in Kisumu.", "run_id": "RUN20261013172621c4f8ca", "flag_source": "Both"}
```

Errors: `400` (missing `flag_id` or `decision_outcome`; `decision_outcome` not one of the two values; `notes` missing or null: "notes is required: give a short plain-text reason for the decision"; "notes must not be empty"; "notes must be a string"; "notes must be at most 1000 characters (got N)"; "notes must be plain text ..."), `403` (wrong role), `404` (unknown flag), `409` (the agent is not flagged in the latest run; the flag is from an earlier analysis period; the flag already has an open proposal or a final decision).

The other review actions take `notes` with the same rules (required unless stated).

### POST /api/review-decisions/<decision_id>/withdraw

**The proposing analyst only.** Body: `{"notes": "Proposed on the wrong agent."}`. Closes an open proposal as `withdrawn` and records `withdraw_decision`.

```json
{"message": "Proposal withdrawn", "decision_id": "RD1a2b3c4d", "status": "withdrawn", "closed_by": "ADM_ANALYST_01",
 "closed_at": "2026-10-14T09:12:00.120000", "close_note": "Proposed on the wrong agent."}
```

Errors: `400` (notes), `403` (wrong role, or not your proposal), `404`, `409` (no longer open).

### POST /api/review-decisions/<decision_id>/agree

**Compliance only, not the proposer.** Body optional: `{"notes": "Evidence checked."}`. Closes the proposal as `agreed` with `final_outcome` equal to the proposed outcome, and records `agree_decision`.

```json
{"message": "Proposal agreed", "decision_id": "RD1a2b3c4d", "status": "agreed", "decision_outcome": "confirmed_fraud",
 "final_outcome": "confirmed_fraud", "closed_by": "ADM_COMPLIANCE_01", "closed_at": "2026-10-14T10:00:00.000000",
 "close_note": null, "notes": "Shares customers with two agents in Kisumu."}
```

Errors: `400` (notes given but invalid), `403` (wrong role, or your own proposal), `404`, `409` (no longer open). `POST .../confirm` no longer exists.

### POST /api/review-decisions/<decision_id>/overrule

**Compliance only, not the proposer.** Body: `{"final_outcome": "legitimate", "notes": "The shared customers are one family."}`. `final_outcome` must differ from the proposed outcome (`400` otherwise; to keep it, agree). Closes the proposal as `overruled` and records `overrule_decision`. The response has the same fields as agree.

Errors: `400` (notes, `final_outcome`), `403`, `404`, `409`.

### POST /api/review-decisions/<decision_id>/corrections

**Compliance only, not the proposer** (the officer who decided may correct). Body: `{"new_outcome": "legitimate", "expected_current_outcome": "confirmed_fraud", "notes": "The customer list was from the wrong month."}`. Adds a correction to an agreed or overruled decision and records `correct_decision`; the decision itself is not changed. `expected_current_outcome` is the outcome in force that the officer saw: if another correction changed it meanwhile, the request is refused with `409`.

```json
{"message": "Correction recorded", "decision_id": "RD1a2b3c4d", "correction_id": "RC5e6f7a8b",
 "previous_outcome": "confirmed_fraud", "new_outcome": "legitimate", "corrected_by": "ADM_COMPLIANCE_02",
 "corrected_at": "2026-10-15T08:30:00.000000", "note": "The customer list was from the wrong month.", "effective_outcome": "legitimate"}
```

Errors: `400` (notes; outcomes not one of the two values; `new_outcome` equal to `expected_current_outcome`), `403`, `404`, `409` (not agreed or overruled; outcome changed meanwhile).

### GET /api/review-decisions

```json
{"count": 1, "overdue_hours": 72, "decisions": [{
  "decision_id": "RD1a2b3c4d", "flag_id": "FL93b6b96d", "agent_id": "A35485", "reviewer_id": "ADM_ANALYST_01",
  "decision_outcome": "confirmed_fraud", "decision_timestamp": "2026-10-13T15:10:00", "notes": "Shares customers with two agents in Kisumu.",
  "run_id": "RUN20261013172621c4f8ca", "flag_source": "Both", "status": "agreed", "final_outcome": "confirmed_fraud",
  "closed_by": "ADM_COMPLIANCE_01", "closed_at": "2026-10-14T10:00:00", "close_note": null,
  "corrections": [{"correction_id": "RC5e6f7a8b", "previous_outcome": "confirmed_fraud", "new_outcome": "legitimate",
                   "corrected_by": "ADM_COMPLIANCE_02", "corrected_at": "2026-10-15T08:30:00", "note": "The customer list was from the wrong month."}],
  "effective_outcome": "legitimate", "overdue": false, "still_flagged": true}]}
```

- `notes` is `null` for decisions recorded before notes existed; `run_id` and `flag_source` are `null` for decisions made before issue #28.
- The closing fields are `null` while a proposal is open. `closed_by` is the analyst for a withdrawal and the officer otherwise; it replaces `confirmed_by`, which the migration copied into it.
- `effective_outcome` is `null` while open or withdrawn. `still_flagged` is `false` when the agent is no longer flagged in the latest run; an open proposal stays open.

### GET /api/audit-log

**admin only** (other roles get `403`). Newest first. Event types are in "Audit log" above.

Query parameters (all optional):
- `category`: one of the six categories (anything else returns `400`);
- `actor`: an exact actor (for example `ADM_ADMIN_01`, `anonymous` or `system:lof_v3_4f`) or a username, which also matches that account's ID;
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

### GET /api/threat-intelligence/ring-candidates/<candidate_id>

Any signed-in role, like the other threat intelligence views (issue #28). `candidate_id` is one listed by `ring-candidates` for the latest run (for example `cand_01`); anything else is `404`.

- `nodes`: the candidate's members (from the stored ring-candidates view), each with `county`, `flag_source`, `risk_band`, `activations` and `linked_members`.
- `edges`: every pair of members that share at least one customer, with `shared_customers` (a count only, never a customer ID) and `meets_rule` (3 or more, the ring-candidate rule).
- `county` is the agent's `region` in the loaded data (one of Kenya's 47 counties). It is shown for information only; the model never uses it. `counties` and `county_count` give the distinct counties of the ring.
- `days`: the members' activations per day of the data window, in total and `by_agent`. Days are as recorded in the data.
- Computed on request from stored data (about 15 ms for the largest ring); nothing is written and nothing is audited.

```json
{
  "run_id": "RUN20261013172621c4f8ca", "candidate_id": "cand_01", "size": 6, "min_shared_customers": 3,
  "nodes": [{"agent_id": "A37760", "county": "Nakuru", "flag_source": "Both", "risk_band": "high", "activations": 310, "linked_members": 5}],
  "edges": [{"source": "A37760", "target": "A90728", "shared_customers": 117, "meets_rule": true}],
  "counties": ["Bungoma", "Kericho", "Kisii", "Nakuru", "Narok"], "county_count": 5,
  "first_day": "2026-08-01", "last_day": "2026-08-30",
  "days": [{"date": "2026-08-01", "activations": 61, "by_agent": {"A37760": 11}}]
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

The same filters as `GET /api/audit-log` (no paging), newest first, at most 50,000 rows; when more matched, the response has the header `X-Row-Limit-Reached: true`. Columns: `Time (UTC)` (ISO, ending in `Z`), `Actor`, `Actor type`, `Category`, `Action`, `Agent`, `Request IP (masked)`, `Result` (`Success` or `Failed` where the entry says which, otherwise blank), `Details`.

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

The list gives each account `last_login`: its most recent successful sign in, taken from the latest `login` audit entry (ISO UTC ending in `Z`), or `null`. No column stores it. Changes are audited (category `admin`). A request that changes nothing returns `"changed": false` and is not audited. The second example below uses an illustrative account.

```json
{"count": 4, "accounts": [{"admin_id": "ADM_ADMIN_01", "username": "admin_01", "role": "admin", "is_active": true, "last_login": "2026-10-27T05:30:00Z"}]}
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
