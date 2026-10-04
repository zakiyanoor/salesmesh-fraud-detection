import joblib
import pytest
from src.detector import DEFAULT_ARTIFACT_PATH, FEATURE_COLUMNS, FraudDetector


def make_row(agent_id: str, frequency: int, dist: float, similarity: float, collusion: float) -> dict:
    return {
        "agent_id": agent_id,
        "submission_frequency": frequency,
        "time_of_day_dist": dist,
        "customer_similarity": similarity,
        "collusion_score": collusion,
    }


# Typical values from the v2 synthetic data (ml/results/evaluation_summary.md).
LEGIT = dict(frequency=115, dist=0.75, similarity=0.0, collusion=0.01)
RING = dict(frequency=300, dist=0.77, similarity=0.35, collusion=0.55)


@pytest.fixture(scope="module")
def detector() -> FraudDetector:
    return FraudDetector()


def test_collusion_score_is_a_detector_feature() -> None:
    assert "collusion_score" in FEATURE_COLUMNS


def test_detector_loads_the_isolation_forest_artifact(detector) -> None:
    assert detector.model_version == "isolation_forest_v2"


def test_score_returns_empty_for_no_rows(detector) -> None:
    assert detector.score([]) == []


def test_flags_ring_like_agent_and_clears_typical_legit_agent(detector) -> None:
    results = {r.agent_id: r for r in detector.score([make_row("L1", **LEGIT), make_row("R1", **RING)])}

    assert results["R1"].is_flagged
    assert not results["L1"].is_flagged


def test_suspicion_scores_are_normalized_between_zero_and_one(detector) -> None:
    extreme = make_row("X1", frequency=5000, dist=0.0, similarity=1.0, collusion=1.0)
    results = detector.score([make_row("L1", **LEGIT), make_row("R1", **RING), extreme])

    assert all(0.0 <= r.suspicion_score <= 1.0 for r in results)


def test_agent_score_does_not_depend_on_the_rest_of_the_batch(detector) -> None:
    """The model is loaded, not refitted per run, so batch composition can't move a score."""
    alone = detector.score([make_row("R1", **RING)])[0]
    in_batch = detector.score([make_row(f"L{i}", **LEGIT) for i in range(30)] + [make_row("R1", **RING)])[-1]

    assert alone == in_batch


def test_colluding_agents_score_higher_than_agents_with_no_overlap(detector) -> None:
    # Not asserted: that collusion alone gets an agent flagged. With every other
    # feature normal, collusion_score 0.5 scores well above legit but below the
    # Isolation Forest threshold.
    ring = make_row("C1", frequency=115, dist=0.75, similarity=0.0, collusion=0.5)
    results = {r.agent_id: r.suspicion_score for r in detector.score([make_row("L1", **LEGIT), ring])}

    assert results["C1"] > results["L1"]


def test_rejects_artifact_trained_on_different_features(tmp_path) -> None:
    artifact = joblib.load(DEFAULT_ARTIFACT_PATH)
    artifact["feature_columns"] = FEATURE_COLUMNS[:3]
    path = tmp_path / "mismatched.joblib"
    joblib.dump(artifact, path)

    with pytest.raises(ValueError, match="expects features"):
        FraudDetector(path)
