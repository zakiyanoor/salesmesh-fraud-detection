"""Roles and account administration (issue #18): separation of duties, self-change and last-admin rules."""

import uuid

import pytest

from src import accounts
from src.auth import ROLE_ADMIN, Administrator, create_admin_user
from src.db import get_session
from tests.helpers import ADMIN, ANALYST, COMPLIANCE, login

PASSWORD = "TemporaryAccount77"


@pytest.fixture
def temp_account(database):
    """A throwaway fraud_analyst account, removed afterwards (administrators rows are not audit rows)."""
    created = []

    def make(role="fraud_analyst"):
        admin_id = f"ADM_TMP_{uuid.uuid4().hex[:8]}"
        account = {"admin_id": admin_id, "username": admin_id.lower(), "password": PASSWORD}
        create_admin_user(admin_id, account["username"], PASSWORD, role)
        created.append(admin_id)
        return account

    yield make
    db_session = get_session()
    try:
        db_session.query(Administrator).filter(Administrator.admin_id.in_(created)).delete(synchronize_session=False)
        db_session.commit()
    finally:
        db_session.close()


def audit_for(client, target_admin_id, action):
    login(client, ADMIN)
    found = client.get("/api/audit-log?category=admin&limit=1000").get_json()["entries"]
    return [e for e in found if e["action"] == action and e["details"]["target_admin_id"] == target_admin_id]


@pytest.mark.parametrize("method, url", [
    ("get", "/api/admin/accounts"),
    ("patch", "/api/admin/accounts/ADM_ANALYST_01/role"),
    ("post", "/api/admin/accounts/ADM_ANALYST_01/deactivate"),
    ("post", "/api/admin/accounts/ADM_ANALYST_01/reactivate"),
])
@pytest.mark.parametrize("account", [ANALYST, COMPLIANCE], ids=["analyst", "compliance"])
def test_account_endpoints_are_admin_only(client, account, method, url) -> None:
    assert getattr(client, method)(url, json={"role": "admin"}).status_code == 401
    login(client, account)
    assert getattr(client, method)(url, json={"role": "admin"}).status_code == 403


def test_admin_lists_accounts_without_password_hashes(client) -> None:
    login(client, ADMIN)
    body = client.get("/api/admin/accounts").get_json()
    roles = {a["admin_id"]: a["role"] for a in body["accounts"]}
    assert roles[ADMIN["admin_id"]] == "admin" and roles[ANALYST["admin_id"]] == "fraud_analyst"
    assert all(set(a) == {"admin_id", "username", "role", "is_active"} for a in body["accounts"])
    assert "password" not in str(body).lower()


def test_role_change_is_audited_and_takes_effect_immediately(client, temp_account) -> None:
    account = temp_account()
    other = client.application.test_client()
    login(other, account)
    assert other.get("/api/flagged-agents").status_code == 200

    login(client, ADMIN)
    response = client.patch(f"/api/admin/accounts/{account['admin_id']}/role", json={"role": "compliance_officer"})
    assert response.status_code == 200 and response.get_json()["account"]["role"] == "compliance_officer"
    assert client.patch(f"/api/admin/accounts/{account['admin_id']}/role",
                        json={"role": "compliance_officer"}).get_json()["changed"] is False
    entry = audit_for(client, account["admin_id"], "role_change")
    assert len(entry) == 1 and entry[0]["details"]["old_role"] == "fraud_analyst"
    assert entry[0]["details"]["new_role"] == "compliance_officer" and entry[0]["actor"] == ADMIN["admin_id"]

    # The other session's role is re-read on its next request.
    assert other.post("/api/review-decisions", json={"flag_id": "x", "decision_outcome": "y"}).status_code == 403


