from datetime import datetime

import pytest
from tests.helpers import TEST_ADMIN_IDS


def _delete_rows_created_since(started) -> None:
    """
    Removes audit entries and review decisions the test accounts created.

    The integration tests run against the real database, so without this every
    run would leave login/logout audit rows and proposed decisions behind.
    """
    from src.db import get_session, AdminActionLog, ReviewDecision

    db_session = get_session()
    try:
        db_session.query(AdminActionLog).filter(
            AdminActionLog.admin_id.in_(TEST_ADMIN_IDS),
            AdminActionLog.timestamp >= started,
        ).delete(synchronize_session=False)
        db_session.query(ReviewDecision).filter(
            ReviewDecision.reviewer_id.in_(TEST_ADMIN_IDS),
            ReviewDecision.decision_timestamp >= started,
        ).delete(synchronize_session=False)
        db_session.commit()
    finally:
        db_session.close()


@pytest.fixture
def client():
    """
    Flask test client for the API integration tests.

    Login rate limiting is off (tests log in far more than 5 times a minute;
    test_login_is_rate_limited turns it back on), and rows the test accounts
    write are deleted afterwards.
    """
    # Imported here so the unit tests don't need FLASK_SECRET_KEY or a database.
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
