"""score_percentile (issue #26): each agent's rank within its detection run, beside the raw score."""

from src.risk import score_percentiles
from tests.helpers import ANALYST, login


def test_percentile_is_the_share_of_agents_with_a_lower_score() -> None:
    scores = {"A": 0.9, "B": 1.2, "C": 1.2, "D": 5.0}
    assert score_percentiles(scores) == {"A": 0.0, "B": 25.0, "C": 25.0, "D": 75.0}


def test_percentile_edge_cases() -> None:
    assert score_percentiles({}) == {}
    assert score_percentiles({"A": 3.0}) == {"A": 0.0}
    top = score_percentiles({f"A{i}": float(i) for i in range(1000)})
    assert top["A999"] == 99.9 and top["A0"] == 0.0


def test_agent_scores_carry_a_percentile_that_falls_with_the_score(client) -> None:
    login(client, ANALYST)
    scores = client.get("/api/agent-scores?limit=1000").get_json()["scores"]
    n = len(scores)
    percentiles = [s["score_percentile"] for s in scores]
    assert all(0 <= p <= 100 for p in percentiles)
    assert percentiles == sorted(percentiles, reverse=True)
    assert percentiles[0] == round(100 * (n - 1) / n, 1)


def test_every_endpoint_reports_the_same_percentile(client) -> None:
    login(client, ANALYST)
    scores = {s["agent_id"]: s["score_percentile"]
              for s in client.get("/api/agent-scores?limit=1000").get_json()["scores"]}
    flagged = client.get("/api/flagged-agents").get_json()["flagged_agents"]
    everyone = client.get("/api/all-agents").get_json()["agents"]
    assert flagged and all(a["score_percentile"] == scores[a["agent_id"]] for a in flagged)
    assert all(a["score_percentile"] == scores[a["agent_id"]] for a in everyone)
    agent_id = flagged[0]["agent_id"]
    detail = client.get(f"/api/agents/{agent_id}").get_json()
    assert detail["score"]["score_percentile"] == scores[agent_id]
