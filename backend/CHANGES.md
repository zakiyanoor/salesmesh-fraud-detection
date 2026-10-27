# Backend changes

## Sprint 12: analyst pages (issue #28)

Branch `feature/analyst-ui`. Frontend only: no backend change, no migration.

- **One date format everywhere** (`frontend/src/format.js`): day, short month, year and 24 hour time in Nairobi time, for example "13 Oct 2026, 17:26", on every page and in the footer. System times from the API (runs, decisions, audit) are UTC and are converted; activation data is shown as recorded.
- **Overview finish** (`frontend/src/pages/Dashboard.jsx`): the same layout, content and numbers as before with a refined look: tinted icon squares on the figure cards, sentence case card titles, a thicker donut with its legend beside it, slimmer risk band bars with values, and a balanced needs attention table with flag source chips. No score bar. New: a line when the latest run is more than 48 hours old, and "See all flagged agents". An earlier redesign on this branch (instrument bar, horizontal bars, score bar) was reverted.
- **County, not region:** every UI label that said Region now says County (the agent lists, chart titles and table views on Analytics and Threat intelligence, agent detail, the report description). Labels only: the API field `region` and the data are unchanged.
- **Shared fixes:** the footer separates the model and the run with a thin rule instead of a middle dot; a stray "0" at the end of the page text (Recharts' off screen measurement span) is hidden; the Proposed chip has the tooltip "Waiting for a compliance officer to agree or overrule", the wording the decision history now uses too; the Analytics score distribution reads the cutoff from `GET /api/model-info`.
- **Flagged agents finish:** the filters, a count line ("174 flagged agents", or "23 of 174 match your filters") and the table in one bordered container, removable chips for the active filters beside Clear filters, and hairline rows with hover and keyboard focus highlights. Same columns, sort, paging and narrow screen cards.
- **Agent detail finish:** the same layout with sentence case card titles, equal gutters and aligned edges; "Back to flagged agents" as a plain link and a subtitle with commas; a larger score with the bar labelled "Typical agent, about 1" and "Cutoff 1.445", the cutoff read from `GET /api/model-info` (the frontend constant is removed); feature rows with the platform average under each value; the reason text in a panel and the duplicate rule as a chip; Daily activity and the hour chart side by side at equal height, the duplicate evidence column only when needed, a line defining an activation, and the hour chart on the 24 hour clock with range tooltips and a range table.
- **Threat intelligence restructured:** one summary line instead of figure cards, then ring candidates (one table with a "Flagged by the model" and "All connected agents" switch), the activation timeline and one county chart of flagged against all agents. Flag sources, top risk agents, the figure cards and the second county chart are removed; What drives the flags moved to Analytics.
- **Ring graph rebuilt** with d3-force 3.0.0 (ISC licence, pinned): a deterministic force layout fitted to the container, dot size from activations, dot fill from the flag source, line width from shared customers, counts on hover, focus or selection, a selected agent's pairs in a panel with "Open agent", and a legend. The circle layout is removed.
- **Analytics trimmed:** score distribution, what drives the flags, review outcomes (with a line explaining overruled) and platform averages; the timeline and the county charts are only on Threat intelligence now.
- **Administrator pages:**
  - Accounts: `GET /api/admin/accounts` gives `last_login` for each account, from the latest successful sign in in the audit log (no schema change, no migration). The page shows it as Last signed in, hides deactivated accounts behind a switch, and its dialogs say the change is recorded in the audit log. The server commands moved to `docs/OPERATIONS.md`. The legacy account `ADM001` is still referenced (the command examples in `src/manage_accounts.py`, a frontend test and these notes), so it was not removed; its role shows as Administrator.
  - Audit log: the API and the export are for administrators only (compliance officers now get `403`). The Actor filter accepts a username. A failed sign in with a username that matches no account stores "unknown username" instead of the typed text; existing rows are unchanged. The CSV export headers are Time (UTC), Actor, Actor type, Category, Action, Agent, Request IP (masked), Result, Details, with times ending in Z, and a header tells the page when the 50,000 row cap cut it off.
  - Reports and Audit log pages: new wording, dates typed as dd/mm/yyyy, and the Agent column only where entries can name an agent.
- **Detection guide** replaces How the model works, at `/detection-guide` (the old address redirects), with the content rewritten around how a flag is made, the signals, the risk bands, reading a score and the test results.
- **Detection guide finish and sidebar:** the guide gains a hero over faint flowing lines, an "On this page" list on wide screens, joined numbered steps, chip labelled signal cards, the app's chips in the flag source table, a histogram of the latest run's scores with the typical agent and the cutoff marked, proportion bars under precision and recall, and the restored lines on where the figures come from. Its copy of the model and last run line is removed (it stays in the app footer). The sidebar shows the username and the role label without "Signed in as". Frontend only.
- **Analytics finish:** `GET /api/analytics` `platform_averages` now includes `collusion_score` (the mean over feature vectors that have it; a new test checks it). The page shows Review outcomes as a rate with a two part bar and tiles, and Average behaviour across all agents as four tiles. The four signals use the Detection guide's names everywhere in the interface (one mapping in `frontend/src/format.js`). The Detection guide's score chart notes that it includes agents the model learned from.
- **Threat intelligence finish:** three stat tiles instead of the summary line; the activation timeline card removed from the page (the endpoint stays); ring candidates in a sortable table with ID chips, a client count and View; the viewed group in tabs (Graph, Members, Pairs, Activity) with the county note once; the ring graph gains dragging, Reset layout and hover highlights; the county chart becomes upright grouped columns, horizontal bars below 700px. Frontend only.
- **How the model works:** next to the test results, one sentence that accuracy figures come only from the test agents (the number from `GET /api/model-info`) and that scores shown for other agents include agents the model learned from.

## Sprint 11: landing page and themes (issue #28)

Branch `feature/landing-page`. Frontend only: no backend change, no migration.

- **Light and dark colour schemes** (MUI `colorSchemes`). Light is the default whatever the device prefers. A theme menu with Light and Dark on the landing page, the sign-in page and the signed-in header remembers the choice; an older stored "system" counts as light. A small first-party script in `frontend/index.html` paints the first frame in the right scheme.
- **Landing page** (replacing the first version from Sprint 10): a top navigation with the pages every role may open (Overview, Threat intelligence, Analytics, How the model works; signed out, each goes to sign in and opens after it, with only known relative paths accepted), a hero with the headline, Sign in and a globe that draws only Kenya with a dot for each of the 47 county headquarters, four cards under "What the platform does" (Detection, Review, Investigation, Accountability, each with one link), and a footer with the Platform pages, the four security points and "2026 SalesMesh" and "Nairobi, Kenya". The globe uses the npm package `cobe` (MIT, no dependencies, bundled), stays a dark sphere in both schemes, pauses when hidden, is still with reduced motion, and falls back to an SVG drawing without WebGL. The sign-in page shares the landing page's surfaces. Details and the code behind each security point are in `docs/FRONTEND.md`.
- **Ring graph**: edge labels are placed so they do not land on each other or on the agents' names, and names have a halo where an edge passes behind them.

## Sprint 10: screens (issue #28)

Branch `feature/sprint-3-screens`.

### Landing page (frontend only)

- A first landing page at the site root before sign in, with Sign in leading to the existing form at `/sign-in`. No backend change. Replaced in Sprint 11 (see above).

### Model information

- **New endpoint `GET /api/model-info`** (`src/model_info.py`), open to every signed-in role and not audited. It reads its figures from the frozen results files on every request; nothing is retyped:
  - the cutoff and model from the frozen `operating_point.json`;
  - the test agents from `summary.json`;
  - precision, recall, PR AUC and ROC AUC with their intervals for the model, the rule and the system, from `test_metrics.csv` of the final evaluation run.
- It also gives the scheduler interval, and says where the figures were measured (the 150 held-out test agents, not a promise for other data).
- **Tests:** `tests/test_model_info.py` compares every value with the files, checks the operating point's hash against `FREEZE.md`, the roles, and that reads are not audited.

### Ring graph

- **New endpoint `GET /api/threat-intelligence/ring-candidates/<candidate_id>`** (`src/ring_graph.py`): the members of one ring candidate, the number of customers each pair shares (never a customer ID), each member's county and the group's activations per day.
- **Members** come from the stored ring-candidates view, so the graph shows exactly the listed groups.
- **County** is the existing `agents.region` (one of Kenya's 47 counties, from the data generator), shown as information only; the model never uses it.
- **Computed on request** from stored data, about 15 ms for the largest ring (6 agents). Nothing is written or audited. Open to every role, like the other threat intelligence views.
- **Tests:** `tests/test_ring_graph.py` checks:
  - roles;
  - 404 for unknown or malformed candidates;
  - members against the ring-candidates view, and pair counts against SQL;
  - no customer ID, counties against `agents`;
  - the timeline adds up;
  - nothing is written, and the response is fast.

### Daily activity for an agent

- **New endpoint `GET /api/agents/<agent_id>/activity`** (`src/activity.py`): one row per day of the data window, with activations, completed activations and whether the day holds a record in the agent's duplicate evidence for the latest run; plus activations per hour of day.
  - The data window is the first to the last day of all activation records, so every agent covers the same days.
  - Same roles as agent detail; reads are not audited; a request without a session is refused and logged by the existing rule.
- **Days and hours are as recorded in the data.** No day is called flagged, because the flag belongs to the agent for the whole run.
- **No customer IDs and no identity data.**
- **Speed:** counted in SQL on the existing `agent_id` index, about 35 ms for the agent with the most records (481).
- **Tests (activity):** `tests/test_activity.py` checks the window, the counts per day and per hour, and the evidence days against SQL; that reads are not audited; that no customer ID appears; and that the response is fast for the agent with the most records.

## Sprint 9: clickable customers in the evidence (issue #28)

Branch `feature/clickable-customers`. The "Why flagged" panel and masking customer IDs are on hold and not built.

- **New endpoint `GET /api/customers/<customer_ref>`** (`src/customers.py`): the agents, clients and dates behind one customer in the latest run's duplicate evidence.
  - Open to fraud analysts and compliance officers; an admin gets 403, recorded as `access_denied`.
  - Any other customer or reference is a 404 and is not audited.
- **The customer ID never appears in a URL or the audit log.**
  - `customer_ref` is an HMAC-SHA256 of the customer ID under the new `CUSTOMER_REF_KEY`. The key is set in `src/config.py`: at least 32 characters and required in production, with a random key per process in development and test. It is listed empty in `.env.example` and never logged.
  - Evidence rows in `GET /api/agents/<id>` gain `customer_ref`. Customer IDs are shown exactly as before, in the evidence table, the customer-sharing view and the dialog.
- **Audit:** every open writes `customer_viewed` in the existing `review` category, with the account, its role, the reference and the counts. It is committed before the response, and if it cannot be written the response is a 500 with no customer data.
  - This is the first read that is audited. The audit categories, the append-only trigger and the access-denied rule are unchanged.
- **Untrusted input:** `from_agent` is kept only if it has the agent ID format and the agent exists, and is recorded as the entry's target agent.
- **Activations:** capped at the latest 200, newest first, with `activations_total`.
- **No database change and no migration.** Nothing changes for the model, the cutoff, the features, the frozen files, the review workflow, `threat_intel.py` or the customer-sharing view.
- **Tests:**
  - `tests/test_customers.py`: roles, scope and 404s without audit; agents, clients and dates against SQL; the cap; one audit entry per open with actor and role, never the customer ID; untrusted `from_agent` values; no data when the audit write fails.
  - `tests/test_config.py`: the key rules.
  - `tests/test_masking.py`: the GET sweep covers the new route.

## Sprint 8: threat intelligence views once per run (issue #28)

Branch `feature/explainability-and-review`.

### Review workflow

- **Before:** a fraud analyst proposed and a compliance officer could only confirm.
  - There was no reject, withdraw or correction, so a disagreement left a proposal pending with no trace.
  - The server accepted a proposal on any flag, even an unflagged agent's: every agent has a `fraud_flags` row, and the agent page showed the form for all of them.
  - Nothing stopped two open proposals on one flag.
- **Now** (`src/review.py`; rules in `docs/API.md`, "Review workflow"):
  1. An analyst proposes an outcome with a required note on any agent flagged by the model, the rule or both in the latest run. The proposal stores that `run_id` and `flag_source`.
  2. One open proposal per flag, and none after a final decision (409, recorded as `review_refused`). The flag row is locked and a partial unique index catches races.
  3. The proposer can withdraw an open proposal with a note.
  4. A compliance officer agrees (note optional) or overrules with the other outcome (note required). `POST /confirm` is removed.
  5. Only the proposer can withdraw; only an officer who is not the proposer can decide or correct, even after a role change; the admin can do neither.
  6. A closed decision is never changed. A correction (any officer but the proposer, note required) is a new `review_corrections` row; `expected_current_outcome` refuses a correction based on an outdated outcome.
  7. `overdue` after 72 hours. Nothing decides a proposal automatically.
  8. Audit: `propose_decision`, `withdraw_decision`, `agree_decision`, `overrule_decision`, `correct_decision` and `review_refused`, in the same transaction as the action.
  9. No decision changes a score, a flag, a run or a threat view. `GET /api/analytics` reports `overrule_rate` = overruled ÷ (agreed + overruled).
- **Database:**
  - `review_decisions` gains `run_id`, `flag_source`, `final_outcome`, `closed_by`, `closed_at` and `close_note`; statuses are `pending_confirmation`, `withdrawn`, `agreed` and `overruled`. The new table is `review_corrections`.
  - Checks keep the closing values consistent. Triggers refuse any other update and every delete unless `salesmesh.review_maintenance` is set; only the loader's `allow_deleting_reviews` path and test cleanup set it. The existing audit trigger is unchanged.
- **Migration:** run `python -m src.migrate`. It renames `confirmed` to `agreed`, copying `confirmed_by` into `closed_by` and taking `closed_at` from the `confirm_decision` audit entry. It stops if a flag has two open proposals.
  - Checked on a copy of the development database: 3 confirmed decisions became agreed with their audit times, the pending one stayed open, and a second run changed nothing.
  - One flag there has two agreed decisions and a later open proposal. The proposal stays in the queue for an officer, the history shows all three, and the outcome in force is the newest decision's.
- **API:** `GET /api/review-decisions` returns the closing fields, corrections, `effective_outcome`, `overdue` and `still_flagged`; `closed_by` replaces `confirmed_by`. Agent detail gains a `review` block.
- **Tests:** `tests/test_review_workflow.py` covers:
  - the migration, the checks, the one-open index and the triggers (with raw SQL);
  - every rule above, including the role matrix for all five actions;
  - proposals, withdraw against agree, and corrections sent at the same moment;
  - a detection run over a five-day-old proposal, which stays open;
  - no change to scores, flags or views.

  Existing tests moved from `/confirm` to `/agree` and now pick a flagged agent's flag.

### Views computed once per detection run

- **Before:** every request to a threat intelligence view recomputed it.
  - Summary, timeline, by-client and by-category each read all 135,494 activation records.
  - Ring candidates rebuilt the flagged agents' customer sets.
- **Now:**
  - `run_detection_cycle` computes all seven views with the unchanged `threat_intel` functions and stores them in the new `threat_views` table (`run_id`, `view`, `view_version`, `payload`).
  - They are stored in the same transaction as the run, so a run never succeeds without its views. A view that fails fails the run.
- **Serving** (`threat_intel.view_payload`):
  - The endpoint finds the latest succeeded run, as before, and returns that run's stored copy.
  - A run with no stored copy at the current version is computed with the current code and kept in memory per run, view and version. That covers runs from before this change and views whose version changed.
- **Staleness:**
  - The cache key is the `run_id`, so nothing needs invalidating: a new run is served as soon as it commits, and a running or failed run is never served.
  - No view reads review decisions or `fraud_flags`, so a review decision changes no view (tested).
  - After a data reload with no new run, the views show the run's own records, consistent with its scores.
- **Versions:** `threat_intel.VIEW_VERSIONS`, all 1. Bump a view's number whenever its output changes; stored copies of other versions are then recomputed.
- **Migration:** `migrate_schema` creates the table. On an existing database, run `python -m src.migrate` (or a detection run) before starting the API.
- **Cost:** computing and serialising the seven views takes about 2.3 s per run (median of 5 on the bench database).

### One fetch of the latest detection run

- **Frontend:** `LatestRunProvider` in the layout fetches `/api/detection-runs/latest` once per page and shares it with the Overview card and the footer, which used to fetch it separately.
  - It refreshes on each navigation, so the footer is now as fresh as the Overview card.
  - The previous answer stays on screen while a refresh loads.

### Tests

- **`tests/test_threat_views.py`:**
  - the table's columns and key;
  - every view stored at the current version, equal to computing it;
  - a failing view fails the run and stores nothing;
  - the API returns the same bytes as computing the view, and serves the stored copy;
  - a stored copy of another version is recomputed;
  - a run without stored views is computed;
  - views follow a new run (one with a flag removed), never a failed or running run, and a normal run afterwards gives the original views again;
  - a proposed and confirmed review decision changes no view.
- **Frontend:**
  - the Overview fetches the latest run once for the card and the footer;
  - the footer refreshes once per page and keeps the previous run on screen meanwhile.
- **Reference check** (outside the test suite):
  - Before any change, the seven responses were saved from a copy of the test database. The new code returned them byte for byte, both for that run (computed) and, apart from the `run` block, for a new run (stored).

### Timings

- **Setup:**
  - a copy of the test database (1000 agents, 135,494 records);
  - the Flask development server;
  - 5 passes, the first straight after the server started.
- **Sequential requests (curl), ms:**

  | Endpoint | Size | Before: cold | Before: warm mean | After: cold | After: warm mean |
  |---|---|---|---|---|---|
  | threat-intelligence/summary | 872 B | 553 | 545 | 16 | 8 |
  | threat-intelligence/timeline | 2,090 B | 462 | 535 | 9 | 9 |
  | threat-intelligence/ring-candidates | 2,764 B | 170 | 183 | 10 | 8 |
  | threat-intelligence/customer-sharing | 6,833 B | 70 | 63 | 8 | 8 |
  | threat-intelligence/by-region | 4,978 B | 57 | 26 | 8 | 9 |
  | agent-scores?limit=10 | 6,672 B | 11 | 11 | 13 | 10 |
  | agent-scores?limit=50 | 31,895 B | 25 | 12 | 35 | 10 |
  | detection-runs/latest | 313–344 B | 26 | 7 | 27 | 8 |
  | me | 49 B | 10 | 5 | 9 | 6 |

- **Browser (Chrome, production build, run 1 with an empty cache):**

  | | Before | After |
  |---|---|---|
  | Overview settled, runs 1–5 | 1.59, 1.45, 1.81, 1.71, 1.76 s | 1.28, 1.18, 1.17, 1.15, 1.17 s |
  | Overview `detection-runs/latest` requests | 2 | 1 |
  | Overview summary request | 361–680 ms | 25–41 ms |
  | Threat Intelligence settled, runs 1–5 | 2.43, 3.11, 2.92, 3.03, 2.74 s | 1.26, 1.30, 1.33, 1.16, 1.28 s |
  | Threat Intelligence view requests | 549–1,873 ms | 24–75 ms |
  | Threat Intelligence long tasks (total) | 241–478 ms | 144–254 ms |

  "Settled" includes a fixed 0.5 s wait for the network to go quiet.
- **Parallel requests:** the 8 Threat Intelligence requests, fired at once, 5 rounds.
  - Before: 1.17 to 1.26 s in total, close to the 1.26 to 1.54 s sum of their solo times, because the work was serialised.
  - After: 36 to 42 ms (157 ms in the first round, while the database connections opened), against a sum of 49 to 67 ms and a slowest single request of 7 to 14 ms.
  - The development server answers in threads, but they overlap only partly, because each request is mostly Python work. A production server is left for the deployment item.

## Sprint 7: hybrid hardening (issue #26)

Branch `sprint-7/hybrid-hardening`.

### Score percentile beside the raw score

- **New field `score_percentile`** next to the raw score:
  - in `/api/agents/<id>` (`score.score_percentile`) and `/api/agent-scores`, through `score_payload`;
  - in `/api/flagged-agents` and `/api/all-agents`.
- **Definition** (`risk.score_percentiles`):
  - The share of agents in the same detection run with a strictly lower score, from 0 to 100, rounded to 1 decimal place.
  - Tied scores share a percentile.
  - It is a rank within the run, not a probability.
- **Computed on read** from the stored `agent_scores` of the latest run, and cached by `run_id` (8 runs at most).
  - No schema change or migration.
  - The model, the cutoff, `risk_band`, the stored scores and the sort order are unchanged.
  - The CSV and PDF reports are unchanged.
- **Tests** (`tests/test_score_percentile.py`):
  - the definition on hand-made scores, including ties, a single agent and the top of 1000;
  - percentiles that fall with the score on `/api/agent-scores`, with the top agent at (n − 1) / n × 100;
  - the same value on all four endpoints.

### Ring candidates in threat intelligence

- **New view `GET /api/threat-intelligence/ring-candidates`** (`threat_intel.ring_candidates`), open to every role like the other views.
- **The Step 11 rule** from `ml/final_evaluation.py`, unchanged:
  - agents the model flagged (`ML` or `Both`) in the latest run;
  - linked when two share at least 3 customers (any client);
  - joined transitively into groups of 2 or more.
  - The backend applies the rule to the run's stored flags, instead of rescoring with the bundle as Step 11 did.
- **Parity:** the backend's groups are exactly the 14 candidates in the frozen `ml/runs/20261013-103859_final_evaluation_s42/ring_candidates.csv`.
  - Step 11 read `activation_records_clean.csv` and the backend reads the loaded `activation_records`; the groups are the same.
  - `tests/test_threat_intel.py` checks this.
- **Tests:**
  - the rule by hand: 2 shared customers do not link agents, and 3 do; groups join transitively; a lone agent is not a candidate;
  - every member is model-flagged; groups do not overlap;
  - `shared_customers` matches SQL;
  - the ids are ordered.
- **Unchanged:** the `customer-sharing` view, the model, the cutoff, the stored scores and the agent detail page.

### Settings from the environment

- **New `src/config.py` (`load_config`)** reads these settings:

  | Variable | Default | Notes |
  |---|---|---|
  | `APP_ENV` | `production` | `development`, `test` or `production` |
  | `FLASK_DEBUG` | `false` | Refused in production |
  | `CORS_ORIGINS` | `http://localhost:5173` in development and test; none in production | `*` is refused |
  | `SESSION_COOKIE_SECURE` | `true`; `false` in development and test | |
  | `SESSION_COOKIE_SAMESITE` | `Lax` | `Lax` or `Strict` |
  | `SESSION_LIFETIME_MINUTES` | 60 | |

- **The session cookie is always `HttpOnly`.**
- **Login marks the session permanent**, so the lifetime applies. Before, the cookie lasted until the browser closed.
- **`app.run` no longer forces `debug=True`.**
- **Tests:**
  - they always run with `APP_ENV=test`;
  - `tests/test_config.py` covers the defaults, the refusals, the cookie flags and expiry on login, and CORS answering only configured origins.
- **`backend/.env.example`** lists every variable the backend reads, with no secrets. The README setup points to it.

### Demo accounts gated, passwords out of the code

- **`python -m src.auth` (`auth.seed_demo_accounts`):**
  - It runs only when `APP_ENV` is `development` or `test`, and refuses in production (or when `APP_ENV` is unset).
  - The passwords come from `DEMO_ANALYST_PASSWORD`, `DEMO_COMPLIANCE_PASSWORD` and `DEMO_ADMIN_PASSWORD`. It names any variable that is missing.
  - Every password must pass `validate_password` before anything is created.
- **No demo password is in the code any more:**
  - `src/auth.py` no longer holds them;
  - the `tests/helpers.py` fallbacks are removed;
  - the frontend's mocked logins type a placeholder.
- **Backend tests:** `tests/conftest.py` loads `backend/.env` and stops with a clear message if a `DEMO_*_PASSWORD` is missing. CI generates them per run.
- **The previous demo passwords remain in git history**, which was not rewritten. Treat them as public. The local development accounts were reset with `manage_accounts reset-password`. Reset them on any other database that still uses them.
- **Tests** (`tests/test_demo_accounts.py`):
  - refused in production, unset and unknown `APP_ENV`;
  - names the missing variables;
  - rejects a weak password before creating anything;
  - succeeds in test;
  - no password literal in `src/auth.py`.

### Requirements split

- **`backend/requirements.txt` now lists direct dependencies only, at the versions already in use:**
  - Flask, Werkzeug, flask-cors, Flask-Limiter;
  - SQLAlchemy, psycopg2-binary, python-dotenv;
  - APScheduler, reportlab;
  - pytest;
  - numpy, pandas, scikit-learn, joblib and Faker, for the frozen ML code imported through `src/ml_bridge.py` (`feature_engineering` imports `data_generation`, which imports Faker).
- **Removed:**
  - packages no code imports: streamlit, uvicorn, starlette, altair, pydeck, websockets, matplotlib;
  - packages only those pulled in: pyarrow, protobuf, httptools, watchdog, toml, jsonschema and their dependencies.
  - `narwhals` is no longer pinned, but it is still installed, because scikit-learn 1.9 depends on it.
- **New `ml/requirements.txt`:** numpy, pandas, scikit-learn, scipy, joblib, Faker, matplotlib, pytest.
- **CI:** the ml job installs it.
- **Checked in fresh Python 3.14 virtual environments:**
  - `pip check` is clean in both;
  - none of the seven unused packages, nor matplotlib in the backend, is installed;
  - the ml suite (192) and the backend suite (234) pass.

### Known issue: frontend test timeouts on a busy computer

- **Some frontend tests sometimes time out when the computer is busy.**
- **A fix was tried and did not hold up, so it was not kept.** It preloaded the lazy page modules before the first test in each file. The first render got faster, but under heavy load failures still spread to other tests, and the preload itself could time out.
- **Locally:** close heavy programs before running the frontend tests, or run `npx vitest run --maxWorkers=6`.
- **Left for later:** the AuditLog filters test and the AgentDetail proposal test are slow under heavy load, because they type one keystroke at a time.

## Sprint 4: backend additions for the frontend

Branch `sprint-4/frontend-dashboard`. Reference in `docs/API.md`.

### Local password recovery (issue #19)

- New: `python -m src.manage_accounts reset-password <admin_id or username> --new-password-env <VARIABLE>`. It is for a forgotten password and needs direct database access, not an admin password.
- **Password handling:**
  - The new password is read only from the named environment variable and is never printed.
  - It must meet the account-creation rule, now shared as `auth.validate_password`.
  - It is hashed with the same `generate_password_hash`.
- **Audit:** an `admin` entry with action `password_reset`, actor `local:<OS user>` and `"channel": "local recovery"`, without the password or hash.
- **Account state:** unchanged; a deactivated account stays deactivated. There are no lockout or failed-attempt fields to clear.
- **The command now uses subcommands;** existing `deactivate`, `reactivate` and `role` invocations work unchanged.
- **Tests** (`tests/test_manage_accounts.py`):
  - success by id and by username;
  - unknown account, weak passwords, an unset variable, no password argument;
  - the audit entry, a deactivated account, the help text;
  - no password or hash in the output or the audit entry.
- Steps: `docs/API.md`, "Account recovery".

### GET /api/me (issue #5)

- Returns `{"username", "role"}` for the current session and nothing else; `401` without a session or for a deactivated account.
- The role is re-read from the database on every request, so a role change shows at once.
- **Not audited:** no other read endpoint writes an audit entry, so a successful call writes none.
- **401s:**
  - A `401` with **no session at all** writes no entry: an anonymous "is anyone logged in?" check is not a security event, and the frontend makes it on every load while logged out. The exception is in `audit_denied_requests` and applies to this route only.
  - A `401` for a **deactivated account** is still recorded as `access_denied` with that account as the actor.
  - Every other denied request on every route is recorded as before.
- Tests: `tests/test_me.py`, covering the unaudited anonymous check (while `/api/flagged-agents` is still audited) and the audited deactivated case. The masking sweep in `test_masking.py` picks the route up automatically.

### Notes on review decisions (issue #13)

- **Required on `POST /api/review-decisions`:** `notes`, a string, trimmed, 1 to 1000 characters after trimming. A missing, null, empty, non-string, too long or non-plain-text value returns `400` with a message naming the problem, and nothing is stored.
- **Plain text:** newlines and tabs are allowed; other control characters are refused; CR LF is stored as LF. Notes are stored as written and never treated as HTML.
- **Masking:** a run of seven or more digits (single spaces allowed, not straight after a letter or digit) is masked on the way in, keeping the last 3 digits, so a phone or national ID typed into a note is never stored or returned in full. Dates and ids such as `CUST12345678` are not touched.
- **Stored** in the new nullable column `review_decisions.notes`; the migration adds it with `ADD COLUMN IF NOT EXISTS` (safe to run twice). Decisions made before this change keep `notes = null` and can still be listed and confirmed.
- **Returned** in the propose response, the confirm response and every entry of `GET /api/review-decisions`.
- **Audited:** `notes` is in the details of both the `propose_decision` and the `confirm_decision` entries, and so also in the audit-log CSV.
- `POST /api/review-decisions` with no JSON body now returns `400` instead of `500`.
- **`decision_outcome` is validated:**
  - Only `"confirmed_fraud"` or `"legitimate"` are accepted (exact match, `DECISION_OUTCOMES` in `src/db.py`). Anything else, including a wrong case, padding, an empty string, null or a non-string, returns `400` naming both allowed values, and writes no decision and no audit entry.
  - The check is in the API only; existing rows are not checked or changed.
  - Tests: seven invalid values and both valid ones in `tests/test_review_notes.py`.
- **Tests:**
  - new `tests/test_review_notes.py`: missing, null, empty, whitespace only, non-string, too long, control character, trimming at the length limit, stored and returned, audit entries, old rows, migration twice, and phone and national ID numbers in notes masked, followed by the full masking sweep;
  - `test_rbac_audit._propose` sends notes;
  - the sweep in `test_masking.py` is now a reusable function.
- **The frontend must send `notes`:** until it does, proposals from the current React page fail with `400`.

## Sprint 3, part 2: roles, audit, threat intelligence and reports (issue #18)

Branch `sprint-3/backend-database`. The full endpoint reference, roles table and audit event types are in `docs/API.md`.

### Roles and separation of duties (`src/auth.py`, `src/accounts.py`)

- **New role `admin`:**
  - may list accounts, change roles, deactivate and reactivate accounts, read the audit log, download reports and view run status;
  - may **not** propose or confirm review decisions.
- **Audit log readers:** `compliance_officer` keeps confirming decisions and can read the audit log; `fraud_analyst` can no longer read it.
- **Accounts:** `administrators.is_active` is added by the migration.
  - Every request re-reads the account, so a deactivation or role change takes effect on the next request.
  - An account whose role is not one of the three is refused at login and on every request. The development database holds a legacy account `ADM001` with role `administrator`, which until now could read every login-protected endpoint.
- **Account rules:**
  - An admin cannot change or deactivate their own account (403).
  - The last active admin cannot be demoted or deactivated (409). The active admin rows are locked before the check; through the API this matters when two admins act at once.
- `role_required` accepts several roles.
- `python -m src.auth` adds the demo account `admin_01`.

### Audit log (`src/audit.py`, `src/db.py`)

- **New columns** in `admin_action_log`: `category`, `actor_type`, `details` (JSON text) and `request_ip` (masked to `a.b.*.*`; IPv6 to its first two groups). The migration adds them with `ADD COLUMN IF NOT EXISTS` and backfills older rows; it is safe to run twice.
- **Append only:** a PostgreSQL trigger refuses `UPDATE`, `DELETE` and `TRUNCATE`. Only a transaction that sets `salesmesh.audit_maintenance`, which the migration does for its backfill, may change rows. No route can change entries, and tests prove both.
- **Recorded:**
  - login success, login failure (actor `anonymous`, with the username and reason) and logout;
  - every 401 and 403 as `access_denied` with route, method, role, status and reason;
  - account changes, review proposals and confirmations, and report downloads.
- **AI decisions** (actor `system:lof_v3_4f`, `actor_type` system):
  - one `ai_detection_run` entry per run, including failed runs;
  - one `ai_flag` entry per agent whose `flag_source` changed since the previous successful run, or that is newly flagged. Each carries the anomaly score, cutoff, flag source, top features, reasons and model version.
- **`GET /api/audit-log`:** filters `category`, `actor`, `agent_id`, `date_from` and `date_to`; paging with `limit` up to 1000.

### risk_band (`src/risk.py`)

- `high`: model flagged (`ML` or `Both`).
- `review`: rule only, or a score from 1.3 up to the cutoff.
- `low`: everything else.

It is on `/api/flagged-agents`, `/api/all-agents`, `/api/agent-scores` and `/api/agents/<id>`.

### Threat intelligence (`src/threat_intel.py`)

Read only, for any authenticated role, from the latest successful run: `/api/threat-intelligence/summary`, `by-region`, `by-client`, `by-category`, `timeline` and `customer-sharing`. Tests check every number against direct SQL.

### Reports (`src/reports.py`)

- **Admin only:** `/api/reports/flagged-agents.csv`, `/api/reports/audit-log.csv` (capped at 50,000 rows) and `/api/reports/detection-summary.pdf` (one page, built with reportlab 5.0.1, pinned in `requirements.txt`).
- **Masking:** names, phones and national IDs are masked.
- **Formula injection:** CSV cells starting with `=`, `+`, `-`, `@`, a tab or a carriage return are prefixed with an apostrophe.
- **Headers:** dated attachment file names and `Cache-Control: no-store`.
- **Audit:** every download is recorded with its filters, row count, size and sha256.

### Tests

- **New files:** `test_audit.py`, `test_accounts.py`, `test_ai_audit.py`, `test_risk_band.py`, `test_threat_intel.py` and `test_reports.py`.
- **Changed:**
  - conftest no longer deletes audit rows after each test (the trigger forbids it), and it seeds and resets the three test accounts;
  - `_audit_entries` reads through the `actor` filter;
  - the audit-log read test now expects admin and compliance to be allowed and the analyst denied;
  - the `role_required` unit tests use real accounts, because the account is re-read on each request;
  - the masking sweep runs as all three roles and decodes binary responses leniently, so it covers the PDF.
- The failed-login test still holds unchanged: failures are recorded with actor `anonymous`, not the account tried.

### Known issues

- **The test database's audit log only grows** (append only), so the audit-log CSV and the masking sweep slow down slowly over many runs. The masking sweep takes about 2.5 minutes now. Recreating the test database resets it.
- **Legacy account in the development database (resolved 2026-10-13):** `ADM001` (role `administrator`) was deactivated by `admin_01` with `python -m src.manage_accounts deactivate ADM001 --as admin_01`.
  - The change went through the accounts service and was audited (`account_deactivated`, category `admin`, `"channel": "cli"`).
  - A before-and-after fingerprint of every table showed that nothing else changed: only `administrators.is_active` for `ADM001`, plus that one new audit entry. The 16 earlier audit rows are unchanged.
- **Test database:** recreated at the start of every test session (`pytest_sessionstart`; refuses any name not ending in `_test`; `KEEP_TEST_DB=1` skips it), so the append-only audit log no longer slows the suite over time.

### Command-line account administration (`src/manage_accounts.py`)

`python -m src.manage_accounts deactivate|reactivate|role <admin_id> [new_role] --as <admin username>` applies the same rules as the API and audits the change with `"channel": "cli"`.
- The acting account must be an active admin and gives its password, by prompt or through `--password-env`.
- It cannot change itself, and it cannot remove the last active admin.

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

- **Frontend:** `Dashboard.jsx` colours risk with fixed tiers (0.8 high, 0.5 medium) made for the old 0 to 1 scores. With LOF scores nearly every agent shows as high risk. Since issue #18 every agent payload carries `risk_band`, which the frontend should use instead.
- **Line endings (fixed in commit `e31f5eb`):** with `core.autocrlf=true`, checkout had rewritten three frozen ML markdown files with CRLF, so 4 ML freeze tests failed.
  - The root `.gitattributes` now pins each hashed file to the line ending it was frozen with: LF for `FREEZE.md`, `acceptance_criteria.md`, `selection_rule.md` and `selection_notes.md`; CRLF for the hashed data files (the CSVs, `operating_point.json` and `data_generation.py`).
  - Binary files (`*.joblib`, `*.png`) are never converted.
  - No stored content changed. All 17 frozen hashes match `FREEZE.md`, and all 185 ML tests pass.
- **Audit:** reading identity is not written to the audit log; consider it if identity becomes viewable beyond the masked form.
