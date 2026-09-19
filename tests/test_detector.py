from src.detector import FEATURE_COLUMNS, FraudDetector


def make_rows(
    agent_ids: list[str], frequency: int, dist: float, similarity: float, collusion: float = 0.0
) -> list[dict]:
    return [
        {
            "agent_id": agent_id,
            "submission_frequency": frequency,
            "time_of_day_dist": dist,
            "customer_similarity": similarity,
            "collusion_score": collusion,
        }
        for agent_id in agent_ids
    ]


def test_collusion_score_is_a_detector_feature() -> None:
    assert "collusion_score" in FEATURE_COLUMNS


def test_score_returns_empty_for_no_rows() -> None:
    detector = FraudDetector()
    assert detector.score([]) == []


def test_score_flags_clear_outliers() -> None:
    legit_rows = make_rows([f"L{i}" for i in range(30)], frequency=100, dist=0.75, similarity=0.0)
    fraud_rows = make_rows(["F1", "F2", "F3"], frequency=900, dist=0.34, similarity=0.98)

    detector = FraudDetector(contamination=0.1, n_neighbors=10)
    results = detector.score(legit_rows + fraud_rows)

    flagged_ids = {r.agent_id for r in results if r.is_flagged}
    assert {"F1", "F2", "F3"}.issubset(flagged_ids)


def test_suspicion_scores_are_normalized_between_zero_and_one() -> None:
    rows = make_rows([f"A{i}" for i in range(20)], frequency=100, dist=0.5, similarity=0.1)
    detector = FraudDetector(n_neighbors=5)
    results = detector.score(rows)

    assert all(0.0 <= r.suspicion_score <= 1.0 for r in results)


def test_score_flags_colluding_agents_that_look_normal_on_every_other_feature() -> None:
    legit_rows = make_rows([f"L{i}" for i in range(30)], frequency=100, dist=0.75, similarity=0.0)
    ring_rows = make_rows(
        ["C1", "C2", "C3"], frequency=100, dist=0.75, similarity=0.0, collusion=1.0
    )

    detector = FraudDetector(contamination=0.1, n_neighbors=10)
    results = detector.score(legit_rows + ring_rows)

    flagged_ids = {r.agent_id for r in results if r.is_flagged}
    assert {"C1", "C2", "C3"} <= flagged_ids


def test_colluding_agents_score_higher_than_agents_with_no_overlap() -> None:
    legit_rows = make_rows([f"L{i}" for i in range(30)], frequency=100, dist=0.75, similarity=0.0)
    ring_rows = make_rows(["C1", "C2"], frequency=100, dist=0.75, similarity=0.0, collusion=0.9)

    results = FraudDetector(contamination=0.1, n_neighbors=10).score(legit_rows + ring_rows)
    scores = {r.agent_id: r.suspicion_score for r in results}

    assert min(scores["C1"], scores["C2"]) > max(scores[f"L{i}"] for i in range(30))
