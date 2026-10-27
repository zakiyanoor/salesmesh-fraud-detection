"""
Flask REST API for the SalesMesh fraud detection system.

Exposes internal endpoints (Section 3.4.2, 3.5.2) that the React frontend
calls to retrieve flagged agent data and submit review decisions. This
API is the only channel through which the frontend accesses stored data,
per the system architecture diagram (Figure 4.2).

Endpoints:
  POST /api/login                 -> authenticate and start a session (FR-01)
  POST /api/logout                -> end the current session
  GET  /api/me                    -> username and role of the current session (protected)
  GET  /api/flagged-agents        -> list of flagged agents (protected, FR-02)
  GET  /api/all-agents            -> every agent with current status (protected)
  GET  /api/agents/<agent_id>     -> feature evidence for one agent (protected, FR-03)
  GET  /api/agents/<agent_id>/activity -> activations per day and per hour for one agent (protected, #28)
  GET  /api/threat-intelligence/ring-candidates/<candidate_id> -> one ring candidate as a graph (protected, #28)
  GET  /api/model-info             -> cutoff and test results from the frozen results files (protected, #28)
  GET  /api/customers/<ref>       -> one customer from the duplicate evidence, audited (analyst, compliance; #28)
  POST /api/review-decisions      -> propose a review decision (fraud_analyst only, FR-04)
  POST /api/review-decisions/<decision_id>/confirm
                                  -> confirm a proposed decision (compliance_officer only)
  GET  /api/review-decisions      -> list past review decisions (protected)
  GET  /api/audit-log             -> admin action audit trail (protected)
  GET  /api/analytics             -> aggregate platform statistics (protected)
  GET  /api/agent-scores          -> latest run's scores, ML and rule flags, flag_source (protected)
  GET  /api/clients               -> client reference list with commission rates (protected)
  GET  /api/detection-runs/latest -> last detection run status: started, finished, counts, error (protected)
  GET  /api/health                -> unprotected health check

Phone and national ID numbers are masked in every response (last 3 digits
visible); identity is fictional and never a model input. Full documentation:
docs/API.md.

Review decisions use dual control: a fraud_analyst proposes a decision
(status "pending_confirmation") and a different admin with the
compliance_officer role confirms it. Logins, logouts, and every decision
action are recorded in the admin_action_log table.
"""

import os
import re
from datetime import datetime
from flask import Flask, g, jsonify, request, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError
from src.db import (
    get_session, Agent, ActivationRecord, FeatureVector, FraudFlag, ReviewDecision,
    AdminActionLog, DECISION_AGREED, DECISION_OUTCOMES, AgentCategory, AgentIdentity, AgentScore, Client,
    DetectionRun, DuplicateEvidence, FLAG_SOURCES,
)
from src.auth import (
    verify_login, login_required, role_required, ROLE_FRAUD_ANALYST, ROLE_COMPLIANCE_OFFICER, ROLE_ADMIN, DEACTIVATED,
    VALID_ROLES, username_exists,
)
from src import accounts, activity, customers, model_info, reports, review, ring_graph, threat_intel
from src import audit
from src.config import load_config
from src.pipeline import compute_client_category_breakdown

# Debug, CORS and the session cookie flags come from the environment (src/config.py; issue #26).
CONFIG = load_config(os.environ)
app = Flask(__name__)
app.config.update(
    SESSION_COOKIE_SECURE=CONFIG["SESSION_COOKIE_SECURE"],
    SESSION_COOKIE_HTTPONLY=CONFIG["SESSION_COOKIE_HTTPONLY"],
    SESSION_COOKIE_SAMESITE=CONFIG["SESSION_COOKIE_SAMESITE"],
    PERMANENT_SESSION_LIFETIME=CONFIG["PERMANENT_SESSION_LIFETIME"],
)
CORS(app, supports_credentials=True, origins=CONFIG["CORS_ORIGINS"],
     expose_headers=["Content-Disposition", "X-Row-Limit-Reached"])

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
if not FLASK_SECRET_KEY:
    raise RuntimeError("FLASK_SECRET_KEY not set in .env")
app.secret_key = FLASK_SECRET_KEY

# Per-IP rate limiting. In-memory storage is per-process, which suits the
# single-process dev server; a multi-worker deployment needs a shared backend
# (e.g. storage_uri="redis://...").
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")


def log_admin_action(db_session, admin_id, action, target_agent_id=None, category="review", details=None):
    """
    Adds an audit entry to db_session without committing.

    The caller commits, so an action and its audit entry are saved (or rolled
    back) together.
    """
    return audit.record(db_session, admin_id, action, category, target_agent_id=target_agent_id, details=details,
                        request_ip=request.remote_addr)


@app.after_request
def audit_denied_requests(response):
    """
    Every 401 and 403 becomes an access_denied entry (route, role, reason), unless the route recorded it.
    Exception (#5): a 401 on GET /api/me with no session at all is only a "who is logged in?" check.
    """
    anonymous_me_check = (request.endpoint == "current_account" and response.status_code == 401
                          and not g.get("denied_admin_id") and "admin_id" not in session)
    if response.status_code in (401, 403) and not g.get("audit_recorded") and not anonymous_me_check:
        body = response.get_json(silent=True) or {}
        audit.record_now(
            g.get("denied_admin_id") or session.get("admin_id", audit.ANONYMOUS), "access_denied", "authorization",
            details={"route": request.path, "method": request.method,
                     "role": g.get("denied_role") or session.get("role"),
                     "status": response.status_code, "reason": body.get("error")},
            request_ip=request.remote_addr,
        )
    return response


def agent_id_for_flag(db_session, flag_id):
    """The agent a fraud flag was raised against, or None if it can't be traced."""
    row = (
        db_session.query(FeatureVector.agent_id)
        .join(FraudFlag, FraudFlag.vector_id == FeatureVector.vector_id)
        .filter(FraudFlag.flag_id == flag_id)
        .first()
    )
    return row[0] if row else None


