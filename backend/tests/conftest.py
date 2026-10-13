import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

# Tests run against their own database, never the development one. Set before
# any src module creates its engine.
os.environ.setdefault("DB_NAME", "salesmesh_fraud_detection_test")
if not os.environ["DB_NAME"].endswith("_test"):
    raise pytest.UsageError(f"tests must use a *_test database, not {os.environ['DB_NAME']!r}")

# The synthetic data generator and feature code live in ml/ (repo root). The app
# imports them through src.ml_bridge; some tests also use them directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ml"))

from tests.helpers import ADMIN, ANALYST, COMPLIANCE, TEST_ADMIN_IDS  # noqa: E402

TEST_ROLES = {ANALYST["admin_id"]: "fraud_analyst", COMPLIANCE["admin_id"]: "compliance_officer",
              ADMIN["admin_id"]: "admin"}


def reset_test_accounts() -> None:
    """The three test accounts back to their roles and active, whatever an interrupted test left."""
    from src.auth import Administrator
    from src.db import get_session

    db_session = get_session()
    try:
        for admin in db_session.query(Administrator).filter(Administrator.admin_id.in_(TEST_ROLES)):
            admin.role, admin.is_active = TEST_ROLES[admin.admin_id], True
        db_session.commit()
    finally:
        db_session.close()


@pytest.fixture(scope="session")
def database():
    """
    The test database, migrated, loaded with the five v3 files (a no-op when the
    same files are already loaded), with the test accounts, scored once per session.
    Returns the detection run summary.
    """
    from src.auth import ROLE_ADMIN, ROLE_COMPLIANCE_OFFICER, ROLE_FRAUD_ANALYST, create_admin_user
    from src.load_data import load_all
    from src.migrate import migrate
    from src.scoring_service import run_detection_cycle

    migrate()
    load_all()
    create_admin_user(ANALYST["admin_id"], ANALYST["username"], ANALYST["password"], ROLE_FRAUD_ANALYST)
    create_admin_user(COMPLIANCE["admin_id"], COMPLIANCE["username"], COMPLIANCE["password"], ROLE_COMPLIANCE_OFFICER)
    create_admin_user(ADMIN["admin_id"], ADMIN["username"], ADMIN["password"], ROLE_ADMIN)
    reset_test_accounts()
    return run_detection_cycle(trigger="test-session")


@pytest.fixture(scope="session")
def known_agent_id(database):
    """An agent flagged by the model in the session's detection run (has records, features and a flag)."""
    from src.db import AgentScore, get_session

    db_session = get_session()
    try:
        row = (db_session.query(AgentScore.agent_id)
               .filter(AgentScore.run_id == database["run_id"], AgentScore.flagged.is_(True))
               .order_by(AgentScore.anomaly_score.desc()).first())
        assert row is not None, "the session run flagged no agent"
        return row[0]
    finally:
        db_session.close()


def _delete_rows_created_since(started) -> None:
    """
    Removes review decisions the test accounts created during a test. Audit
    entries stay: the audit log is append only (a database trigger refuses
    deletes), so tests compare entries before and after instead.
    """
    from src.db import ReviewDecision, get_session

    db_session = get_session()
    try:
        db_session.query(ReviewDecision).filter(
            ReviewDecision.reviewer_id.in_(TEST_ADMIN_IDS),
            ReviewDecision.decision_timestamp >= started,
        ).delete(synchronize_session=False)
        db_session.commit()
    finally:
        db_session.close()


@pytest.fixture
def client(database):
    """
    Flask test client for the API integration tests, on the test database.

    Login rate limiting is off (tests log in far more than 5 times a minute;
    test_login_is_rate_limited turns it back on), and rows the test accounts
    write are deleted afterwards.
    """
    from src.api import app, limiter

    started = datetime.utcnow()
    app.config["TESTING"] = True
    limiter.enabled = False
    try:
        with app.test_client() as test_client:
            yield test_client
    finally:
        limiter.enabled = True
        limiter.reset()
        _delete_rows_created_since(started)
