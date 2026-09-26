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
  GET  /api/health                -> unprotected health check

Review decisions use dual control: a fraud_analyst proposes a decision
(status "pending_confirmation") and a different admin with the
compliance_officer role confirms it. Logins, logouts, and every decision
action are recorded in the admin_action_log table.
"""

import os
import uuid
from datetime import datetime
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import and_, func
from src.db import (
    get_session, Agent, ActivationRecord, FeatureVector, FraudFlag, ReviewDecision,
    AdminActionLog, DECISION_PENDING, DECISION_CONFIRMED,
)
from src.auth import (
    verify_login, login_required, role_required, ROLE_FRAUD_ANALYST, ROLE_COMPLIANCE_OFFICER,
)

app = Flask(__name__)
CORS(app, supports_credentials=True)

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
if not FLASK_SECRET_KEY:
    raise RuntimeError("FLASK_SECRET_KEY not set in .env")
app.secret_key = FLASK_SECRET_KEY

# Per-IP rate limiting. In-memory storage is per-process, which suits the
# single-process dev server; a multi-worker deployment needs a shared backend
# (e.g. storage_uri="redis://...").
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")


def log_admin_action(db_session, admin_id, action, target_agent_id=None):
    """
    Adds an AdminActionLog row to db_session without committing.

    The caller commits, so an action and its audit entry are saved (or rolled
    back) together.
    """
    db_session.add(AdminActionLog(
        log_id=f"AL{uuid.uuid4().hex}",
        admin_id=admin_id,
        action=action,
        target_agent_id=target_agent_id,
        timestamp=datetime.utcnow(),
    ))


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


def client_category_context(db_session, agent_id):
    """Distinct client accounts and product categories this agent has activated for."""
    client_ids = sorted({
        row[0] for row in
        db_session.query(ActivationRecord.client_id)
        .filter(ActivationRecord.agent_id == agent_id)
        .distinct()
        if row[0] is not None
    })
    categories = sorted({
        row[0] for row in
        db_session.query(ActivationRecord.category)
        .filter(ActivationRecord.agent_id == agent_id)
        .distinct()
        if row[0] is not None
    })
    return {"client_ids": client_ids, "categories": categories}


@app.route("/api/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Username and password are required"}), 400

    admin = verify_login(data["username"], data["password"])
    if not admin:
        return jsonify({"error": "Invalid username or password"}), 401

    session["admin_id"] = admin["admin_id"]
    session["username"] = admin["username"]
    session["role"] = admin["role"]

    db_session = get_session()
    try:
        log_admin_action(db_session, admin["admin_id"], "login")
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
            log_admin_action(db_session, admin_id, "logout")
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

        flagged_agents = []
        for flag, vector, agent in results:
            flagged_agents.append({
                "flag_id": flag.flag_id,
                "agent_id": agent.agent_id,
                "region": agent.region,
                "analysis_period": vector.analysis_period,
                "suspicion_score": round_or_none(flag.suspicion_score),
                "flag_status": flag.flag_status,
                "model_version": flag.model_version,
            })

        return jsonify({"count": len(flagged_agents), "flagged_agents": flagged_agents})
    finally:
        db_session.close()


@app.route("/api/all-agents", methods=["GET"])
@login_required
def get_all_agents():
    db_session = get_session()
    try:
        vectors = (
            db_session.query(FeatureVector)
            .filter(FeatureVector.vector_id.in_(latest_vector_ids(db_session)))
            .all()
        )
        agents_by_id = {a.agent_id: a for a in db_session.query(Agent).all()}
        flags_by_vector = {f.vector_id: f for f in db_session.query(FraudFlag).all()}

        results = []
        for vector in vectors:
            agent = agents_by_id.get(vector.agent_id)
            if not agent:
                continue
            flag = flags_by_vector.get(vector.vector_id)

            results.append({
                "agent_id": agent.agent_id,
                "region": agent.region,
                "status": flag.flag_status if flag else "clear",
                "suspicion_score": round_or_none(flag.suspicion_score) if flag else None,
                "submission_frequency": vector.submission_frequency,
                "time_of_day_dist": round_or_none(vector.time_of_day_dist),
                "customer_similarity": round_or_none(vector.customer_similarity),
                "collusion_score": round_or_none(vector.collusion_score),
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

        response = {
            "agent_id": agent.agent_id,
            "region": agent.region,
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
            "context": client_category_context(db_session, agent_id),
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
@login_required
def get_audit_log():
    db_session = get_session()
    try:
        entries = (
            db_session.query(AdminActionLog)
            .order_by(AdminActionLog.timestamp.desc(), AdminActionLog.log_id)
            .all()
        )
        results = [{
            "log_id": e.log_id,
            "admin_id": e.admin_id,
            "action": e.action,
            "target_agent_id": e.target_agent_id,
            "timestamp": e.timestamp.isoformat(),
        } for e in entries]
        return jsonify({"count": len(results), "entries": results})
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

        score_buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
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

            bucket_index = min(int(flag.suspicion_score * 5), 4)
            bucket_label = list(score_buckets.keys())[bucket_index]
            score_buckets[bucket_label] += 1

            region_counts.setdefault(agent.region, {"flagged": 0, "total": 0})
            region_counts[agent.region]["total"] += 1
            if flag.flag_status == "flagged":
                region_counts[agent.region]["flagged"] += 1

        count = len(vectors) or 1
        return jsonify({
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


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)