"""
Flask REST API for the SalesMesh fraud detection system.

Exposes internal endpoints (Section 3.4.2, 3.5.2) that the Streamlit dashboard
will call to retrieve flagged agent data and submit review decisions. This
API is the only channel through which the dashboard accesses stored data,
per the system architecture diagram (Figure 4.2).

Endpoints:
  GET  /api/flagged-agents        -> list of flagged agents with suspicion scores
  GET  /api/agents/<agent_id>     -> feature evidence for one agent
  POST /api/review-decisions      -> submit a review decision for a flag
"""

from flask import Flask, jsonify, request
from src.db import get_session, Agent, FeatureVector, FraudFlag, ReviewDecision
from datetime import datetime
import uuid

app = Flask(__name__)


@app.route("/api/flagged-agents", methods=["GET"])
def get_flagged_agents():
    session = get_session()
    try:
        results = (
            session.query(FraudFlag, FeatureVector, Agent)
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
        session.close()


@app.route("/api/agents/<agent_id>", methods=["GET"])
def get_agent_detail(agent_id):
    session = get_session()
    try:
        agent = session.query(Agent).filter(Agent.agent_id == agent_id).first()
        if not agent:
            return jsonify({"error": "Agent not found"}), 404

        vector = (
            session.query(FeatureVector)
            .filter(FeatureVector.agent_id == agent_id)
            .first()
        )
        flag = None
        if vector:
            flag = (
                session.query(FraudFlag)
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
        session.close()


@app.route("/api/review-decisions", methods=["POST"])
def submit_review_decision():
    session = get_session()
    try:
        data = request.get_json()

        required_fields = ["flag_id", "reviewer_id", "decision_outcome"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({"error": f"Missing fields: {missing}"}), 400

        flag = session.query(FraudFlag).filter(FraudFlag.flag_id == data["flag_id"]).first()
        if not flag:
            return jsonify({"error": "Fraud flag not found"}), 404

        decision = ReviewDecision(
            decision_id=f"RD{uuid.uuid4().hex[:8]}",
            flag_id=data["flag_id"],
            reviewer_id=data["reviewer_id"],
            decision_outcome=data["decision_outcome"],
            decision_timestamp=datetime.utcnow(),
        )
        session.add(decision)
        session.commit()

        return jsonify({
            "message": "Review decision recorded",
            "decision_id": decision.decision_id,
        }), 201
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)