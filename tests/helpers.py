"""Shared test accounts and helpers for the API integration tests."""

# Demo/test accounts created by `python -m src.auth`.
ANALYST = {"username": "analyst_01", "password": "RiverbankTrader42", "admin_id": "ADM_ANALYST_01"}
COMPLIANCE = {"username": "compliance_01", "password": "MarigoldStation17", "admin_id": "ADM_COMPLIANCE_01"}
TEST_ADMIN_IDS = (ANALYST["admin_id"], COMPLIANCE["admin_id"])


def login(client, account) -> None:
    response = client.post(
        "/api/login", json={"username": account["username"], "password": account["password"]}
    )
    assert response.status_code == 200, response.get_json()
