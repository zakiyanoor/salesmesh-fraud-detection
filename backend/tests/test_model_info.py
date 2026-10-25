"""GET /api/model-info (issue #28): the figures come from the frozen results files, never retyped."""

import csv
import hashlib
import json
from pathlib import Path

from sqlalchemy import text

from src.db import engine
from tests.helpers import ALL_ACCOUNTS, ANALYST, login

ML = Path(__file__).resolve().parents[2] / "ml"
OPERATING_POINT = ML / "runs" / "20261013-093050_selection_s42" / "operating_point.json"
FINAL = ML / "runs" / "20261013-103859_final_evaluation_s42"


def sql(statement):
    with engine.connect() as conn:
        return conn.execute(text(statement)).all()


def info(client):
    login(client, ANALYST)
    response = client.get("/api/model-info")
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def metrics_row(prefix):
    with open(FINAL / "test_metrics.csv", newline="", encoding="utf-8") as f:
        return next(r for r in csv.DictReader(f) if r["method"].startswith(prefix))


def test_a_request_without_a_session_is_refused_and_logged(client) -> None:
    before = sql("SELECT count(*) FROM admin_action_log WHERE action = 'access_denied'")[0][0]
    assert client.get("/api/model-info").status_code == 401
    rows = sql("SELECT details FROM admin_action_log WHERE action = 'access_denied' ORDER BY timestamp")
    assert len(rows) == before + 1 and json.loads(rows[-1][0])["route"] == "/api/model-info"


def test_every_role_can_read_it(client) -> None:
    for account in ALL_ACCOUNTS:
        login(client, account)
        assert client.get("/api/model-info").status_code == 200
        client.post("/api/logout")


def test_the_cutoff_and_model_equal_the_frozen_operating_point(client) -> None:
    body = info(client)
    point = json.loads(OPERATING_POINT.read_text(encoding="utf-8"))
    assert body["cutoff"] == point["threshold"]
    assert (body["model_version"], body["features"], body["cutoff_rule"], body["cutoff_chosen_on"]) == (
        point["model_version"], point["feature_columns"], point["threshold_rule"], point["chosen_on"])
    freeze = (ML / "results" / "FREEZE.md").read_text(encoding="utf-8")
    assert hashlib.sha256(OPERATING_POINT.read_bytes()).hexdigest() in freeze


def test_the_test_results_equal_the_final_evaluation_files(client) -> None:
    body = info(client)
    summary = json.loads((FINAL / "summary.json").read_text(encoding="utf-8"))
    assert (body["test_agents"], body["test_fraud_agents"]) == (summary["test_agents"], summary["test_fraud"])
    for key, prefix in (("model", "lof_v3_4f"), ("rule", "duplicate_activation_rule"),
                        ("model_or_rule", "SECONDARY: union")):
        row, result = metrics_row(prefix), body["results"][key]
        assert result["method"] == row["method"]
        for metric in ("precision", "recall", "pr_auc", "roc_auc"):
            assert result[metric] == float(row[metric]), (key, metric)
            assert result[f"{metric}_ci"] == [float(row[f"{metric}_ci_low"]), float(row[f"{metric}_ci_high"])]
        for count in ("flagged", "tp", "fp", "fn", "tn"):
            assert result[count] == int(float(row[count])), (key, count)


def test_it_says_where_the_figures_were_measured_and_names_its_sources(client) -> None:
    body = info(client)
    assert "150 held-out test agents" in body["measured_on"] and "not a promise for other data" in body["measured_on"]
    root = ML.parent
    assert all((root / source).is_file() for source in body["sources"]) and len(body["sources"]) == 3
    assert body["detection_interval_minutes"] > 0


def test_reads_are_not_audited(client) -> None:
    login(client, ANALYST)
    before = sql("SELECT count(*) FROM admin_action_log")[0][0]
    client.get("/api/model-info")
    assert sql("SELECT count(*) FROM admin_action_log")[0][0] == before