def latest_vector_ids(db_session):
    """
    Query yielding the vector_id of each agent's newest FeatureVector.

    Agents are re-scored every detection cycle, so they accumulate one vector
    per analysis period. analysis_period is "YYYY-MM" so it sorts
    lexicographically; vector_id breaks ties so the pick is deterministic when
    a period was analysed more than once. Filter on `FeatureVector.vector_id
    .in_(latest_vector_ids(db_session))` to see each agent exactly once.
    """
    ranked = (
        db_session.query(
            FeatureVector.vector_id.label("vector_id"),
            func.row_number().over(
                partition_by=FeatureVector.agent_id,
                order_by=(FeatureVector.analysis_period.desc(), FeatureVector.vector_id.desc()),
            ).label("rn"),
        )
        .subquery()
    )
    return db_session.query(ranked.c.vector_id).filter(ranked.c.rn == 1)


def round_or_none(value, digits: int = 3):
    """Round a nullable column; vectors stored before a feature existed hold NULL."""
    return None if value is None else round(value, digits)


MASK_VISIBLE = 3
SCORE_EDGES = (1.1, 1.3, 2.0)
MAX_PAGE = 1000
from src.risk import REVIEW_SCORE, RISK_BANDS, risk_band, score_percentiles  # noqa: E402,F401


def mask_tail(value, visible: int = MASK_VISIBLE):
    """Data minimisation: every character but the last `visible` becomes '*'."""
    if value is None:
        return None
    text_value = str(value)
    return "*" * max(len(text_value) - visible, 0) + text_value[-visible:]


NOTES_MAX_LENGTH = 1000
# Plain text: printable characters, newlines and tabs only.
NOTES_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
# Seven or more digits (single spaces between them allowed) could be a phone or national ID number.
# Not after a letter or digit, so ids such as CUST12345678 are left alone; dates (2026-10-14) do not match.
NOTES_LONG_NUMBER = re.compile(r"(?<![0-9A-Za-z])\+?\d(?: ?\d){6,}")


def clean_notes(value):
    """
    Issue #13: (notes, None) for a valid notes value, else (None, error message).
    Trimmed, 1 to 1000 characters, plain text; long digit runs are masked like phone numbers.
    """
    if value is None:
        return None, "notes is required: give a short plain-text reason for the decision"
    if not isinstance(value, str):
        return None, "notes must be a string"
    notes = value.replace("\r\n", "\n").strip()
    if not notes:
        return None, "notes must not be empty"
    if len(notes) > NOTES_MAX_LENGTH:
        return None, f"notes must be at most {NOTES_MAX_LENGTH} characters (got {len(notes)})"
    if NOTES_CONTROL_CHARACTERS.search(notes):
        return None, "notes must be plain text (no control characters other than newlines and tabs)"
    return NOTES_LONG_NUMBER.sub(lambda m: mask_tail(re.sub(r"\D", "", m.group())), notes), None


def identity_payload(identity):
    """Fictional identity for display. Phone and national ID are always masked; the full values never leave the database."""
    if identity is None:
        return None
    return {
        "full_name": identity.full_name,
        "phone_number": mask_tail(identity.phone_number),
        "national_id_number": mask_tail(identity.national_id_number),
    }


def error_summary(error):
    if not error:
        return None
    lines = [line.strip() for line in error.strip().splitlines() if line.strip()]
    return lines[-1] if lines else None


def latest_run(db_session):
    """The newest successful detection run, or None."""
    return (
        db_session.query(DetectionRun)
        .filter(DetectionRun.status == "succeeded")
        .order_by(DetectionRun.finished_at.desc())
        .first()
    )


def latest_scores_by_agent(db_session, run=None):
    run = run or latest_run(db_session)
    if run is None:
        return {}
    return {s.agent_id: s for s in db_session.query(AgentScore).filter(AgentScore.run_id == run.run_id)}


_PERCENTILE_CACHE = {}
_PERCENTILE_CACHE_RUNS = 8


def run_percentiles(db_session, run):
    """{agent_id: score_percentile} for a finished run (cached by run_id; a finished run never changes)."""
    if run is None:
        return {}
    if run.run_id not in _PERCENTILE_CACHE:
        rows = db_session.query(AgentScore.agent_id, AgentScore.anomaly_score).filter(AgentScore.run_id == run.run_id)
        if len(_PERCENTILE_CACHE) >= _PERCENTILE_CACHE_RUNS:
            _PERCENTILE_CACHE.pop(next(iter(_PERCENTILE_CACHE)))
        _PERCENTILE_CACHE[run.run_id] = score_percentiles(dict(rows.all()))
    return _PERCENTILE_CACHE[run.run_id]


def score_payload(score, percentile=None):
    if score is None:
        return None
    return {
        "run_id": score.run_id,
        "model_version": score.model_version,
        "anomaly_score": round(score.anomaly_score, 6),
        "score_percentile": percentile,
        "threshold": round(score.threshold, 6),
        "flagged": score.flagged,
        "rule_flagged": score.rule_flagged,
        "duplicate_pairs": score.duplicate_pairs,
        "flag_source": score.flag_source,
        "risk_band": risk_band(score.flag_source, score.anomaly_score, score.threshold),
        "top_features": score.top_features.split(";") if score.top_features else [],
        "reasons": score.reasons,
        "scored_at": score.created_at.isoformat(),
    }