def test_deactivated_account_cannot_log_in_or_keep_its_session(client, temp_account) -> None:
    account = temp_account()
    other = client.application.test_client()
    login(other, account)

    login(client, ADMIN)
    assert client.post(f"/api/admin/accounts/{account['admin_id']}/deactivate").status_code == 200
    response = other.get("/api/flagged-agents")
    assert response.status_code == 401 and response.get_json()["error"] == "Account is deactivated"
    denied = client.get(f"/api/audit-log?category=authorization&actor={account['admin_id']}").get_json()["entries"]
    assert denied and denied[0]["details"]["reason"] == "Account is deactivated"

    failed = other.post("/api/login", json={"username": account["username"], "password": PASSWORD})
    assert failed.status_code == 401
    failure = client.get("/api/audit-log?category=authentication&actor=anonymous&limit=20").get_json()["entries"]
    assert any(e["details"]["username"] == account["username"] and e["details"]["reason"] == "account deactivated"
               for e in failure)

    assert client.post(f"/api/admin/accounts/{account['admin_id']}/reactivate").status_code == 200
    login(other, account)
    assert len(audit_for(client, account["admin_id"], "account_deactivated")) == 1
    assert len(audit_for(client, account["admin_id"], "account_reactivated")) == 1


@pytest.mark.parametrize("method, url, body", [
    ("patch", f"/api/admin/accounts/{ADMIN['admin_id']}/role", {"role": "fraud_analyst"}),
    ("post", f"/api/admin/accounts/{ADMIN['admin_id']}/deactivate", None),
])
def test_admin_cannot_change_or_deactivate_own_account(client, method, url, body) -> None:
    login(client, ADMIN)
    response = getattr(client, method)(url, json=body)
    assert response.status_code == 403 and "own account" in response.get_json()["error"]
    me = next(a for a in client.get("/api/admin/accounts").get_json()["accounts"] if a["admin_id"] == ADMIN["admin_id"])
    assert me["role"] == "admin" and me["is_active"] is True


def test_last_active_admin_cannot_be_removed(database, temp_account) -> None:
    """
    Through the API this is only reachable when two admins act at once (each sees
    the other as removable); the check locks the active admin rows to prevent it.
    Here every other admin is made inactive so the target is the last one.
    """
    target = temp_account(role=ROLE_ADMIN)
    db_session = get_session()
    try:
        others = [a for a in db_session.query(Administrator).filter(Administrator.role == ROLE_ADMIN,
                                                                     Administrator.is_active.is_(True))
                  if a.admin_id != target["admin_id"]]
        for a in others:
            a.is_active = False
        db_session.commit()
        try:
            for change in (lambda s: accounts.set_active(s, "ADM_SOMEONE_ELSE", target["admin_id"], False),
                           lambda s: accounts.change_role(s, "ADM_SOMEONE_ELSE", target["admin_id"], "fraud_analyst")):
                check = get_session()
                try:
                    with pytest.raises(accounts.AccountError, match="last active admin") as error:
                        change(check)
                    assert error.value.status == 409
                finally:
                    check.rollback()
                    check.close()
        finally:
            for a in others:
                a.is_active = True
            db_session.commit()
    finally:
        db_session.close()


def test_an_admin_can_demote_another_admin_while_one_remains(client, temp_account) -> None:
    second = temp_account(role=ROLE_ADMIN)
    login(client, ADMIN)
    assert client.patch(f"/api/admin/accounts/{second['admin_id']}/role", json={"role": "fraud_analyst"}).status_code == 200


def test_unknown_account_and_bad_role(client) -> None:
    login(client, ADMIN)
    assert client.post("/api/admin/accounts/NOPE/deactivate").status_code == 404
    assert client.patch(f"/api/admin/accounts/{ANALYST['admin_id']}/role", json={"role": "superuser"}).status_code == 400
    assert client.patch(f"/api/admin/accounts/{ANALYST['admin_id']}/role", json={}).status_code == 400


def test_admin_cannot_propose_or_confirm_review_decisions(client) -> None:
    login(client, ADMIN)
    assert client.post("/api/review-decisions", json={"flag_id": "x", "decision_outcome": "y"}).status_code == 403
    assert client.post("/api/review-decisions/ANY/confirm").status_code == 403


def test_admin_can_view_detection_run_status(client) -> None:
    login(client, ADMIN)
    assert client.get("/api/detection-runs/latest").status_code == 200
