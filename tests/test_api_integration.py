import pytest
from src.api import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_health_check_requires_no_auth(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_flagged_agents_rejects_unauthenticated(client) -> None:
    response = client.get("/api/flagged-agents")
    assert response.status_code == 401


def test_login_with_invalid_credentials_fails(client) -> None:
    response = client.post("/api/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


def test_login_then_access_protected_route(client) -> None:
    login_response = client.post(
        "/api/login", json={"username": "admin", "password": "ChangeMe123!"}
    )
    assert login_response.status_code == 200

    agents_response = client.get("/api/flagged-agents")
    assert agents_response.status_code == 200
    body = agents_response.get_json()
    assert "flagged_agents" in body
    assert isinstance(body["count"], int)


def test_agent_detail_returns_features_for_known_agent(client) -> None:
    client.post("/api/login", json={"username": "admin", "password": "ChangeMe123!"})
    response = client.get("/api/agents/A1104")
    assert response.status_code == 200
    body = response.get_json()
    assert body["agent_id"] == "A1104"
    assert "features" in body


def test_agent_detail_returns_404_for_unknown_agent(client) -> None:
    client.post("/api/login", json={"username": "admin", "password": "ChangeMe123!"})
    response = client.get("/api/agents/NONEXISTENT")
    assert response.status_code == 404


def test_logout_revokes_session(client) -> None:
    client.post("/api/login", json={"username": "admin", "password": "ChangeMe123!"})
    client.post("/api/logout")

    response = client.get("/api/flagged-agents")
    assert response.status_code == 401