@app.route("/api/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Username and password are required"}), 400

    admin = verify_login(data["username"], data["password"])
    if not admin or not admin["is_active"] or admin["role"] not in VALID_ROLES:
        # The actor is unknown until a login succeeds, so failures are "anonymous".
        reason = ("invalid credentials" if not admin else "account deactivated" if not admin["is_active"]
                  else "unknown role")
        # A username that matches no account is not stored: it may be anything a person typed.
        known = admin is not None or username_exists(data["username"])
        details = ({"username": str(data["username"])[:100], "reason": reason} if known
                   else {"username": "unknown username", "reason": reason})
        audit.record_now(audit.ANONYMOUS, "login_failure", "authentication", details=details,
                         request_ip=request.remote_addr)
        g.audit_recorded = True
        message = ("Invalid username or password" if not admin else DEACTIVATED if not admin["is_active"]
                   else "This account has no valid role; an admin must assign one")
        return jsonify({"error": message}), 401

    # Permanent, so PERMANENT_SESSION_LIFETIME (SESSION_LIFETIME_MINUTES) ends the session.
    session.permanent = True
    session["admin_id"] = admin["admin_id"]
    session["username"] = admin["username"]
    session["role"] = admin["role"]

    db_session = get_session()
    try:
        log_admin_action(db_session, admin["admin_id"], "login", category="authentication",
                         details={"username": admin["username"], "role": admin["role"]})
        db_session.commit()
    finally:
        db_session.close()

    return jsonify({"message": "Login successful", "username": admin["username"], "role": admin["role"]})


@app.route("/api/logout", methods=["POST"])
def logout():
    admin_id = session.get("admin_id")
    if admin_id:
        db_session = get_session()
        try:
            log_admin_action(db_session, admin_id, "logout", category="authentication")
            db_session.commit()
        finally:
            db_session.close()
    session.clear()
    return jsonify({"message": "Logged out successfully"})


@app.route("/api/me", methods=["GET"])
@login_required
def current_account():
    """Issue #5: who is logged in. Not audited, like the other reads; see audit_denied_requests for its 401."""
    return jsonify({"username": session.get("username"), "role": session["role"]})


@app.route("/api/flagged-agents", methods=["GET"])
@login_required
def get_flagged_agents():
    db_session = get_session()
    try:
        results = (
            db_session.query(FraudFlag, FeatureVector, Agent)
            .join(FeatureVector, FraudFlag.vector_id == FeatureVector.vector_id)
            .join(Agent, FeatureVector.agent_id == Agent.agent_id)
            .filter(FraudFlag.flag_status == "flagged")
            .filter(FeatureVector.vector_id.in_(latest_vector_ids(db_session)))
            .order_by(FraudFlag.suspicion_score.desc())
            .all()
        )

        run = latest_run(db_session)
        scores, percentiles = latest_scores_by_agent(db_session, run), run_percentiles(db_session, run)
        flagged_agents = []
        for flag, vector, agent in results:
            score = scores.get(agent.agent_id)
            flagged_agents.append({
                "flag_id": flag.flag_id,
                "agent_id": agent.agent_id,
                "region": agent.region,
                "analysis_period": vector.analysis_period,
                "suspicion_score": round_or_none(flag.suspicion_score),
                "score_percentile": percentiles.get(agent.agent_id),
                "flag_status": flag.flag_status,
                "model_version": flag.model_version,
                "flag_source": score.flag_source if score else None,
                "risk_band": risk_band(score.flag_source, score.anomaly_score, score.threshold) if score else None,
                "threshold": round_or_none(score.threshold, 6) if score else None,
            })

        return jsonify({"count": len(flagged_agents), "flagged_agents": flagged_agents})
    finally:
        db_session.close()


@app.route("/api/all-agents", methods=["GET"])
@login_required
def get_all_agents():
    db_session = get_session()
    try:
        rows = (
            db_session.query(Agent, FeatureVector, FraudFlag)
            .select_from(Agent)
            .outerjoin(
                FeatureVector,
                and_(
                    FeatureVector.agent_id == Agent.agent_id,
                    FeatureVector.vector_id.in_(latest_vector_ids(db_session)),
                ),
            )
            .outerjoin(FraudFlag, FraudFlag.vector_id == FeatureVector.vector_id)
            .order_by(Agent.agent_id)
            .all()
        )

        run = latest_run(db_session)
        scores, percentiles = latest_scores_by_agent(db_session, run), run_percentiles(db_session, run)
        results = []
        for agent, vector, flag in rows:
            score = scores.get(agent.agent_id)
            results.append({
                "agent_id": agent.agent_id,
                "region": agent.region,
                "account_status": agent.account_status,
                "status": "flagged" if flag and flag.flag_status == "flagged" else "clear",
                "suspicion_score": round_or_none(flag.suspicion_score) if flag else None,
                "score_percentile": percentiles.get(agent.agent_id),
                "flag_source": score.flag_source if score else None,
                "risk_band": risk_band(score.flag_source, score.anomaly_score, score.threshold) if score else None,
                "submission_frequency": vector.submission_frequency if vector else None,
                "time_of_day_dist": round_or_none(vector.time_of_day_dist) if vector else None,
                "customer_similarity": round_or_none(vector.customer_similarity) if vector else None,
                "collusion_score": round_or_none(vector.collusion_score) if vector else None,
            })

        return jsonify({"count": len(results), "agents": results})
    finally:
        db_session.close()


