"""
Flask REST API for the SalesMesh fraud detection system.

Exposes internal endpoints (Section 3.4.2, 3.5.2) that the React dashboard
calls to retrieve flagged agent data and submit review decisions. This
API is the only channel through which the dashboard accesses stored data,
per the system architecture diagram (Figure 4.2).

Endpoints:
  POST /api/login                 -> authenticate and start a session (FR-01)
  POST /api/logout                -> end the current session
  GET  /api/flagged-agents        -> list of flagged agents (protected, FR-02)
  GET  /api/agents/<agent_id>     -> feature evidence for one agent (protected, FR-03)
  POST /api/review-decisions      -> submit a review decision (protected, FR-04)
  GET  /api/review-decisions      -> list past review decisions (protected)
  GET  /api/analytics             -> aggregate platform statistics (protected)
  GET  /api/health                -> unprotected health check
"""

import os
import uuid
from datetime import datetime
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from src.db import get_session, Agent, FeatureVector, FraudFlag, ReviewDecision
from src.auth import verify_login, login_required

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost:5173"])

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
if not FLASK_SECRET_KEY:
    raise RuntimeError("FLASK_SECRET_KEY not set in .env")
app.secret_key = FLASK_SECRET_KEY


@app.route("/api/login", methods=["POST"])
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

    return jsonify({"message": "Login successful", "username": admin["username"]})


@app.route("/api/logout", methods=["POST"])
def logout():
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
                "suspicion_score": round(flag.suspicion_score, 3),
                "flag_status": flag.flag_status,
                "model_version": flag.model_version,
            })

        return jsonify({"count": len(flagged_agents), "flagged_agents": flagged_agents})
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
                "submission_frequency": vector.submission_frequency if vector else None,
                "time_of_day_dist": round(vector.time_of_day_dist, 3) if vector else None,
                "customer_similarity": round(vector.customer_similarity, 3) if vector else None,
            } if vector else None,
            "flag": {
                "flag_id": flag.flag_id,
                "suspicion_score": round(flag.suspicion_score, 3),
                "flag_status": flag.flag_status,
                "model_version": flag.model_version,
            } if flag else None,
        }

        return jsonify(response)
    finally:
        db_session.close()


@app.route("/api/review-decisions", methods=["POST"])
@login_required
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
        )
        db_session.add(decision)
        db_session.commit()

        return jsonify({
            "message": "Review decision recorded",
            "decision_id": decision.decision_id,
        }), 201
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
            })
        return jsonify({"count": len(results), "decisions": results})
    finally:
        db_session.close()


@app.route("/api/analytics", methods=["GET"])
@login_required
def get_analytics():
    db_session = get_session()
    try:
        vectors = db_session.query(FeatureVector).all()
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