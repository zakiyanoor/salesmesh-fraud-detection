"""Shared test accounts and helpers for the API integration tests."""

import pytest

# Demo/test accounts created by `python -m src.auth` (and by the test session fixture).
ANALYST = {"username": "analyst_01", "password": "RiverbankTrader42", "admin_id": "ADM_ANALYST_01"}
COMPLIANCE = {"username": "compliance_01", "password": "MarigoldStation17", "admin_id": "ADM_COMPLIANCE_01"}
ADMIN = {"username": "admin_01", "password": "LanternHarbour58", "admin_id": "ADM_ADMIN_01"}
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
