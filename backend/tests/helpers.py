"""Shared test accounts and helpers for the API integration tests."""

import os

import pytest

# Demo/test accounts created by `python -m src.auth` (and by the test session fixture). The passwords
# come only from DEMO_*_PASSWORD (backend/.env locally, generated per run in CI); conftest.py checks them.
ANALYST = {"username": "analyst_01", "password": os.getenv("DEMO_ANALYST_PASSWORD"), "admin_id": "ADM_ANALYST_01"}
COMPLIANCE = {"username": "compliance_01", "password": os.getenv("DEMO_COMPLIANCE_PASSWORD"),
              "admin_id": "ADM_COMPLIANCE_01"}
ADMIN = {"username": "admin_01", "password": os.getenv("DEMO_ADMIN_PASSWORD"), "admin_id": "ADM_ADMIN_01"}
TEST_ADMIN_IDS = (ANALYST["admin_id"], COMPLIANCE["admin_id"], ADMIN["admin_id"])
ALL_ACCOUNTS = (ANALYST, COMPLIANCE, ADMIN)


def login(client, account) -> None:
    response = client.post(
        "/api/login", json={"username": account["username"], "password": account["password"]}
    )
    assert response.status_code == 200, response.get_json()


def recreate_test_database(name):
    """Drops and creates the *_test database, so every session starts empty (the audit log is append only)."""
    if not name.endswith("_test"):
        raise pytest.UsageError(f"refusing to drop {name!r}: only a *_test database may be recreated")
    from sqlalchemy import create_engine, text

    from src.db import DB_HOST, DB_PASSWORD, DB_PORT, DB_USER, engine

    engine.dispose()
    server = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres",
                           isolation_level="AUTOCOMMIT")
    try:
        with server.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        server.dispose()


def reviewable_flag(sources=("ML", "Both"), skip=0):
    """
    (flag_id, agent_id) of an agent whose flag_source in the latest run is one of sources, in the latest
    analysis period, with no review decision on its flag (issue #28). skip picks a later one.
    """
    from sqlalchemy import text

    from src.db import engine

    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT f.flag_id, v.agent_id FROM fraud_flags f JOIN feature_vectors v ON v.vector_id = f.vector_id "
            "JOIN agent_scores s ON s.agent_id = v.agent_id AND s.run_id = (SELECT run_id FROM detection_runs "
            "  WHERE status = 'succeeded' ORDER BY finished_at DESC LIMIT 1) "
            "WHERE s.flag_source = ANY(:sources) "
            "AND v.analysis_period = (SELECT max(analysis_period) FROM feature_vectors w WHERE w.agent_id = v.agent_id) "
            "AND NOT EXISTS (SELECT 1 FROM review_decisions d WHERE d.flag_id = f.flag_id) "
            "ORDER BY s.anomaly_score DESC, f.flag_id OFFSET :skip LIMIT 1"
        ), {"sources": list(sources), "skip": skip}).first()
    assert row is not None, f"no reviewable flag with flag_source in {sources}"
    return tuple(row)
