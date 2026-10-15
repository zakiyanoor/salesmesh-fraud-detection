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


# --- Local recovery: reset-password (issue #19) ---

NEW_PASSWORD = "FreshHarbourLantern93"


def reset_entries(admin_id):
    db_session = get_session()
    try:
        return [e for e in db_session.query(AdminActionLog).filter(AdminActionLog.action == "password_reset")
                if json.loads(e.details or "{}").get("target_admin_id") == admin_id]
    finally:
        db_session.close()


def stored_hash(admin_id):
    return account(admin_id).password_hash


@pytest.mark.parametrize("by", ["admin_id", "username"])
def test_reset_password_sets_a_new_hashed_password(target, monkeypatch, capsys, by) -> None:
    from src.auth import verify_login

    monkeypatch.setenv("RECOVERY_TEST_PASSWORD", NEW_PASSWORD)
    old_hash = stored_hash(target)
    manage_accounts.main(["reset-password", target if by == "admin_id" else target.lower(),
                          "--new-password-env", "RECOVERY_TEST_PASSWORD"])
    output = capsys.readouterr()
    assert f"Password reset for {target.lower()} ({target}, fraud_analyst)" in output.out
    assert verify_login(target.lower(), NEW_PASSWORD)["admin_id"] == target
    assert verify_login(target.lower(), PASSWORD) is None
    new_hash = stored_hash(target)
    assert new_hash != old_hash and new_hash != NEW_PASSWORD
    # Same hashing as account creation (werkzeug's default method).
    assert new_hash.split("$")[0] == old_hash.split("$")[0]
    for text in (output.out, output.err):
        assert NEW_PASSWORD not in text and new_hash not in text and "$" not in text


def test_reset_password_writes_an_audit_entry_without_the_password(target, monkeypatch) -> None:
    monkeypatch.setenv("RECOVERY_TEST_PASSWORD", NEW_PASSWORD)
    manage_accounts.main(["reset-password", target, "--new-password-env", "RECOVERY_TEST_PASSWORD"])
    entries = reset_entries(target)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.category == "admin" and entry.admin_id.startswith("local:")
    assert json.loads(entry.details) == {"target_admin_id": target, "target_username": target.lower(), "channel": "local recovery"}
    row = " ".join(str(getattr(entry, c)) for c in ("admin_id", "action", "details", "target_agent_id", "category"))
    assert NEW_PASSWORD not in row and stored_hash(target) not in row and "password_hash" not in row


def test_reset_password_refuses_an_unknown_account(database, monkeypatch) -> None:
    monkeypatch.setenv("RECOVERY_TEST_PASSWORD", NEW_PASSWORD)
    with pytest.raises(SystemExit, match="Account not found"):
        manage_accounts.main(["reset-password", "NO_SUCH_ACCOUNT", "--new-password-env", "RECOVERY_TEST_PASSWORD"])
    assert reset_entries("NO_SUCH_ACCOUNT") == []


@pytest.mark.parametrize("weak", ["short", "elevenchars"])
def test_reset_password_refuses_a_weak_password(target, monkeypatch, capsys, weak) -> None:
    from src.auth import verify_login

    monkeypatch.setenv("RECOVERY_TEST_PASSWORD", weak)
    old_hash = stored_hash(target)
    with pytest.raises(SystemExit, match="at least 12 characters") as refused:
        manage_accounts.main(["reset-password", target, "--new-password-env", "RECOVERY_TEST_PASSWORD"])
    assert weak not in str(refused.value) and weak not in capsys.readouterr().out
    assert stored_hash(target) == old_hash and verify_login(target.lower(), PASSWORD) is not None
    assert reset_entries(target) == []


def test_reset_password_needs_the_variable_set(target, monkeypatch) -> None:
    monkeypatch.delenv("RECOVERY_TEST_UNSET", raising=False)
    with pytest.raises(SystemExit, match="RECOVERY_TEST_UNSET is not set or is empty"):
        manage_accounts.main(["reset-password", target, "--new-password-env", "RECOVERY_TEST_UNSET"])


def test_reset_password_takes_no_password_argument(target, capsys) -> None:
    with pytest.raises(SystemExit):
        manage_accounts.main(["reset-password", target, "--new-password", NEW_PASSWORD])
    assert NEW_PASSWORD not in capsys.readouterr().out


def test_reset_password_keeps_a_deactivated_account_deactivated(target, monkeypatch, capsys) -> None:
    monkeypatch.setenv("CLI_TEST_PASSWORD", ADMIN["password"])
    manage_accounts.main(["deactivate", target, "--as", ADMIN["username"], "--password-env", "CLI_TEST_PASSWORD"])
    monkeypatch.setenv("RECOVERY_TEST_PASSWORD", NEW_PASSWORD)
    manage_accounts.main(["reset-password", target, "--new-password-env", "RECOVERY_TEST_PASSWORD"])
    assert account(target).is_active is False
    assert "deactivated" in capsys.readouterr().out.splitlines()[-1]


def test_help_says_no_admin_password_is_needed(capsys) -> None:
    with pytest.raises(SystemExit):
        manage_accounts.main(["reset-password", "--help"])
    text = " ".join(capsys.readouterr().out.split())
    assert "direct database access" in text and "does not need an admin password" in text
    assert "never from the command line" in text
