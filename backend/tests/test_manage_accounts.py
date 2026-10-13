"""Command-line account administration (issue #18): same rules as the API, audited."""

import json
import uuid

import pytest

from src import manage_accounts
from src.auth import Administrator, create_admin_user
from src.db import AdminActionLog, get_session
from tests.helpers import ADMIN, ANALYST

PASSWORD = "TemporaryAccount77"


@pytest.fixture
def target(database):
    admin_id = f"ADM_CLI_{uuid.uuid4().hex[:8]}"
    create_admin_user(admin_id, admin_id.lower(), PASSWORD, "fraud_analyst")
    yield admin_id
    db_session = get_session()
    try:
        db_session.query(Administrator).filter(Administrator.admin_id == admin_id).delete()
        db_session.commit()
    finally:
        db_session.close()


def account(admin_id):
    db_session = get_session()
    try:
        return db_session.get(Administrator, admin_id)
    finally:
        db_session.close()


def test_deactivate_and_reactivate_are_audited(target, monkeypatch) -> None:
    monkeypatch.setenv("CLI_TEST_PASSWORD", ADMIN["password"])
    manage_accounts.main(["deactivate", target, "--as", ADMIN["username"], "--password-env", "CLI_TEST_PASSWORD"])
    assert account(target).is_active is False
    manage_accounts.main(["deactivate", target, "--as", ADMIN["username"], "--password-env", "CLI_TEST_PASSWORD"])
    manage_accounts.main(["reactivate", target, "--as", ADMIN["username"], "--password-env", "CLI_TEST_PASSWORD"])
    assert account(target).is_active is True
    db_session = get_session()
    try:
        entries = [e for e in db_session.query(AdminActionLog).filter(AdminActionLog.category == "admin")
                   if json.loads(e.details or "{}").get("target_admin_id") == target]
    finally:
        db_session.close()
    assert sorted(e.action for e in entries) == ["account_deactivated", "account_reactivated"]
    assert all(e.admin_id == ADMIN["admin_id"] and json.loads(e.details)["channel"] == "cli" for e in entries)


def test_refuses_wrong_password_non_admin_and_self(target, monkeypatch) -> None:
    monkeypatch.setenv("CLI_TEST_PASSWORD", "wrong-password")
    with pytest.raises(SystemExit, match="invalid username or password"):
        manage_accounts.main(["deactivate", target, "--as", ADMIN["username"], "--password-env", "CLI_TEST_PASSWORD"])
    monkeypatch.setenv("CLI_TEST_PASSWORD", ANALYST["password"])
    with pytest.raises(SystemExit, match="active admin"):
        manage_accounts.main(["deactivate", target, "--as", ANALYST["username"], "--password-env", "CLI_TEST_PASSWORD"])
    monkeypatch.setenv("CLI_TEST_PASSWORD", ADMIN["password"])
    with pytest.raises(SystemExit, match="own account"):
        manage_accounts.main(["deactivate", ADMIN["admin_id"], "--as", ADMIN["username"], "--password-env", "CLI_TEST_PASSWORD"])
    assert account(target).is_active is True and account(ADMIN["admin_id"]).is_active is True


def test_role_change(target, monkeypatch) -> None:
    monkeypatch.setenv("CLI_TEST_PASSWORD", ADMIN["password"])
    manage_accounts.main(["role", target, "compliance_officer", "--as", ADMIN["username"], "--password-env", "CLI_TEST_PASSWORD"])
    assert account(target).role == "compliance_officer"
