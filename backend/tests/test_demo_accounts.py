"""Demo accounts (issue #26): development and test only, passwords from the environment, none in the code."""

from pathlib import Path

import pytest

from src.auth import DEMO_ACCOUNTS, Administrator, seed_demo_accounts
from src.db import get_session

PASSWORDS = {variable: f"Demo-{variable.lower()}-pass" for *_, variable in DEMO_ACCOUNTS}


def demo_usernames():
    db_session = get_session()
    try:
        names = [u for _, u, _, _ in DEMO_ACCOUNTS]
        return {a.username for a in db_session.query(Administrator).filter(Administrator.username.in_(names))}
    finally:
        db_session.close()


@pytest.mark.parametrize("app_env", [None, "production", "staging"])
def test_refused_outside_development_and_test(database, app_env) -> None:
    environ = dict(PASSWORDS) if app_env is None else {**PASSWORDS, "APP_ENV": app_env}
    with pytest.raises(RuntimeError, match="development and test only"):
        seed_demo_accounts(environ)


def test_names_every_missing_password(database) -> None:
    with pytest.raises(RuntimeError, match="DEMO_COMPLIANCE_PASSWORD, DEMO_ADMIN_PASSWORD"):
        seed_demo_accounts({"APP_ENV": "development", "DEMO_ANALYST_PASSWORD": PASSWORDS["DEMO_ANALYST_PASSWORD"]})


def test_rejects_a_weak_password_before_creating_anything(database) -> None:
    with pytest.raises(RuntimeError, match="DEMO_ADMIN_PASSWORD: Password must be at least 12"):
        seed_demo_accounts({"APP_ENV": "test", **PASSWORDS, "DEMO_ADMIN_PASSWORD": "short"})


def test_creates_the_three_accounts_in_test(database) -> None:
    # The session fixture already created them, so this checks the call succeeds and leaves them in place.
    seed_demo_accounts({"APP_ENV": "test", **PASSWORDS})
    assert demo_usernames() == {"analyst_01", "compliance_01", "admin_01"}


def test_no_demo_password_is_written_in_the_code() -> None:
    source = (Path(__file__).resolve().parents[1] / "src" / "auth.py").read_text(encoding="utf-8")
    assert "password=\"" not in source and "password='" not in source
