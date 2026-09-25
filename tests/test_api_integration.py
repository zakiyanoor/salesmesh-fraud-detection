import pytest
from src.api import app
from src.db import get_session, FeatureVector


def _latest_period_by_agent() -> dict:
    """Newest analysis_period per agent, read straight from the database."""
    db_session = get_session()
    try:
        latest: dict = {}
        for agent_id, period in db_session.query(FeatureVector.agent_id, FeatureVector.analysis_period):
            if agent_id not in latest or period > latest[agent_id]:
                latest[agent_id] = period
        return latest
    finally:
        db_session.close()


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


def test_all_agents_rejects_unauthenticated(client) -> None:
    response = client.get("/api/all-agents")
    assert response.status_code == 401


def test_all_agents_returns_every_agent_once_with_status(client) -> None:
    client.post("/api/login", json={"username": "admin", "password": "ChangeMe123!"})
    response = client.get("/api/all-agents")
    assert response.status_code == 200
    body = response.get_json()

    agent_ids = [a["agent_id"] for a in body["agents"]]
    assert body["count"] == len(agent_ids)
    assert len(agent_ids) == len(set(agent_ids))
    for agent in body["agents"]:
        assert agent["status"] in ("flagged", "clear")
        for key in ("suspicion_score", "submission_frequency", "time_of_day_dist",
                    "customer_similarity", "collusion_score", "region"):
            assert key in agent


def test_flagged_agents_lists_each_agent_once(client) -> None:
    client.post("/api/login", json={"username": "admin", "password": "ChangeMe123!"})
    body = client.get("/api/flagged-agents").get_json()

    agent_ids = [a["agent_id"] for a in body["flagged_agents"]]
    assert body["count"] == len(agent_ids)
    assert len(agent_ids) == len(set(agent_ids))


def test_flagged_agents_only_reports_latest_analysis_period(client) -> None:
    client.post("/api/login", json={"username": "admin", "password": "ChangeMe123!"})
    latest_period = _latest_period_by_agent()

    for row in client.get("/api/flagged-agents").get_json()["flagged_agents"]:
        assert row["analysis_period"] == latest_period[row["agent_id"]]


def test_flagged_agents_matches_flagged_status_in_all_agents(client) -> None:
    client.post("/api/login", json={"username": "admin", "password": "ChangeMe123!"})
    flagged_ids = {a["agent_id"] for a in client.get("/api/flagged-agents").get_json()["flagged_agents"]}
    all_agents = client.get("/api/all-agents").get_json()["agents"]
    assert flagged_ids == {a["agent_id"] for a in all_agents if a["status"] == "flagged"}


def test_analytics_counts_each_agent_once(client) -> None:
    client.post("/api/login", json={"username": "admin", "password": "ChangeMe123!"})
    all_agents = client.get("/api/all-agents").get_json()["agents"]
    scored = [a for a in all_agents if a["suspicion_score"] is not None]
    flagged = [a for a in scored if a["status"] == "flagged"]

    body = client.get("/api/analytics").get_json()
    assert sum(r["total"] for r in body["region_breakdown"]) == len(scored)
    assert sum(r["flagged"] for r in body["region_breakdown"]) == len(flagged)
    assert sum(b["count"] for b in body["score_distribution"]) == len(scored)


def test_agent_detail_returns_features_for_known_agent(client) -> None:
    client.post("/api/login", json={"username": "admin", "password": "ChangeMe123!"})
    response = client.get("/api/agents/A1104")
    assert response.status_code == 200
    body = response.get_json()
    assert body["agent_id"] == "A1104"
    assert "features" in body


def test_agent_detail_includes_collusion_score(client) -> None:
    client.post("/api/login", json={"username": "admin", "password": "ChangeMe123!"})
    features = client.get("/api/agents/A1104").get_json()["features"]
    assert "collusion_score" in features
    assert 0.0 <= features["collusion_score"] <= 1.0


def test_agent_detail_uses_the_same_latest_vector_as_all_agents(client) -> None:
    client.post("/api/login", json={"username": "admin", "password": "ChangeMe123!"})
    detail = client.get("/api/agents/A1104").get_json()
    listed = next(a for a in client.get("/api/all-agents").get_json()["agents"] if a["agent_id"] == "A1104")

    for key in ("submission_frequency", "time_of_day_dist", "customer_similarity", "collusion_score"):
        assert detail["features"][key] == listed[key]
    assert detail["flag"]["suspicion_score"] == listed["suspicion_score"]


def test_agent_detail_includes_context_separate_from_features(client) -> None:
    client.post("/api/login", json={"username": "admin", "password": "ChangeMe123!"})
    body = client.get("/api/agents/A1104").get_json()

    assert "context" in body
    assert "client_id" not in body["features"]
    assert "category" not in body["features"]

    context = body["context"]
    assert "client_ids" in context and "categories" in context
    assert isinstance(context["client_ids"], list) and isinstance(context["categories"], list)
    assert len(context["client_ids"]) > 0
    assert len(context["categories"]) > 0


def test_agent_detail_context_lists_only_known_clients_and_categories(client) -> None:
    from src.data_generation import CLIENTS, CATEGORIES

    client.post("/api/login", json={"username": "admin", "password": "ChangeMe123!"})
    context = client.get("/api/agents/A1104").get_json()["context"]

    assert set(context["client_ids"]) <= set(CLIENTS)
    assert set(context["categories"]) <= set(CATEGORIES)


def test_agent_detail_returns_404_for_unknown_agent(client) -> None:
    client.post("/api/login", json={"username": "admin", "password": "ChangeMe123!"})
    response = client.get("/api/agents/NONEXISTENT")
    assert response.status_code == 404


def test_logout_revokes_session(client) -> None:
    client.post("/api/login", json={"username": "admin", "password": "ChangeMe123!"})
    client.post("/api/logout")

    response = client.get("/api/flagged-agents")
    assert response.status_code == 401