"""Deployment (issue #20): proxy trust, the database URL, migrate options and the first admin command."""

import json
import logging
import uuid
from datetime import datetime

import pytest
from sqlalchemy.engine import make_url
from werkzeug.security import check_password_hash

from src import manage_accounts, migrate as migrate_module
from src.auth import ROLE_ADMIN, ROLE_FRAUD_ANALYST, Administrator
from src.db import AdminActionLog, database_url, get_session
from tests.helpers import ANALYST

CLIENT_ADDRESS, OTHER_ADDRESS = "203.0.113.7", "198.51.100.9"
WRONG = {"username": ANALYST["username"], "password": "wrong-password"}


@pytest.fixture
def proxy(client):
    """Sets whether the app trusts X-Forwarded-For, as TRUST_PROXY does at start, and restores it afterwards."""
    from src.api import app, behind_proxy, limiter

    original = app.wsgi_app

    def apply(trusted):
        app.wsgi_app = behind_proxy(original) if trusted else original

    limiter.reset()
    try:
        yield apply
    finally:
        app.wsgi_app = original


def failed_login(client, address):
    return client.post("/api/login", json=WRONG, headers={"X-Forwarded-For": address}).status_code


def newest_login_failure_ip(since):
    db_session = get_session()
    try:
        entry = (db_session.query(AdminActionLog)
                 .filter(AdminActionLog.action == "login_failure", AdminActionLog.timestamp >= since)
                 .order_by(AdminActionLog.timestamp.desc()).first())
        return entry.request_ip
    finally:
        db_session.close()


def test_trusted_proxy_gives_the_forwarded_address_to_the_audit_log(client, proxy) -> None:
    proxy(True)
    started = datetime.utcnow()
    assert failed_login(client, CLIENT_ADDRESS) == 401
    assert newest_login_failure_ip(started) == "203.0.*.*"


def test_untrusted_proxy_header_is_ignored_by_the_audit_log(client, proxy) -> None:
    proxy(False)
    started = datetime.utcnow()
    assert failed_login(client, CLIENT_ADDRESS) == 401
    assert newest_login_failure_ip(started) == "127.0.*.*"


def test_trusted_proxy_gives_the_forwarded_address_to_the_limiter(client, proxy) -> None:
    from src.api import limiter

    proxy(True)
    limiter.enabled = True
    assert [failed_login(client, CLIENT_ADDRESS) for _ in range(6)] == [401] * 5 + [429]
    assert failed_login(client, OTHER_ADDRESS) == 401


def test_untrusted_proxy_header_is_ignored_by_the_limiter(client, proxy) -> None:
    from src.api import limiter

    proxy(False)
    limiter.enabled = True
    assert [failed_login(client, CLIENT_ADDRESS) for _ in range(5)] == [401] * 5
    assert failed_login(client, OTHER_ADDRESS) == 429


# --- Database URL and migrate ---

@pytest.mark.parametrize("password", ["p@ss:w/rd#?%&=+ ", "simple", "üñï€ode"])
def test_database_url_keeps_any_password(password) -> None:
    url = database_url("salesmesh", user="app", password=password, host="db.example", port="5432")
    assert url.password == password and url.host == "db.example" and url.database == "salesmesh"
    assert make_url(url.render_as_string(hide_password=False)).password == password


def test_database_url_applies_sslmode_only_when_set() -> None:
    assert database_url("salesmesh", sslmode="require").query == {"sslmode": "require"}
    assert database_url("salesmesh", sslmode="").query == {}


def test_migrate_can_skip_creating_the_database(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(migrate_module, "create_database_if_missing", lambda name: calls.append(name))
    monkeypatch.setattr(migrate_module, "create_all_tables", lambda: None)
    assert migrate_module.migrate(create_database=False) is False and calls == []
    migrate_module.migrate(create_database=True)
    assert calls == [migrate_module.DB_NAME]


# --- First admin ---

FIRST_PASSWORD = "FirstAdminPassword2026!"


@pytest.fixture
def no_admins(database):
    """No account with the admin role, as on a new server; the roles are restored and new accounts removed."""
    db_session = get_session()
    try:
        admins = [a.admin_id for a in db_session.query(Administrator).filter(Administrator.role == ROLE_ADMIN)]
        db_session.query(Administrator).filter(Administrator.admin_id.in_(admins)).update(
            {Administrator.role: ROLE_FRAUD_ANALYST}, synchronize_session=False)
        db_session.commit()
        existing = {a.admin_id for a in db_session.query(Administrator.admin_id)}
    finally:
        db_session.close()
    yield
    db_session = get_session()
    try:
        db_session.query(Administrator).filter(Administrator.admin_id.not_in(existing)).delete(
            synchronize_session=False)
        db_session.query(Administrator).filter(Administrator.admin_id.in_(admins)).update(
            {Administrator.role: ROLE_ADMIN}, synchronize_session=False)
        db_session.commit()
    finally:
        db_session.close()


def create_admin(username, monkeypatch, password=FIRST_PASSWORD, admin_id=None):
    monkeypatch.setenv("FIRST_ADMIN_PASSWORD", password)
    manage_accounts.main(["create-admin", username, "--password-env", "FIRST_ADMIN_PASSWORD",
                          *(["--admin-id", admin_id] if admin_id else [])])


def test_create_admin_works_once_and_is_audited_without_the_password(no_admins, monkeypatch, capsys, caplog) -> None:
    caplog.set_level(logging.DEBUG)
    admin_id, username = f"ADM_FIRST_{uuid.uuid4().hex[:6]}", f"first_{uuid.uuid4().hex[:6]}"
    create_admin(username, monkeypatch, admin_id=admin_id)
    db_session = get_session()
    try:
        account = db_session.get(Administrator, admin_id)
        entries = [e for e in db_session.query(AdminActionLog).filter(AdminActionLog.action == "account_created")
                   if json.loads(e.details)["target_admin_id"] == admin_id]
    finally:
        db_session.close()
    assert account.username == username and account.role == ROLE_ADMIN and account.is_active
    assert check_password_hash(account.password_hash, FIRST_PASSWORD)
    (entry,) = entries
    assert entry.category == "admin" and entry.admin_id.startswith("local:")
    assert json.loads(entry.details) == {"target_admin_id": admin_id, "target_username": username,
                                         "role": ROLE_ADMIN, "channel": "first admin"}

    with pytest.raises(SystemExit, match="an admin account already exists"):
        create_admin(f"second_{uuid.uuid4().hex[:6]}", monkeypatch)
    output = capsys.readouterr()
    assert FIRST_PASSWORD not in output.out + output.err + caplog.text + entry.details


def test_create_admin_refuses_when_an_admin_exists(database, monkeypatch) -> None:
    with pytest.raises(SystemExit, match="an admin account already exists"):
        create_admin(f"extra_{uuid.uuid4().hex[:6]}", monkeypatch)


def test_create_admin_checks_the_password_and_the_username(no_admins, monkeypatch, capsys) -> None:
    with pytest.raises(SystemExit, match="at least 12 characters"):
        create_admin("first_short", monkeypatch, password="short")
    with pytest.raises(SystemExit, match="already taken"):
        create_admin(ANALYST["username"], monkeypatch)
    monkeypatch.delenv("FIRST_ADMIN_PASSWORD")
    with pytest.raises(SystemExit, match="FIRST_ADMIN_PASSWORD is not set"):
        manage_accounts.main(["create-admin", "first_unset", "--password-env", "FIRST_ADMIN_PASSWORD"])
    assert "short" not in capsys.readouterr().out
