"""Threat intelligence views computed once per detection run and stored in threat_views (issue #28)."""

import json
from datetime import datetime

import pytest
from sqlalchemy import inspect

from src import scoring_service, threat_intel
from src.db import (
    AgentScore, DetectionRun, FeatureVector, FraudFlag, ThreatView, engine, get_session, migrate_schema,
)
from src.scoring_service import run_detection_cycle
from tests.helpers import ANALYST, COMPLIANCE, login


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


# --- Serving (GET /api/threat-intelligence/<view>) ---

def served(client):
    """{view: raw response bytes} for every view, as the analyst."""
    login(client, ANALYST)
    out = {}
    for name in threat_intel.VIEWS:
        response = client.get(f"/api/threat-intelligence/{name}")
        assert response.status_code == 200, (name, response.get_json())
        out[name] = response.data
    client.post("/api/logout")
    return out


def computed(name, run_id=None):
    """The bytes the API returned before issue #28: the view computed now, serialised the same way."""
    from src.api import app

    db_session = get_session()
    try:
        run = db_session.get(DetectionRun, run_id) if run_id else threat_intel.latest_run(db_session)
        with app.app_context():
            return app.json.response(threat_intel.VIEWS[name](db_session, run)).get_data()
    finally:
        db_session.close()


def without_run(body):
    return {k: v for k, v in json.loads(body).items() if k != "run"}


class StoredRow:
    """Changes one stored view of the latest run for a test, and puts it back afterwards."""

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.db_session = get_session()
        run_id = threat_intel.latest_run(self.db_session).run_id
        self.row = self.db_session.get(ThreatView, (run_id, self.name))
        self.saved = (self.row.view_version, self.row.payload)
        return self

    def set(self, version, payload):
        self.row.view_version, self.row.payload = version, json.dumps(payload)
        self.db_session.commit()

    def __exit__(self, *exc):
        self.row.view_version, self.row.payload = self.saved
        self.db_session.commit()
        self.db_session.close()


def test_api_returns_the_same_bytes_as_computing_the_view(client) -> None:
    for name, body in served(client).items():
        assert body == computed(name), name


def test_api_serves_the_stored_copy(client) -> None:
    with StoredRow("summary") as stored:
        stored.set(threat_intel.VIEW_VERSIONS["summary"], {"marker": "stored copy"})
        login(client, ANALYST)
        assert client.get("/api/threat-intelligence/summary").get_json() == {"marker": "stored copy"}


def test_a_stored_copy_of_another_version_is_computed_again_with_the_current_code(client) -> None:
    name = "ring-candidates"
    with StoredRow(name) as stored:
        stored.set(threat_intel.VIEW_VERSIONS[name] - 1, {"marker": "old version"})
        login(client, ANALYST)
        response = client.get(f"/api/threat-intelligence/{name}")
        assert response.data == computed(name)
        assert "marker" not in response.get_json()
        assert response.get_json()["candidates_total"] == 14


def test_a_run_without_stored_views_is_computed_with_the_current_code(client) -> None:
    db_session = get_session()
    run_id = threat_intel.latest_run(db_session).run_id
    rows = db_session.query(ThreatView).filter(ThreatView.run_id == run_id)
    saved = [(r.view, r.view_version, r.payload, r.created_at) for r in rows]
    rows.delete()
    db_session.commit()
    try:
        assert served(client) == {name: computed(name) for name in threat_intel.VIEWS}
    finally:
        db_session.add_all(ThreatView(run_id=run_id, view=v, view_version=n, payload=p, created_at=c)
                           for v, n, p, c in saved)
        db_session.commit()
        db_session.close()


def test_views_follow_each_new_run_and_never_a_failed_or_running_one(client, monkeypatch) -> None:
    run_a, before = latest_succeeded_run_id(), served(client)
    real = scoring_service.score_frame

    def one_flag_fewer(*args, **kwargs):
        scores, features, evidence = real(*args, **kwargs)
        top = scores.loc[scores["flagged"], "anomaly_score"].idxmax()
        scores.loc[top, "flagged"] = False
        scores.loc[top, "flag_source"] = "Rule" if scores.loc[top, "rule_flagged"] else "None"
        return scores, features, evidence

    monkeypatch.setattr(scoring_service, "score_frame", one_flag_fewer)
    run_b = run_detection_cycle(trigger="test-views-b")["run_id"]
    monkeypatch.undo()
    after_b = served(client)
    for name, body in after_b.items():
        assert json.loads(body)["run"]["run_id"] == run_b, name
        assert body == computed(name, run_b), name
    for name in ("summary", "ring-candidates"):
        assert json.loads(after_b[name])["flagged" if name == "summary" else "flagged_agents"] ==             json.loads(before[name])["flagged" if name == "summary" else "flagged_agents"] - 1

    db_session = get_session()
    now = datetime.utcnow()
    db_session.add_all([DetectionRun(run_id="RUNTESTFAILED", trigger="test", status="failed", started_at=now,
                                     finished_at=now, error="RuntimeError: test"),
                        DetectionRun(run_id="RUNTESTRUNNING", trigger="test", status="running", started_at=now)])
    db_session.commit()
    try:
        assert served(client) == after_b
    finally:
        db_session.query(DetectionRun).filter(DetectionRun.run_id.in_(["RUNTESTFAILED", "RUNTESTRUNNING"])).delete()
        db_session.commit()
        db_session.close()

    # A normal run on the same data gives the views of run A again, under the new run id.
    run_c = run_detection_cycle(trigger="test-views-c")["run_id"]
    after_c = served(client)
    assert run_c not in (run_a, run_b)
    for name, body in after_c.items():
        assert json.loads(body)["run"]["run_id"] == run_c
        assert without_run(body) == without_run(before[name]), name


def test_a_review_decision_changes_no_view(client) -> None:
    db_session = get_session()
    try:
        flag_id = (db_session.query(FraudFlag.flag_id).join(FeatureVector, FraudFlag.vector_id == FeatureVector.vector_id)
                   .filter(FraudFlag.flag_status == "flagged").first()[0])
        stored_rows = db_session.query(ThreatView).count()
    finally:
        db_session.close()
    before = served(client)

    login(client, ANALYST)
    proposed = client.post("/api/review-decisions", json={"flag_id": flag_id, "decision_outcome": "confirmed_fraud",
                                                           "notes": "Views must not change."})
    assert proposed.status_code == 201, proposed.get_json()
    client.post("/api/logout")
    login(client, COMPLIANCE)
    confirmed = client.post(f"/api/review-decisions/{proposed.get_json()['decision_id']}/confirm")
    assert confirmed.status_code == 200, confirmed.get_json()
    client.post("/api/logout")

    assert served(client) == before
    db_session = get_session()
    try:
        assert db_session.query(ThreatView).count() == stored_rows
    finally:
        db_session.close()
