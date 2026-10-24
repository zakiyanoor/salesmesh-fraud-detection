"""Threat intelligence views computed once per detection run and stored in threat_views (issue #28)."""

import json

import pytest
from sqlalchemy import inspect

from src import threat_intel
from src.db import AgentScore, DetectionRun, ThreatView, engine, get_session, migrate_schema
from src.scoring_service import run_detection_cycle


def latest_succeeded_run_id():
    db_session = get_session()
    try:
        return threat_intel.latest_run(db_session).run_id
    finally:
        db_session.close()


def test_threat_views_table_has_the_expected_columns_and_key(database) -> None:
    migrate_schema()  # idempotent: a second run on an existing table changes nothing
    table = inspect(engine)
    columns = {c["name"]: c for c in table.get_columns("threat_views")}
    assert set(columns) == {"run_id", "view", "view_version", "payload", "created_at"}
    assert not any(c["nullable"] for c in columns.values())
    assert table.get_pk_constraint("threat_views")["constrained_columns"] == ["run_id", "view"]
    assert [fk["referred_table"] for fk in table.get_foreign_keys("threat_views")] == ["detection_runs"]


def test_run_stores_every_view_at_the_current_version_equal_to_computing_it(database) -> None:
    db_session = get_session()
    try:
        run = db_session.get(DetectionRun, database["run_id"])
        rows = {r.view: r for r in db_session.query(ThreatView).filter(ThreatView.run_id == run.run_id)}
        assert set(rows) == set(threat_intel.VIEWS) == set(threat_intel.VIEW_VERSIONS)
        for name, compute in threat_intel.VIEWS.items():
            assert rows[name].view_version == threat_intel.VIEW_VERSIONS[name]
            assert json.loads(rows[name].payload) == compute(db_session, run), name
    finally:
        db_session.close()


def test_a_view_that_fails_fails_the_run_and_stores_nothing(database, monkeypatch) -> None:
    def broken(db_session, run):
        raise RuntimeError("view failed")

    before = latest_succeeded_run_id()
    monkeypatch.setitem(threat_intel.VIEWS, "timeline", broken)
    with pytest.raises(RuntimeError, match="view failed"):
        run_detection_cycle(trigger="test-view-failure")
    db_session = get_session()
    try:
        failed = db_session.query(DetectionRun).order_by(DetectionRun.started_at.desc()).first()
        assert failed.trigger == "test-view-failure" and failed.status == "failed"
        assert db_session.query(ThreatView).filter(ThreatView.run_id == failed.run_id).count() == 0
        assert db_session.query(AgentScore).filter(AgentScore.run_id == failed.run_id).count() == 0
    finally:
        db_session.close()
    assert latest_succeeded_run_id() == before
