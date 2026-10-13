"""risk_band (issue #18) on every agent payload."""

from collections import Counter

import pytest

from src.api import REVIEW_SCORE, risk_band
from tests.helpers import ANALYST, login

CUTOFF = 1.4447993633890617


@pytest.mark.parametrize("flag_source, score, expected", [
    ("ML", 1.5, "high"), ("Both", 9.0, "high"), ("Rule", 1.0, "review"),
    ("None", 1.3, "review"), ("None", 1.44, "review"), ("None", 1.2999, "low"), ("None", 0.9, "low"),
    (None, 2.0, None),
])
def test_risk_band_rules(flag_source, score, expected) -> None:
    assert risk_band(flag_source, score, CUTOFF) == expected
    assert REVIEW_SCORE == 1.3


def test_all_agents_risk_band_matches_flag_source_and_score(client) -> None:
    login(client, ANALYST)
    agents = client.get("/api/all-agents").get_json()["agents"]
    scores = {s["agent_id"]: s for s in client.get("/api/agent-scores?limit=1000").get_json()["scores"]}
    assert len(agents) == len(scores) == 1000
    for agent in agents:
        score = scores[agent["agent_id"]]
        assert agent["risk_band"] == score["risk_band"] == risk_band(score["flag_source"], score["anomaly_score"], CUTOFF)
    bands = Counter(a["risk_band"] for a in agents)
    sources = Counter(s["flag_source"] for s in scores.values())
    assert bands["high"] == sources["ML"] + sources["Both"]
    review_by_score = sum(1 for s in scores.values() if s["flag_source"] == "None" and REVIEW_SCORE <= s["anomaly_score"] < CUTOFF)
    assert bands["review"] == sources["Rule"] + review_by_score
    assert bands["low"] == 1000 - bands["high"] - bands["review"]


def test_flagged_agents_are_all_high(client) -> None:
    login(client, ANALYST)
    assert {a["risk_band"] for a in client.get("/api/flagged-agents").get_json()["flagged_agents"]} == {"high"}


def test_agent_detail_carries_risk_band(client, known_agent_id) -> None:
    login(client, ANALYST)
    body = client.get(f"/api/agents/{known_agent_id}").get_json()
    assert body["risk_band"] == body["score"]["risk_band"] == "high"