@app.route("/api/agents/<agent_id>", methods=["GET"])
@login_required
def get_agent_detail(agent_id):
    db_session = get_session()
    try:
        agent = db_session.query(Agent).filter(Agent.agent_id == agent_id).first()
        if not agent:
            return jsonify({"error": "Agent not found"}), 404

        vector = (
            db_session.query(FeatureVector)
            .filter(FeatureVector.agent_id == agent_id)
            .filter(FeatureVector.vector_id.in_(latest_vector_ids(db_session)))
            .first()
        )
        flag = None
        if vector:
            flag = (
                db_session.query(FraudFlag)
                .filter(FraudFlag.vector_id == vector.vector_id)
                .first()
            )

        agent_records = (
            db_session.query(ActivationRecord)
            .filter(ActivationRecord.agent_id == agent_id)
            .all()
        )

        run = latest_run(db_session)
        score = (
            db_session.query(AgentScore)
            .filter(AgentScore.run_id == run.run_id, AgentScore.agent_id == agent_id)
            .first()
        ) if run else None
        evidence = (
            db_session.query(DuplicateEvidence)
            .filter(DuplicateEvidence.run_id == run.run_id, DuplicateEvidence.agent_id == agent_id)
            .order_by(DuplicateEvidence.reason, DuplicateEvidence.customer_id, DuplicateEvidence.client_id,
                      DuplicateEvidence.other_agent_id)
            .all()
        ) if run else []
        identity = db_session.get(AgentIdentity, agent_id)
        certifications = (
            db_session.query(AgentCategory).filter(AgentCategory.agent_id == agent_id)
            .order_by(AgentCategory.category).all()
        )

        response = {
            "agent_id": agent.agent_id,
            "region": agent.region,
            "account_status": agent.account_status,
            "risk_band": risk_band(score.flag_source, score.anomaly_score, score.threshold) if score else None,
            # Fictional identity; phone and national ID masked (last 3 digits only).
            "identity": identity_payload(identity),
            "certifications": [{
                "category": c.category,
                "certification_status": c.certification_status,
                "certified_at": c.certified_at.isoformat(),
            } for c in certifications],
            # Model result (primary flag) with the duplicate rule beside it.
            "score": score_payload(score, run_percentiles(db_session, run).get(agent_id)),
            "duplicate_evidence": [{
                "customer_id": e.customer_id,
                # Issue #28: opens the customer view; the URL and audit log carry this, not the customer ID.
                "customer_ref": customers.customer_ref(CONFIG["CUSTOMER_REF_KEY"], e.customer_id),
                "client_id": e.client_id,
                "other_agent_id": e.other_agent_id,
                "reason": e.reason,
                "record_ids": e.record_ids.split(","),
            } for e in evidence],
            "registration_timestamp": agent.registration_timestamp.isoformat() if agent.registration_timestamp else None,
            "features": {
                "submission_frequency": vector.submission_frequency,
                "time_of_day_dist": round_or_none(vector.time_of_day_dist),
                "customer_similarity": round_or_none(vector.customer_similarity),
                "collusion_score": round_or_none(vector.collusion_score),
            } if vector else None,
            "flag": {
                "flag_id": flag.flag_id,
                "suspicion_score": round_or_none(flag.suspicion_score),
                "flag_status": flag.flag_status,
                "model_version": flag.model_version,
            } if flag else None,
            # Issue #28: whether this agent's flag can be reviewed now (any flag_source but None in the
            # latest run), with its open and final decisions. The screen uses this, not the flag object.
            "review": review.review_block(db_session, vector, flag, run, viewer_id=session.get("admin_id")),
            # Pass-through context from other SalesMesh modules -- not used as a
            # detection feature, kept separate from "features" for that reason.
            # An agent can work across several clients/categories, so this is a
            # breakdown of distinct values rather than a single client_id/category.
            "context": compute_client_category_breakdown(agent_records),
        }

        return jsonify(response)
    finally:
        db_session.close()


def review_refused(error, **details):
    """
    The response for a broken review rule (issue #28). A 409 is recorded as review_refused, in its own
    transaction because the action's is rolled back; a 403 is recorded as access_denied by
    audit_denied_requests.
    """
    if error.status == 409:
        audit.record_now(session["admin_id"], "review_refused", "review",
                         details={"route": request.path, "reason": error.message, **details},
                         request_ip=request.remote_addr)
    return jsonify({"error": error.message}), error.status


def review_body():
    """(body, notes, error response): the JSON body and its cleaned notes, or a 400."""
    data = request.get_json(silent=True) or {}
    notes, notes_error = clean_notes(data.get("notes"))
    return data, notes, ((jsonify({"error": notes_error}), 400) if notes_error else None)


@app.route("/api/agents/<agent_id>/activity", methods=["GET"])
@login_required
def get_agent_activity(agent_id):
    """Issue #28: the agent's activations per day of the data window and per hour of day (src/activity.py)."""
    db_session = get_session()
    try:
        if db_session.get(Agent, agent_id) is None:
            return jsonify({"error": "Agent not found"}), 404
        return jsonify(activity.agent_activity(db_session, latest_run(db_session), agent_id))
    finally:
        db_session.close()


@app.route("/api/customers/<customer_ref>", methods=["GET"])
@role_required(ROLE_FRAUD_ANALYST, ROLE_COMPLIANCE_OFFICER)
def get_customer(customer_ref):
    """
    Issue #28: one customer from the latest run's duplicate evidence (src/customers.py). Every open is
    audited (customer_viewed, category review) and committed before the response; if that fails, nothing
    is shown. An unknown reference is a 404 and is not audited. ?from_agent= is kept only if it is a
    well-formed, existing agent ID.
    """
    db_session = get_session()
    try:
        run = latest_run(db_session)
        customer_id = customers.resolve(db_session, run, CONFIG["CUSTOMER_REF_KEY"], customer_ref) if run else None
        if customer_id is None:
            return jsonify({"error": "Customer not found in the latest run's duplicate evidence"}), 404
        source = customers.opened_from(db_session, request.args.get("from_agent"))
        view = customers.customer_view(db_session, run, customer_id, customer_ref)
        try:
            log_admin_action(
                db_session, session["admin_id"], "customer_viewed", target_agent_id=source,
                details={"customer_ref": customer_ref, "role": session.get("role"), "opened_from": source,
                         "run_id": run.run_id, "agent_count": view["agent_count"],
                         "client_count": view["client_count"], "activations_total": view["activations_total"]},
            )
            db_session.commit()
        except Exception:
            db_session.rollback()
            return jsonify({"error": "This access could not be recorded in the audit log, so the customer is not shown"}), 500
        return jsonify(view)
    finally:
        db_session.close()


