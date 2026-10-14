"""GET /api/me (issue #5): the current session's username and role, nothing else."""

import uuid
from datetime import datetime, timedelta

import pytest

from src import audit
from src.auth import Administrator, create_admin_user
from src.db import get_session
from tests.helpers import ADMIN, ALL_ACCOUNTS, ANALYST, COMPLIANCE, login

PASSWORD = "ThrowawayPassphrase77"


@pytest.fixture
def throwaway(database):
    admin_id = f"ADM_TMP_{uuid.uuid4().hex[:8]}"
    account = {"admin_id": admin_id, "username": admin_id.lower(), "password": PASSWORD}
    create_admin_user(admin_id, account["username"], PASSWORD, "fraud_analyst")
    yield account
    db_session = get_session()
    try:
        db_session.query(Administrator).filter(Administrator.admin_id == admin_id).delete()
        db_session.commit()
    finally:
        db_session.close()


def audit_entries(client, **filters):
    query = "&".join(f"{k}={v}" for k, v in {**filters, "limit": 1000}.items())
    return client.get(f"/api/audit-log?{query}").get_json()["entries"]


def test_me_requires_a_session(client) -> None:
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication required"}


@pytest.mark.parametrize("account", ALL_ACCOUNTS, ids=["analyst", "compliance", "admin"])
def test_me_returns_only_username_and_role(client, account) -> None:
    login(client, account)
    response = client.get("/api/me")
    assert response.status_code == 200
    expected_role = {ANALYST["username"]: "fraud_analyst", COMPLIANCE["username"]: "compliance_officer",
                     ADMIN["username"]: "admin"}[account["username"]]
    assert response.get_json() == {"username": account["username"], "role": expected_role}
    text = response.get_data(as_text=True).lower()
    assert "password" not in text and "pbkdf2" not in text and "scrypt" not in text
    assert account["admin_id"].lower() not in text


def test_me_is_401_after_logout(client) -> None:
    login(client, ANALYST)
    client.post("/api/logout")
    assert client.get("/api/me").status_code == 401


def test_me_follows_role_change_and_deactivation(client, throwaway) -> None:
    other = client.application.test_client()
    login(other, throwaway)
    assert other.get("/api/me").get_json()["role"] == "fraud_analyst"

    login(client, ADMIN)
    assert client.patch(f"/api/admin/accounts/{throwaway['admin_id']}/role",
                        json={"role": "compliance_officer"}).status_code == 200
    assert other.get("/api/me").get_json() == {"username": throwaway["username"], "role": "compliance_officer"}

    assert client.post(f"/api/admin/accounts/{throwaway['admin_id']}/deactivate").status_code == 200
    response = other.get("/api/me")
    assert response.status_code == 401 and response.get_json()["error"] == "Account is deactivated"


def test_me_is_not_audited_like_other_reads(client) -> None:
    login(client, COMPLIANCE)
    started = datetime.utcnow().isoformat()
    assert client.get("/api/me").status_code == 200
    assert client.get("/api/flagged-agents").status_code == 200
    assert audit_entries(client, actor=COMPLIANCE["admin_id"], date_from=started) == []


def test_me_401_is_recorded_as_access_denied_like_other_routes(client) -> None:
    started = (datetime.utcnow() - timedelta(seconds=1)).isoformat()
    assert client.get("/api/me").status_code == 401
    login(client, COMPLIANCE)
    denied = audit_entries(client, category="authorization", actor=audit.ANONYMOUS, date_from=started)
    entry = next(e for e in denied if e["details"]["route"] == "/api/me")
    assert entry["action"] == "access_denied" and entry["details"]["status"] == 401
