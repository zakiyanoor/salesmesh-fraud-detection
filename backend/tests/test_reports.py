"""Admin report downloads (issue #18): access, content, masking, audit of every download, CSV injection."""

import csv
import hashlib
import io
import re

import pytest
from sqlalchemy import text

from src import audit, reports
from src.db import AgentIdentity, engine, get_session
from tests.helpers import ADMIN, ANALYST, COMPLIANCE, login

URLS = ["/api/reports/flagged-agents.csv", "/api/reports/audit-log.csv", "/api/reports/detection-summary.pdf"]
DATED = re.compile(r'attachment; filename="[a-z-]+_\d{4}-\d{2}-\d{2}\.(csv|pdf)"')


def rows_of(response):
    return list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))


def latest_run_id():
    with engine.connect() as conn:
        return conn.execute(text("SELECT run_id FROM detection_runs WHERE status = 'succeeded' "
                                 "ORDER BY finished_at DESC LIMIT 1")).scalar()


def last_download(client, report):
    login(client, ADMIN)
    found = client.get("/api/audit-log?category=report&limit=50").get_json()["entries"]
    return next(e for e in found if e["details"]["report"] == report)


@pytest.mark.parametrize("url", URLS)
def test_reports_are_admin_only(client, url) -> None:
    assert client.get(url).status_code == 401
    for account in (ANALYST, COMPLIANCE):
        login(client, account)
        assert client.get(url).status_code == 403
        client.post("/api/logout")
    login(client, ADMIN)
    response = client.get(url)
    assert response.status_code == 200
    assert DATED.fullmatch(response.headers["Content-Disposition"])
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("url", URLS)
def test_every_download_is_audited_with_hash_and_row_count(client, url) -> None:
    login(client, ADMIN)
    response = client.get(url)
    entry = last_download(client, url.rsplit("/", 1)[1])
    assert entry["action"] == "report_download" and entry["category"] == "report" and entry["actor"] == ADMIN["admin_id"]
    assert entry["details"]["sha256"] == hashlib.sha256(response.data).hexdigest()
    assert entry["details"]["bytes"] == len(response.data)
    if url.endswith(".csv"):
        assert entry["details"]["row_count"] == len(rows_of(response))


def test_flagged_agents_csv_content_and_masking(client) -> None:
    login(client, ADMIN)
    response = client.get("/api/reports/flagged-agents.csv")
    assert response.headers["Content-Type"] == "text/csv; charset=utf-8"
    rows = rows_of(response)
    assert list(rows[0]) == reports.FLAGGED_COLUMNS
    with engine.connect() as conn:
        expected = conn.execute(text("SELECT count(*) FROM agent_scores WHERE run_id = :r AND flag_source <> 'None'"),
                                {"r": latest_run_id()}).scalar()
    assert len(rows) == expected
    assert {r["flag_source"] for r in rows} <= {"ML", "Rule", "Both"}
    assert all(r["risk_band"] == ("high" if r["flag_source"] in ("ML", "Both") else "review") for r in rows)
    scores = [float(r["anomaly_score"]) for r in rows]
    assert scores == sorted(scores, reverse=True)
    for row in rows:
        assert re.fullmatch(r"\*+\d{3}", row["masked_phone"]) and re.fullmatch(r"\*+\d{3}", row["masked_national_id"])
        assert re.fullmatch(r"[A-Z]\**( [A-Z]\**)+", row["masked_name"])
    db_session = get_session()
    try:
        identities = db_session.query(AgentIdentity).all()
    finally:
        db_session.close()
    body = response.get_data(as_text=True)
    for identity in identities:
        assert identity.phone_number not in body and identity.national_id_number not in body
        assert identity.full_name not in body


def test_audit_log_csv_filters_and_cap(client, monkeypatch) -> None:
    login(client, ADMIN)
    rows = rows_of(client.get("/api/reports/audit-log.csv?category=authentication"))
    assert rows and {r["Category"] for r in rows} == {"authentication"}
    assert list(rows[0]) == reports.AUDIT_COLUMNS == [
        "Time (UTC)", "Actor", "Actor type", "Category", "Action", "Agent", "Request IP (masked)", "Result", "Details"]
    assert all(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?Z", r["Time (UTC)"]) for r in rows)
    results = {r["Action"]: r["Result"] for r in rows}
    assert results.get("login", "Success") == "Success" and results.get("login_failure", "Failed") == "Failed"
    assert client.get("/api/reports/audit-log.csv?category=nope").status_code == 400
    entry = last_download(client, "audit-log.csv")
    assert entry["details"]["filters"] == {"category": "authentication"} and entry["details"]["cap"] == 50000
    monkeypatch.setattr(reports, "AUDIT_CSV_CAP", 5)
    capped = client.get("/api/reports/audit-log.csv")
    assert len(rows_of(capped)) == 5 and capped.headers.get("X-Row-Limit-Reached") == "true"
    monkeypatch.setattr(reports, "AUDIT_CSV_CAP", 50000)
    assert client.get("/api/reports/audit-log.csv?category=report").headers.get("X-Row-Limit-Reached") is None


def test_audit_result_column_only_where_the_entry_says() -> None:
    assert audit.result_of("login", None) == "Success" and audit.result_of("access_denied", {}) == "Failed"
    assert audit.result_of("ai_detection_run", {"status": "failed"}) == "Failed"
    assert audit.result_of("ai_detection_run", {"status": "succeeded"}) == "Success"
    assert audit.result_of("ai_flag", {"change": "newly flagged"}) == ""


def test_detection_summary_pdf_content(client) -> None:
    login(client, ADMIN)
    response = client.get("/api/reports/detection-summary.pdf")
    assert response.mimetype == "application/pdf" and response.data.startswith(b"%PDF")
    pages = response.data.count(b"/Type /Page\n")
    assert 1 <= pages <= 2
    body = response.data.decode("latin-1")
    for expected in ["Run status", "lof_v3_4f", "1.444799", "Agents by flag_source and risk_band",
                     "Top 10 regions by flagged rate", "Generated", ADMIN["admin_id"], latest_run_id()]:
        assert expected in body, expected
    db_session = get_session()
    try:
        load_id, data_hash = reports.data_fingerprint(db_session)
    finally:
        db_session.close()
    assert load_id in body and data_hash in body
    entry = last_download(client, "detection-summary.pdf")
    assert entry["details"]["data_hash"] == data_hash and entry["details"]["run_id"] == latest_run_id()


@pytest.mark.parametrize("value, expected", [
    ("=1+1", "'=1+1"), ("+SUM(A1)", "'+SUM(A1)"), ("-2+3", "'-2+3"), ("@cmd", "'@cmd"), ("\tx", "'\tx"),
    ("\rx", "'\rx"), ("A1", "A1"), ("", ""), (-2.5, -2.5), (7, 7),
])
def test_csv_safe(value, expected) -> None:
    assert reports.csv_safe(value) == expected


def test_csv_injection_is_neutralised_end_to_end(client) -> None:
    hostile = '=HYPERLINK("http://example.invalid","click")'
    audit.record_now(hostile, "test_entry", "admin")
    login(client, ADMIN)
    response = client.get("/api/reports/audit-log.csv", query_string={"actor": hostile})
    rows = rows_of(response)
    assert rows and all(r["Actor"] == "'" + hostile for r in rows)
    assert all(not v.startswith(reports.FORMULA_PREFIXES) for r in rows for v in r.values() if v)


def test_mask_name() -> None:
    assert reports.mask_name("Agnes Omondi") == "A**** O*****"
    assert reports.mask_name(None) is None