@app.route("/api/review-decisions", methods=["POST"])
@role_required(ROLE_FRAUD_ANALYST)
def submit_review_decision():
    """Issue #28: a flagged agent (ML, Rule or Both in the latest run), one open proposal per flag, a note."""
    db_session = get_session()
    try:
        data = request.get_json(silent=True) or {}

        required_fields = ["flag_id", "decision_outcome"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({"error": f"Missing fields: {missing}"}), 400
        if data["decision_outcome"] not in DECISION_OUTCOMES:
            return jsonify({"error": f"decision_outcome must be one of {list(DECISION_OUTCOMES)}, "
                                     f"got {str(data['decision_outcome'])[:50]!r}"}), 400
        _, notes, invalid = review_body()
        if invalid:
            return invalid
        flag_id = str(data["flag_id"])

        try:
            decision, agent_id = review.propose(db_session, session["admin_id"], flag_id,
                                                data["decision_outcome"], notes)
            log_admin_action(
                db_session, session["admin_id"], "propose_decision", target_agent_id=agent_id,
                details={"decision_id": decision.decision_id, "flag_id": flag_id,
                         "decision_outcome": data["decision_outcome"], "notes": notes,
                         "run_id": decision.run_id, "flag_source": decision.flag_source},
            )
            db_session.commit()
        except review.ReviewError as e:
            db_session.rollback()
            return review_refused(e, flag_id=flag_id)
        except IntegrityError:
            # Two proposals at the same moment: the one-open-proposal index refuses the second.
            db_session.rollback()
            return review_refused(review.ReviewError(409, "This flag already has an open proposal"), flag_id=flag_id)

        return jsonify({
            "message": "Review decision proposed; awaiting compliance confirmation",
            "decision_id": decision.decision_id,
            "status": decision.status,
            "notes": decision.notes,
            "run_id": decision.run_id,
            "flag_source": decision.flag_source,
        }), 201
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()


@app.route("/api/review-decisions/<decision_id>/withdraw", methods=["POST"])
@role_required(ROLE_FRAUD_ANALYST)
def withdraw_review_decision(decision_id):
    """Issue #28: the proposing analyst withdraws their open proposal, with a note."""
    db_session = get_session()
    try:
        _, notes, invalid = review_body()
        if invalid:
            return invalid
        try:
            decision = review.withdraw(db_session, session["admin_id"], decision_id, notes)
        except review.ReviewError as e:
            db_session.rollback()
            return review_refused(e, decision_id=decision_id)
        log_admin_action(
            db_session, session["admin_id"], "withdraw_decision",
            target_agent_id=agent_id_for_flag(db_session, decision.flag_id),
            details={"decision_id": decision.decision_id, "flag_id": decision.flag_id,
                     "decision_outcome": decision.decision_outcome, "notes": notes},
        )
        db_session.commit()
        return jsonify({
            "message": "Proposal withdrawn",
            "decision_id": decision.decision_id,
            "status": decision.status,
            "closed_by": decision.closed_by,
            "closed_at": decision.closed_at.isoformat(),
            "close_note": decision.close_note,
        })
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()


def close_review_decision(decision_id, final_outcome, notes):
    """Issue #28: agree or overrule an open proposal (review.close), with its audit entry, in one transaction."""
    db_session = get_session()
    try:
        try:
            decision = review.close(db_session, session["admin_id"], decision_id, final_outcome, notes)
        except review.ReviewError as e:
            db_session.rollback()
            return review_refused(e, decision_id=decision_id)
        action = "agree_decision" if decision.status == DECISION_AGREED else "overrule_decision"
        log_admin_action(
            db_session, session["admin_id"], action,
            target_agent_id=agent_id_for_flag(db_session, decision.flag_id),
            details={"decision_id": decision.decision_id, "flag_id": decision.flag_id,
                     "proposed_by": decision.reviewer_id, "decision_outcome": decision.decision_outcome,
                     "final_outcome": decision.final_outcome, "notes": notes, "proposal_notes": decision.notes},
        )
        db_session.commit()
        return jsonify({
            "message": "Proposal agreed" if action == "agree_decision" else "Proposal overruled",
            "decision_id": decision.decision_id,
            "status": decision.status,
            "decision_outcome": decision.decision_outcome,
            "final_outcome": decision.final_outcome,
            "closed_by": decision.closed_by,
            "closed_at": decision.closed_at.isoformat(),
            "close_note": decision.close_note,
            "notes": decision.notes,
        })
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()


@app.route("/api/review-decisions/<decision_id>/agree", methods=["POST"])
@role_required(ROLE_COMPLIANCE_OFFICER)
def agree_review_decision(decision_id):
    """Issue #28: a compliance officer other than the proposer agrees; the note is optional."""
    data = request.get_json(silent=True) or {}
    notes = None
    if data.get("notes") is not None:
        notes, notes_error = clean_notes(data["notes"])
        if notes_error:
            return jsonify({"error": notes_error}), 400
    db_session = get_session()
    try:
        decision = db_session.get(ReviewDecision, decision_id)
        outcome = decision.decision_outcome if decision else None
    finally:
        db_session.close()
    # An unknown decision gets its 404 from review.close; the outcome is re-read under the row lock there.
    return close_review_decision(decision_id, outcome, notes)


@app.route("/api/review-decisions/<decision_id>/overrule", methods=["POST"])
@role_required(ROLE_COMPLIANCE_OFFICER)
def overrule_review_decision(decision_id):
    """Issue #28: a compliance officer other than the proposer picks the other outcome, with a note."""
    data, notes, invalid = review_body()
    if invalid:
        return invalid
    final_outcome = data.get("final_outcome")
    if final_outcome not in DECISION_OUTCOMES:
        return jsonify({"error": f"final_outcome must be one of {list(DECISION_OUTCOMES)}, "
                                 f"got {str(final_outcome)[:50]!r}"}), 400
    db_session = get_session()
    try:
        decision = db_session.get(ReviewDecision, decision_id)
        if decision is not None and final_outcome == decision.decision_outcome:
            return jsonify({"error": "final_outcome must differ from the proposed outcome; to keep it, agree instead"}), 400
    finally:
        db_session.close()
    return close_review_decision(decision_id, final_outcome, notes)


@app.route("/api/review-decisions/<decision_id>/corrections", methods=["POST"])
@role_required(ROLE_COMPLIANCE_OFFICER)
def correct_review_decision(decision_id):
    """
    Issue #28: a compliance officer other than the proposer corrects an agreed or overruled decision, with a
    note. The decision itself is never changed; the correction is a new row, and the history shows both.
    """
    data, notes, invalid = review_body()
    if invalid:
        return invalid
    new_outcome, expected = data.get("new_outcome"), data.get("expected_current_outcome")
    for name, value in (("new_outcome", new_outcome), ("expected_current_outcome", expected)):
        if value not in DECISION_OUTCOMES:
            return jsonify({"error": f"{name} must be one of {list(DECISION_OUTCOMES)}, got {str(value)[:50]!r}"}), 400
    if new_outcome == expected:
        return jsonify({"error": "new_outcome must differ from the current outcome"}), 400
    db_session = get_session()
    try:
        try:
            decision, correction = review.correct(db_session, session["admin_id"], decision_id, new_outcome,
                                                  expected, notes)
        except review.ReviewError as e:
            db_session.rollback()
            return review_refused(e, decision_id=decision_id)
        log_admin_action(
            db_session, session["admin_id"], "correct_decision",
            target_agent_id=agent_id_for_flag(db_session, decision.flag_id),
            details={"decision_id": decision_id, "correction_id": correction.correction_id,
                     "flag_id": decision.flag_id, "previous_outcome": correction.previous_outcome,
                     "new_outcome": correction.new_outcome, "notes": notes},
        )
        db_session.commit()
        return jsonify({
            "message": "Correction recorded",
            "decision_id": decision_id,
            "correction_id": correction.correction_id,
            "previous_outcome": correction.previous_outcome,
            "new_outcome": correction.new_outcome,
            "corrected_by": correction.corrected_by,
            "corrected_at": correction.corrected_at.isoformat(),
            "note": correction.note,
            "effective_outcome": correction.new_outcome,
        }), 201
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()


@app.route("/api/review-decisions", methods=["GET"])
@login_required
def list_review_decisions():
    """
    Every decision, newest first, with its closing fields, corrections, the outcome in force, whether it is
    overdue (open for more than review.OVERDUE_HOURS) and whether its agent is still flagged (issue #28).
    """
    db_session = get_session()
    try:
        decisions = (
            db_session.query(ReviewDecision)
            .order_by(ReviewDecision.decision_timestamp.desc())
            .all()
        )
        agents = dict(db_session.query(FraudFlag.flag_id, FeatureVector.agent_id)
                      .join(FeatureVector, FraudFlag.vector_id == FeatureVector.vector_id)
                      .filter(FraudFlag.flag_id.in_({d.flag_id for d in decisions})).all()) if decisions else {}
        sources = {agent_id: s.flag_source for agent_id, s in latest_scores_by_agent(db_session).items()}
        now = datetime.utcnow()
        results = []
        for d in decisions:
            agent_id = agents.get(d.flag_id)
            results.append(review.decision_payload(
                d, agent_id, still_flagged=sources.get(agent_id) in review.REVIEWABLE_SOURCES, now=now))
        return jsonify({"count": len(results), "overdue_hours": review.OVERDUE_HOURS, "decisions": results})
    finally:
        db_session.close()


@app.route("/api/audit-log", methods=["GET"])
@role_required(ROLE_ADMIN)
def get_audit_log():
    """Newest first. Filters: category, actor, agent_id, date_from, date_to; paging: limit (max 1000), offset."""
    try:
        limit = min(int(request.args.get("limit", 100)), audit.MAX_LIMIT)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        return jsonify({"error": "limit and offset must be integers"}), 400
    db_session = get_session()
    try:
        try:
            query = audit.filtered_query(db_session, request.args)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        total = query.count()
        entries = query.offset(offset).limit(limit).all()
        return jsonify({"total": total, "count": len(entries), "offset": offset, "limit": limit,
                        "filters": audit.active_filters(request.args),
                        "entries": [audit.entry_payload(e) for e in entries]})
    finally:
        db_session.close()


@app.route("/api/analytics", methods=["GET"])
@login_required
def get_analytics():
    db_session = get_session()
    try:
        vectors = (
            db_session.query(FeatureVector)
            .filter(FeatureVector.vector_id.in_(latest_vector_ids(db_session)))
            .all()
        )
        agents = {a.agent_id: a for a in db_session.query(Agent).all()}
        flags = {f.vector_id: f for f in db_session.query(FraudFlag).all()}

        # Scores are LOF anomaly scores (about 1 for typical agents, unbounded
        # above), not 0-1 probabilities; buckets are placed around the cutoff.
        run = latest_run(db_session)
        cutoff = run.threshold if run and run.threshold else 1.445
        edges = [(f"< {SCORE_EDGES[0]:.1f}", 0, SCORE_EDGES[0]),
                 (f"{SCORE_EDGES[0]:.1f}-{SCORE_EDGES[1]:.1f}", SCORE_EDGES[0], SCORE_EDGES[1]),
                 (f"{SCORE_EDGES[1]:.1f}-cutoff", SCORE_EDGES[1], cutoff),
                 (f"cutoff ({cutoff:.3f})-{SCORE_EDGES[2]:.1f}", cutoff, SCORE_EDGES[2]),
                 (f">= {SCORE_EDGES[2]:.1f}", SCORE_EDGES[2], float("inf"))]
        score_buckets = {label: 0 for label, _, _ in edges}
        region_counts: dict = {}
        freq_sum = dist_sum = sim_sum = coll_sum = 0.0
        coll_count = 0

        for v in vectors:
            flag = flags.get(v.vector_id)
            agent = agents.get(v.agent_id)
            if not flag or not agent:
                continue
            freq_sum += v.submission_frequency
            dist_sum += v.time_of_day_dist
            sim_sum += v.customer_similarity
            # Issue #28: the fourth signal; vectors written before the column existed have none.
            if v.collusion_score is not None:
                coll_sum += v.collusion_score
                coll_count += 1

            bucket_label = next(label for label, low, high in edges if low <= flag.suspicion_score < high)
            score_buckets[bucket_label] += 1

            region_counts.setdefault(agent.region, {"flagged": 0, "total": 0})
            region_counts[agent.region]["total"] += 1
            if flag.flag_status == "flagged":
                region_counts[agent.region]["flagged"] += 1

        count = len(vectors) or 1
        sources = {s: 0 for s in FLAG_SOURCES}
        for score in latest_scores_by_agent(db_session, run).values():
            sources[score.flag_source] += 1
        return jsonify({
            "cutoff": round(cutoff, 6),
            "flag_sources": [{"flag_source": s, "count": n} for s, n in sources.items()],
            "score_distribution": [{"bucket": k, "count": v} for k, v in score_buckets.items()],
            "region_breakdown": [{"region": r, **c} for r, c in region_counts.items()],
            "platform_averages": {
                "submission_frequency": round(freq_sum / count, 1),
                "time_of_day_dist": round(dist_sum / count, 3),
                "customer_similarity": round(sim_sum / count, 3),
                "collusion_score": round(coll_sum / coll_count, 3) if coll_count else None,
            },
            # Issue #28: proposal counts and the overrule rate (src/review.py, review_stats).
            "review": review.review_stats(db_session),
        })
    finally:
        db_session.close()


@app.route("/api/agent-scores", methods=["GET"])
@login_required
def list_agent_scores():
    """Latest detection run's scores, highest first; optional flag_source filter and paging."""
    flag_source = request.args.get("flag_source")
    if flag_source is not None and flag_source not in FLAG_SOURCES:
        return jsonify({"error": f"flag_source must be one of {list(FLAG_SOURCES)}"}), 400
    try:
        limit = min(int(request.args.get("limit", 100)), MAX_PAGE)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        return jsonify({"error": "limit and offset must be integers"}), 400
    db_session = get_session()
    try:
        run = latest_run(db_session)
        if run is None:
            return jsonify({"run_id": None, "total": 0, "count": 0, "scores": []})
        query = db_session.query(AgentScore).filter(AgentScore.run_id == run.run_id)
        if flag_source:
            query = query.filter(AgentScore.flag_source == flag_source)
        total = query.count()
        rows = query.order_by(AgentScore.anomaly_score.desc(), AgentScore.agent_id).offset(offset).limit(limit).all()
        percentiles = run_percentiles(db_session, run)
        return jsonify({
            "run_id": run.run_id, "model_version": run.model_version, "threshold": round_or_none(run.threshold, 6),
            "total": total, "count": len(rows), "offset": offset,
            "scores": [{"agent_id": s.agent_id, **score_payload(s, percentiles.get(s.agent_id))} for s in rows],
        })
    finally:
        db_session.close()


@app.route("/api/detection-runs/latest", methods=["GET"])
@login_required
def latest_detection_run():
    """Status of the most recent detection run (any outcome), for the scheduler (issue #12)."""
    db_session = get_session()
    try:
        run = db_session.query(DetectionRun).order_by(DetectionRun.started_at.desc()).first()
        if run is None:
            return jsonify({"run": None})
        return jsonify({"run": {
            "run_id": run.run_id,
            "trigger": run.trigger,
            "status": run.status,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "model_version": run.model_version,
            "threshold": round_or_none(run.threshold, 6),
            "agents_scored": run.agents_scored,
            "flagged_count": run.flagged_count,
            "rule_flagged_count": run.rule_flagged_count,
            "both_count": run.both_count,
            # Only the final "Type: message" line; the traceback (server paths) stays in the database.
            "error": error_summary(run.error),
        }})
    finally:
        db_session.close()


@app.route("/api/clients", methods=["GET"])
@login_required
def list_clients():
    db_session = get_session()
    try:
        clients = db_session.query(Client).order_by(Client.client_id).all()
        return jsonify({"count": len(clients), "clients": [{
            "client_id": c.client_id, "name": c.name, "category": c.category,
            "commission_per_activation_kes": c.commission_per_activation_kes,
        } for c in clients]})
    finally:
        db_session.close()


def _threat_view(name):
    def view():
        db_session = get_session()
        try:
            run = threat_intel.latest_run(db_session)
            if run is None:
                return jsonify({"error": "No successful detection run yet"}), 404
            # Stored with the run (issue #28); computed now only for a run without a current stored copy.
            return jsonify(threat_intel.view_payload(db_session, run, name))
        finally:
            db_session.close()

    view.__name__ = f"threat_intelligence_{name.replace('-', '_')}"
    return login_required(view)


# Read only, any authenticated role (issue #18).
for _name in threat_intel.VIEWS:
    app.add_url_rule(f"/api/threat-intelligence/{_name}", view_func=_threat_view(_name), methods=["GET"])


@app.route("/api/threat-intelligence/ring-candidates/<candidate_id>", methods=["GET"])
@login_required
def get_ring_graph(candidate_id):
    """
    Issue #28: one ring candidate as a graph (src/ring_graph.py): members, shared-customer counts per pair,
    county per member and the group's activations per day. Open to every role, like the other threat
    intelligence views; computed on request, nothing is written.
    """
    db_session = get_session()
    try:
        run = threat_intel.latest_run(db_session)
        ring = ring_graph.candidate(db_session, run, candidate_id) if run else None
        if ring is None:
            return jsonify({"error": "Ring candidate not found in the latest run"}), 404
        return jsonify(ring_graph.ring_graph(db_session, run, ring))
    finally:
        db_session.close()


@app.route("/api/model-info", methods=["GET"])
@login_required
def get_model_info():
    """Issue #28: the cutoff and the test results, read from the frozen results files (src/model_info.py)."""
    return jsonify(model_info.model_info())


def _download(name, extension, mimetype, build):
    """Builds a report, audits the download (category report) and sends it as an attachment."""
    db_session = get_session()
    try:
        try:
            content, row_count, extra = build(db_session)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except LookupError as e:
            return jsonify({"error": str(e)}), 404
        filename = f"{name}_{datetime.utcnow():%Y-%m-%d}.{extension}"
        log_admin_action(db_session, session["admin_id"], "report_download", category="report", details={
            "report": f"{name}.{extension}", "filename": filename, "filters": audit.active_filters(request.args),
            "row_count": row_count, "sha256": reports.sha256(content), "bytes": len(content), **extra})
        db_session.commit()
        response = app.response_class(content, mimetype=mimetype)
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.headers["Cache-Control"] = "no-store"
        if extra.get("truncated"):
            # The export stopped at the row cap; the page says so after the download.
            response.headers["X-Row-Limit-Reached"] = "true"
        return response
    finally:
        db_session.close()


def _latest_run_or_fail(db_session):
    run = latest_run(db_session)
    if run is None:
        raise LookupError("No successful detection run yet")
    return run


@app.route("/api/reports/flagged-agents.csv", methods=["GET"])
@role_required(ROLE_ADMIN)
def report_flagged_agents():
    def build(db_session):
        run = _latest_run_or_fail(db_session)
        content, rows = reports.flagged_agents_csv(db_session, run)
        return content, rows, {"run_id": run.run_id}

    return _download("flagged-agents", "csv", "text/csv", build)


@app.route("/api/reports/audit-log.csv", methods=["GET"])
@role_required(ROLE_ADMIN)
def report_audit_log():
    def build(db_session):
        content, rows, truncated = reports.audit_log_csv(db_session, request.args)
        return content, rows, {"cap": reports.AUDIT_CSV_CAP, "truncated": truncated}

    return _download("audit-log", "csv", "text/csv", build)


@app.route("/api/reports/detection-summary.pdf", methods=["GET"])
@role_required(ROLE_ADMIN)
def report_detection_summary():
    def build(db_session):
        run = _latest_run_or_fail(db_session)
        content, rows, extra = reports.detection_summary_pdf(db_session, run, session["admin_id"])
        return content, rows, {"run_id": run.run_id, **extra}

    return _download("detection-summary", "pdf", "application/pdf", build)


@app.route("/api/admin/accounts", methods=["GET"])
@role_required(ROLE_ADMIN)
def list_admin_accounts():
    db_session = get_session()
    try:
        found = accounts.list_accounts(db_session)
        return jsonify({"count": len(found), "accounts": found})
    finally:
        db_session.close()


def _account_change(apply, action, details):
    """Runs one account change; audits it (category admin) only when something changed."""
    db_session = get_session()
    try:
        try:
            account, changed_details = apply(db_session)
        except accounts.AccountError as e:
            db_session.rollback()
            return jsonify({"error": str(e)}), e.status
        if changed_details is None:
            db_session.rollback()
            return jsonify({"message": "No change", "changed": False, "account": accounts.account_payload(account)})
        log_admin_action(db_session, session["admin_id"], action, category="admin",
                         details={"target_admin_id": account.admin_id, "target_username": account.username,
                                  **details, **changed_details})
        db_session.commit()
        return jsonify({"message": "Account updated", "changed": True, "account": accounts.account_payload(account)})
    finally:
        db_session.close()


@app.route("/api/admin/accounts/<admin_id>/role", methods=["PATCH"])
@role_required(ROLE_ADMIN)
def change_account_role(admin_id):
    data = request.get_json(silent=True) or {}
    if "role" not in data:
        return jsonify({"error": "Missing field: role"}), 400

    def apply(db_session):
        account, old_role = accounts.change_role(db_session, session["admin_id"], admin_id, data["role"])
        return account, (None if old_role == account.role else {"old_role": old_role, "new_role": account.role})

    return _account_change(apply, "role_change", {})


@app.route("/api/admin/accounts/<admin_id>/deactivate", methods=["POST"])
@role_required(ROLE_ADMIN)
def deactivate_account(admin_id):
    def apply(db_session):
        account, was_active = accounts.set_active(db_session, session["admin_id"], admin_id, False)
        return account, ({"role": account.role} if was_active else None)

    return _account_change(apply, "account_deactivated", {})


@app.route("/api/admin/accounts/<admin_id>/reactivate", methods=["POST"])
@role_required(ROLE_ADMIN)
def reactivate_account(admin_id):
    def apply(db_session):
        account, was_active = accounts.set_active(db_session, session["admin_id"], admin_id, True)
        return account, (None if was_active else {"role": account.role})

    return _account_change(apply, "account_reactivated", {})


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=CONFIG["DEBUG"], port=5000)