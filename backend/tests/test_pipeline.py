import random
from datetime import datetime
from types import SimpleNamespace

import numpy as np
import pandas as pd

import data_generation
from src import ml_bridge
from src.pipeline import compute_client_category_breakdown, derive_analysis_period

collusion_scores = ml_bridge.feature_engineering.collusion_scores


def make_record(hour: int) -> SimpleNamespace:
    return SimpleNamespace(timestamp=datetime(2026, 8, 1, hour, 0, 0))


def make_activation(agent_id: str, customer_id: str, client_id: str | None = None,
                    category: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(agent_id=agent_id, customer_id=customer_id, timestamp=datetime(2026, 8, 1, 12, 0, 0),
                           client_id=client_id, category=category)


def frame(pairs) -> pd.DataFrame:
    return pd.DataFrame(pairs, columns=["agent_id", "customer_id"])


# --- collusion_score, now ml.feature_engineering.collusion_scores (imported, not copied) ---

def test_collusion_score_zero_when_no_customers_shared() -> None:
    scores = collusion_scores(frame([("A1", f"CUST{i}") for i in range(5)] + [("A2", f"CUST{i}") for i in range(100, 105)]))
    assert scores.to_dict() == {"A1": 0.0, "A2": 0.0}


def test_collusion_score_is_fraction_of_distinct_customers_shared() -> None:
    scores = collusion_scores(frame([("A1", f"CUST{i}") for i in range(4)] + [("A2", "CUST0")]))
    assert scores["A1"] == 0.25 and scores["A2"] == 1.0


def test_collusion_score_ignores_the_agents_own_repeats() -> None:
    assert collusion_scores(frame([("A1", "CUST1"), ("A1", "CUST1")]))["A1"] == 0.0
    own = [("A1", "CUST1")] * 9 + [("A1", "CUST2"), ("A2", "CUST1")]
    assert collusion_scores(frame(own))["A1"] == 0.5


def test_backend_uses_the_ml_feature_code_not_a_copy() -> None:
    import feature_engineering

    assert ml_bridge.compute_feature_vectors is feature_engineering.compute_feature_vectors
    assert ml_bridge.MODEL_FEATURES == ["submission_frequency", "time_of_day_entropy", "customer_similarity",
                                        "collusion_score"]


def test_client_id_and_category_are_not_model_features() -> None:
    assert not {"client_id", "category", "quality_score", "commission_kes", "account_status"} & set(ml_bridge.MODEL_FEATURES)


# --- context helpers kept in src.pipeline ---

def test_client_category_breakdown_returns_distinct_sorted_values() -> None:
    records = [
        make_activation("A1", "CUST1", client_id="Acme", category="fintech"),
        make_activation("A1", "CUST2", client_id="Acme", category="fintech"),
        make_activation("A1", "CUST3", client_id="Zenith", category="fashion"),
    ]
    assert compute_client_category_breakdown(records) == {"client_ids": ["Acme", "Zenith"], "categories": ["fashion", "fintech"]}


def test_client_category_breakdown_empty_for_no_records() -> None:
    assert compute_client_category_breakdown([]) == {"client_ids": [], "categories": []}


def test_analysis_period_comes_from_the_records_not_the_run_date() -> None:
    august = [make_record(9), SimpleNamespace(timestamp=datetime(2026, 8, 30, 23, 0, 0))]
    assert derive_analysis_period(august) == "2026-08"
    spanning = august + [SimpleNamespace(timestamp=datetime(2026, 10, 2, 8, 0, 0))]
    assert derive_analysis_period(spanning) == "2026-08_to_2026-10"


# --- the synthetic data the backend loads (generated in memory; labels.csv is never read) ---

def test_data_generation_assigns_client_id_and_category_from_known_lists() -> None:
    agents_df = data_generation.generate_agents(5, 2)
    activations = data_generation.generate_activation_records(agents_df)
    assert not activations.empty
    assert set(activations["client_id"].unique()) <= set(data_generation.CLIENTS)
    assert set(activations["category"].unique()) <= set(data_generation.CATEGORIES)
    assert activations.groupby("agent_id")["client_id"].nunique().max() > 1


def test_client_id_and_category_are_not_correlated_with_fraud_status() -> None:
    from data_checks import agent_table, chi_square_p

    agents = agent_table(data_generation.generate_dataset(42))
    assert chi_square_p(agents, "primary_client") > 0.05
    assert chi_square_p(agents, "primary_category") > 0.05


def generate_dataset_in_memory(seed: int = 42):
    saved = (random.getstate(), np.random.get_state())
    try:
        return data_generation.generate_dataset(seed)
    finally:
        random.setstate(saved[0])
        np.random.set_state(saved[1])


def test_collusion_ring_agents_from_synthetic_data_score_above_every_legit_agent() -> None:
    """
    The claim is separation: every strong-ring agent shares more of its customers
    than any honest agent. The old test also required every ring agent to score
    above a fixed 0.3. That floor described the v2 data; on the v3 data (integrity
    rules R1 to R6, DATA_CARD.md) the lowest strong-ring agent scores 0.288 and the
    highest honest agent 0.100, so the floor no longer matched while the
    separation it was meant to show still holds. Weak rings overlap honest agents
    by design and are not asserted.
    """
    dataset = generate_dataset_in_memory()
    scores = collusion_scores(dataset.activations)
    labels = dataset.labels.set_index("agent_id")
    ring = scores[labels.reindex(scores.index)["profile"] == "ring"]
    legit = scores[~labels.reindex(scores.index)["is_fraud"].astype(bool)]
    assert len(ring) == dataset.rings.loc[dataset.rings["strength"] == "strong", "size"].sum()
    assert ring.min() > legit.max()
    assert (ring > 0).all()
