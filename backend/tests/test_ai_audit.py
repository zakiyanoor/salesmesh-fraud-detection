"""AI decisions in the audit log (issue #18): one entry per detection run, one per changed or new flag."""

import json

import pandas as pd
import pytest
from sqlalchemy import text

from src import ml_bridge
from src.db import AdminActionLog, engine, get_session
from src.scoring_service import flag_changes, run_detection_cycle

SYSTEM = "system:lof_v3_4f"


def scores(rows):
    return pd.DataFrame([{"agent_id": a, "flag_source": s, "anomaly_score": 2.0, "threshold": 1.4448,
                          "top_features": "collusion_score;submission_frequency", "reasons": "r", "model_version": "lof_v3_4f"}
                         for a, s in rows])


def test_flag_changes_by_hand() -> None:
    previous = {"A1": "None", "A2": "ML", "A3": "Both", "A4": "Rule"}
    current = scores([("A1", "ML"), ("A2", "ML"), ("A3", "None"), ("A4", "Both"), ("A5", "Rule"), ("A6", "None")])
    changes = {c["agent_id"]: c for c in flag_changes(previous, current)}
    assert set(changes) == {"A1", "A3", "A4", "A5"}
    assert changes["A1"]["change"] == "newly flagged" and changes["A5"]["change"] == "newly flagged"
    assert changes["A3"]["change"] == "cleared" and changes["A4"]["change"] == "flag source changed"
    assert changes["A4"]["previous_flag_source"] == "Rule" and changes["A4"]["flag_source"] == "Both"
    assert changes["A1"]["top_features"] == ["collusion_score", "submission_frequency"]
    assert {"anomaly_score", "threshold", "reasons", "model_version"} <= set(changes["A1"])


def test_first_run_records_every_flagged_agent() -> None:
    changes = flag_changes({}, scores([("A1", "ML"), ("A2", "None"), ("A3", "Rule")]))
    assert [c["agent_id"] for c in changes] == ["A1", "A3"]


def entries_for_run(run_id):
    db_session = get_session()
    try:
        found = db_session.query(AdminActionLog).filter(AdminActionLog.category == "ai_decision").all()
        return [e for e in found if json.loads(e.details).get("run_id") == run_id]
    finally:
        db_session.close()


def test_detection_run_writes_system_entries_matching_the_score_changes(database) -> None:
    result = run_detection_cycle(trigger="test")
    found = entries_for_run(result["run_id"])
    runs = [e for e in found if e.action == "ai_detection_run"]
    assert len(runs) == 1
    run = runs[0]
    details = json.loads(run.details)
    assert run.admin_id == SYSTEM and run.actor_type == "system"
    assert details["status"] == "succeeded" and details["trigger"] == "test" and details["model_version"] == "lof_v3_4f"
    assert details["agents_scored"] == 1000 and details["flagged_count"] == result["flagged"]
    assert abs(details["threshold"] - 1.4447993633890617) < 1e-12

    with engine.connect() as conn:
        previous = conn.execute(text(
            "SELECT run_id FROM detection_runs WHERE status = 'succeeded' AND run_id <> :r "
            "ORDER BY finished_at DESC LIMIT 1"), {"r": result["run_id"]}).scalar()
        expected = conn.execute(text(
            "SELECT count(*) FROM agent_scores c LEFT JOIN agent_scores p ON p.agent_id = c.agent_id AND p.run_id = :p "
            "WHERE c.run_id = :r AND ((p.agent_id IS NULL AND c.flag_source <> 'None') "
            "OR (p.agent_id IS NOT NULL AND p.flag_source <> c.flag_source))"),
            {"p": previous, "r": result["run_id"]}).scalar()
    flags = [e for e in found if e.action == "ai_flag"]
    assert len(flags) == expected == details["flag_changes"]
    assert all(e.admin_id == SYSTEM and e.actor_type == "system" and e.target_agent_id for e in flags)


def test_failed_run_is_recorded_as_an_ai_decision(database, monkeypatch) -> None:
    def broken():
        raise RuntimeError("bundle unavailable (test)")

    monkeypatch.setattr(ml_bridge, "load_frozen_bundle", broken)
    with pytest.raises(RuntimeError):
        run_detection_cycle(trigger="test-failure")
    db_session = get_session()
    try:
        entry = (db_session.query(AdminActionLog).filter(AdminActionLog.action == "ai_detection_run")
                 .order_by(AdminActionLog.timestamp.desc()).first())
    finally:
        db_session.close()
    details = json.loads(entry.details)
    assert details["status"] == "failed" and details["trigger"] == "test-failure"
    assert details["error"] == "RuntimeError: bundle unavailable (test)" and entry.admin_id == SYSTEM
