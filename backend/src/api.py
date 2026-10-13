"""
Flask REST API for the SalesMesh fraud detection system.

Exposes internal endpoints (Section 3.4.2, 3.5.2) that the React frontend
calls to retrieve flagged agent data and submit review decisions. This
API is the only channel through which the frontend accesses stored data,
per the system architecture diagram (Figure 4.2).

Endpoints:
  POST /api/login                 -> authenticate and start a session (FR-01)
  POST /api/logout                -> end the current session
  GET  /api/flagged-agents        -> list of flagged agents (protected, FR-02)
  GET  /api/all-agents            -> every agent with current status (protected)
  GET  /api/agents/<agent_id>     -> feature evidence for one agent (protected, FR-03)
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
import uuid
from datetime import datetime
from flask import Flask, g, jsonify, request, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import and_, func
from src.db import (
    get_session, Agent, ActivationRecord, FeatureVector, FraudFlag, ReviewDecision,
    AdminActionLog, DECISION_PENDING, DECISION_CONFIRMED, AgentCategory, AgentIdentity, AgentScore, Client,
    DetectionRun, DuplicateEvidence, FLAG_SOURCES,
)
from src.auth import (
    verify_login, login_required, role_required, ROLE_FRAUD_ANALYST, ROLE_COMPLIANCE_OFFICER, ROLE_ADMIN, DEACTIVATED,
)
from src import accounts
from src import audit
from src.pipeline import compute_client_category_breakdown

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost:5173"])

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
    """Every 401 and 403 becomes an access_denied entry (route, role, reason), unless the route recorded it."""
    if response.status_code in (401, 403) and not g.get("audit_recorded"):
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


def mask_tail(value, visible: int = MASK_VISIBLE):
    """Data minimisation: every character but the last `visible` becomes '*'."""
    if value is None:
        return None
    text_value = str(value)
    return "*" * max(len(text_value) - visible, 0) + text_value[-visible:]


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


def score_payload(score):
    if score is None:
        return None
    return {
        "run_id": score.run_id,
        "model_version": score.model_version,
        "anomaly_score": round(score.anomaly_score, 6),
        "threshold": round(score.threshold, 6),
        "flagged": score.flagged,
        "rule_flagged": score.rule_flagged,
        "duplicate_pairs": score.duplicate_pairs,
        "flag_source": score.flag_source,
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
    if not admin or not admin["is_active"]:
        # The actor is unknown until a login succeeds, so failures are "anonymous".
        reason = "invalid credentials" if not admin else "account deactivated"
        audit.record_now(audit.ANONYMOUS, "login_failure", "authentication",
                         details={"username": str(data["username"])[:100], "reason": reason},
                         request_ip=request.remote_addr)
        g.audit_recorded = True
        message = "Invalid username or password" if not admin else DEACTIVATED
        return jsonify({"error": message}), 401

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

        scores = latest_scores_by_agent(db_session)
        flagged_agents = []
        for flag, vector, agent in results:
            score = scores.get(agent.agent_id)
            flagged_agents.append({
                "flag_id": flag.flag_id,
                "agent_id": agent.agent_id,
                "region": agent.region,
                "analysis_period": vector.analysis_period,
                "suspicion_score": round_or_none(flag.suspicion_score),
                "flag_status": flag.flag_status,
                "model_version": flag.model_version,
                "flag_source": score.flag_source if score else None,
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

        scores = latest_scores_by_agent(db_session)
        results = []
        for agent, vector, flag in rows:
            score = scores.get(agent.agent_id)
            results.append({
                "agent_id": agent.agent_id,
                "region": agent.region,
                "account_status": agent.account_status,
                "status": "flagged" if flag and flag.flag_status == "flagged" else "clear",
                "suspicion_score": round_or_none(flag.suspicion_score) if flag else None,
                "flag_source": score.flag_source if score else None,
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
            # Fictional identity; phone and national ID masked (last 3 digits only).
            "identity": identity_payload(identity),
            "certifications": [{
                "category": c.category,
                "certification_status": c.certification_status,
                "certified_at": c.certified_at.isoformat(),
            } for c in certifications],
            # Model result (primary flag) with the duplicate rule beside it.
            "score": score_payload(score),
            "duplicate_evidence": [{
                "customer_id": e.customer_id,
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
            # Pass-through context from other SalesMesh modules -- not used as a
            # detection feature, kept separate from "features" for that reason.
            # An agent can work across several clients/categories, so this is a
            # breakdown of distinct values rather than a single client_id/category.
            "context": compute_client_category_breakdown(agent_records),
        }

        return jsonify(response)
    finally:
        db_session.close()


@app.route("/api/review-decisions", methods=["POST"])
@role_required(ROLE_FRAUD_ANALYST)
def submit_review_decision():
    db_session = get_session()
    try:
        data = request.get_json()

        required_fields = ["flag_id", "decision_outcome"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({"error": f"Missing fields: {missing}"}), 400

        flag = db_session.query(FraudFlag).filter(FraudFlag.flag_id == data["flag_id"]).first()
        if not flag:
            return jsonify({"error": "Fraud flag not found"}), 404

        decision = ReviewDecision(
            decision_id=f"RD{uuid.uuid4().hex[:8]}",
            flag_id=data["flag_id"],
            reviewer_id=session["admin_id"],
            decision_outcome=data["decision_outcome"],
            decision_timestamp=datetime.utcnow(),
            status=DECISION_PENDING,
        )
        db_session.add(decision)
        log_admin_action(
            db_session, session["admin_id"], "propose_decision",
            target_agent_id=agent_id_for_flag(db_session, data["flag_id"]),
            details={"decision_id": decision.decision_id, "flag_id": data["flag_id"],
                     "decision_outcome": data["decision_outcome"]},
        )
        db_session.commit()

        return jsonify({
            "message": "Review decision proposed; awaiting compliance confirmation",
            "decision_id": decision.decision_id,
            "status": decision.status,
        }), 201
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()


@app.route("/api/review-decisions/<decision_id>/confirm", methods=["POST"])
@role_required(ROLE_COMPLIANCE_OFFICER)
def confirm_review_decision(decision_id):
    db_session = get_session()
    try:
        # Row lock so two concurrent confirmations can't both see "pending".
        decision = (
            db_session.query(ReviewDecision)
            .filter(ReviewDecision.decision_id == decision_id)
            .with_for_update()
            .first()
        )
        if not decision:
            return jsonify({"error": "Review decision not found"}), 404
        if decision.reviewer_id == session["admin_id"]:
            return jsonify({"error": "A decision cannot be confirmed by the admin who proposed it"}), 403
        if decision.status != DECISION_PENDING:
            return jsonify({"error": f"Decision is already {decision.status}"}), 409

        decision.status = DECISION_CONFIRMED
        decision.confirmed_by = session["admin_id"]
        log_admin_action(
            db_session, session["admin_id"], "confirm_decision",
            target_agent_id=agent_id_for_flag(db_session, decision.flag_id),
            details={"decision_id": decision.decision_id, "flag_id": decision.flag_id,
                     "proposed_by": decision.reviewer_id},
        )
        db_session.commit()

        return jsonify({
            "message": "Review decision confirmed",
            "decision_id": decision.decision_id,
            "status": decision.status,
            "confirmed_by": decision.confirmed_by,
        })
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()


@app.route("/api/review-decisions", methods=["GET"])
@login_required
def list_review_decisions():
    db_session = get_session()
    try:
        decisions = (
            db_session.query(ReviewDecision)
            .order_by(ReviewDecision.decision_timestamp.desc())
            .all()
        )
        results = []
        for d in decisions:
            flag = db_session.query(FraudFlag).filter(FraudFlag.flag_id == d.flag_id).first()
            vector = (
                db_session.query(FeatureVector).filter(FeatureVector.vector_id == flag.vector_id).first()
                if flag else None
            )
            results.append({
                "decision_id": d.decision_id,
                "agent_id": vector.agent_id if vector else None,
                "reviewer_id": d.reviewer_id,
                "decision_outcome": d.decision_outcome,
                "decision_timestamp": d.decision_timestamp.isoformat(),
                "status": d.status,
                "confirmed_by": d.confirmed_by,
            })
        return jsonify({"count": len(results), "decisions": results})
    finally:
        db_session.close()


@app.route("/api/audit-log", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_COMPLIANCE_OFFICER)
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
        freq_sum = dist_sum = sim_sum = 0.0

        for v in vectors:
            flag = flags.get(v.vector_id)
            agent = agents.get(v.agent_id)
            if not flag or not agent:
                continue
            freq_sum += v.submission_frequency
            dist_sum += v.time_of_day_dist
            sim_sum += v.customer_similarity

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
            },
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
        return jsonify({
            "run_id": run.run_id, "model_version": run.model_version, "threshold": round_or_none(run.threshold, 6),
            "total": total, "count": len(rows), "offset": offset,
            "scores": [{"agent_id": s.agent_id, **score_payload(s)} for s in rows],
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
    app.run(debug=True, port=5000)