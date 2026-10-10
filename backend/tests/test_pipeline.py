import random
from datetime import datetime
from types import SimpleNamespace
import numpy as np
import data_generation
from src.detector import FEATURE_COLUMNS
from src.pipeline import (
    build_feature_row,
    compute_submission_frequency,
    compute_time_of_day_entropy,
    compute_repetition_score,
    compute_sequential_score,
    compute_customer_similarity,
    compute_collusion_score,
    compute_client_category_breakdown,
    derive_analysis_period,
)


def make_record(hour: int) -> SimpleNamespace:
    return SimpleNamespace(timestamp=datetime(2026, 8, 1, hour, 0, 0))


def make_activation(
    agent_id: str, customer_id: str, hour: int = 12, client_id: str | None = None, category: str | None = None
) -> SimpleNamespace:
    return SimpleNamespace(
        agent_id=agent_id,
        customer_id=customer_id,
        timestamp=datetime(2026, 8, 1, hour, 0, 0),
        client_id=client_id,
        category=category,
    )


def customer_ids_of(agent_id: str, records: list) -> list[str]:
    return [r.customer_id for r in records if r.agent_id == agent_id]


def test_submission_frequency_counts_records() -> None:
    records = [make_record(9), make_record(10), make_record(11)]
    assert compute_submission_frequency(records) == 3


def test_time_of_day_entropy_is_zero_for_empty() -> None:
    assert compute_time_of_day_entropy([]) == 0.0


def test_time_of_day_entropy_low_when_clustered() -> None:
    records = [make_record(2) for _ in range(20)]
    assert compute_time_of_day_entropy(records) == 0.0


def test_time_of_day_entropy_high_when_spread() -> None:
    hours = list(range(24))
    records = [make_record(h) for h in hours]
    entropy = compute_time_of_day_entropy(records)
    assert entropy > 0.9


def test_repetition_score_zero_for_unique_ids() -> None:
    ids = [f"CUST{i}" for i in range(10)]
    assert compute_repetition_score(ids) == 0.0


def test_repetition_score_high_for_duplicates() -> None:
    ids = ["CUST1"] * 10
    assert compute_repetition_score(ids) == 0.9


def test_sequential_score_high_for_incrementing_ids() -> None:
    ids = [f"CUST{i}" for i in range(10000, 10010)]
    assert compute_sequential_score(ids) == 1.0


def test_sequential_score_low_for_random_ids() -> None:
    ids = ["CUST48213", "CUST91742", "CUST10", "CUST99981"]
    assert compute_sequential_score(ids) < 0.5


def test_customer_similarity_takes_max_of_both_signals() -> None:
    sequential_ids = [f"CUST{i}" for i in range(20000, 20010)]
    assert compute_customer_similarity(sequential_ids) == 1.0


def test_collusion_score_zero_when_no_customers_shared() -> None:
    records = [make_activation("A1", f"CUST{i}") for i in range(5)]
    records += [make_activation("A2", f"CUST{i}") for i in range(100, 105)]
    assert compute_collusion_score("A1", customer_ids_of("A1", records), records) == 0.0
    assert compute_collusion_score("A2", customer_ids_of("A2", records), records) == 0.0


def test_collusion_score_is_one_for_both_agents_sharing_all_customers() -> None:
    shared = [f"CUST{i}" for i in range(5)]
    records = [make_activation("A1", c) for c in shared] + [make_activation("A2", c) for c in shared]
    assert compute_collusion_score("A1", customer_ids_of("A1", records), records) == 1.0
    assert compute_collusion_score("A2", customer_ids_of("A2", records), records) == 1.0


def test_collusion_score_is_fraction_of_customers_shared() -> None:
    records = [make_activation("A1", f"CUST{i}") for i in range(4)]
    records.append(make_activation("A2", "CUST0"))
    assert compute_collusion_score("A1", customer_ids_of("A1", records), records) == 0.25
    assert compute_collusion_score("A2", customer_ids_of("A2", records), records) == 1.0


def test_collusion_score_ignores_the_agents_own_records() -> None:
    records = [make_activation("A1", "CUST1"), make_activation("A1", "CUST1")]
    assert compute_collusion_score("A1", ["CUST1", "CUST1"], records) == 0.0


def test_collusion_score_counts_distinct_customers_not_repeats() -> None:
    own = ["CUST1"] * 9 + ["CUST2"]
    records = [make_activation("A1", c) for c in own] + [make_activation("A2", "CUST1")]
    assert compute_collusion_score("A1", own, records) == 0.5


def test_collusion_score_zero_for_agent_with_no_customers() -> None:
    assert compute_collusion_score("A1", [], [make_activation("A2", "CUST1")]) == 0.0


def test_build_feature_row_includes_collusion_score_from_all_records() -> None:
    a1 = [make_activation("A1", "CUST1", hour=9), make_activation("A1", "CUST2", hour=10)]
    a2 = [make_activation("A2", "CUST1", hour=9)]
    row = build_feature_row("A1", a1, a1 + a2)
    assert row["collusion_score"] == 0.5
    assert row["submission_frequency"] == 2


def test_client_id_and_category_are_not_detection_features() -> None:
    """client_id/category are pass-through context from other SalesMesh modules,
    not fraud signal, so they must never enter the whitelist the detector scores on."""
    assert "client_id" not in FEATURE_COLUMNS
    assert "category" not in FEATURE_COLUMNS

    a1 = [make_activation("A1", "CUST1", hour=9, client_id="Acme", category="fintech")]
    row = build_feature_row("A1", a1, a1)
    assert "client_id" not in row
    assert "category" not in row


def test_client_category_breakdown_returns_distinct_sorted_values() -> None:
    records = [
        make_activation("A1", "CUST1", client_id="Acme", category="fintech"),
        make_activation("A1", "CUST2", client_id="Acme", category="fintech"),
        make_activation("A1", "CUST3", client_id="Zenith", category="fashion"),
    ]
    breakdown = compute_client_category_breakdown(records)
    assert breakdown == {"client_ids": ["Acme", "Zenith"], "categories": ["fashion", "fintech"]}


def test_client_category_breakdown_empty_for_no_records() -> None:
    assert compute_client_category_breakdown([]) == {"client_ids": [], "categories": []}


def test_analysis_period_comes_from_the_records_not_the_run_date() -> None:
    august = [make_record(9), SimpleNamespace(timestamp=datetime(2026, 8, 30, 23, 0, 0))]
    assert derive_analysis_period(august) == "2026-08"

    spanning = august + [SimpleNamespace(timestamp=datetime(2026, 10, 2, 8, 0, 0))]
    assert derive_analysis_period(spanning) == "2026-08_to_2026-10"


def test_data_generation_assigns_client_id_and_category_from_known_lists() -> None:
    agents_df = data_generation.generate_agents(5, 2)
    activations = data_generation.generate_activation_records(agents_df)

    assert not activations.empty
    assert set(activations["client_id"].unique()) <= set(data_generation.CLIENTS)
    assert set(activations["category"].unique()) <= set(data_generation.CATEGORIES)
    # An agent can legitimately work across several clients/categories (SRS).
    assert activations.groupby("agent_id")["client_id"].nunique().max() > 1


def test_client_id_and_category_are_not_correlated_with_fraud_status() -> None:
    """Assigned independently of is_fraud: both groups should draw from (most
    of) the same pool, i.e. client_id/category carry no fraud signal."""
    agents_df = data_generation.generate_agents(30, 10)
    activations = data_generation.generate_activation_records(agents_df)

    fraud_agent_ids = set(agents_df[agents_df["is_fraud"]]["agent_id"])
    fraud_clients = set(activations[activations["agent_id"].isin(fraud_agent_ids)]["client_id"])
    legit_clients = set(activations[~activations["agent_id"].isin(fraud_agent_ids)]["client_id"])

    assert len(fraud_clients & legit_clients) >= len(data_generation.CLIENTS) - 1


def generate_ring_dataset(seed: int = 42):
    """Regenerate the synthetic data in memory, returning (dataset, ring agent ids, records)."""
    saved = (random.getstate(), np.random.get_state())
    try:
        dataset = data_generation.generate_dataset(seed)
    finally:
        random.setstate(saved[0])
        np.random.set_state(saved[1])

    records = [
        SimpleNamespace(agent_id=r.agent_id, customer_id=r.customer_id, timestamp=r.timestamp)
        for r in dataset.activations.itertuples()
    ]
    ring_agents = dataset.labels[dataset.labels["ring_id"] != ""]["agent_id"].tolist()
    return dataset, ring_agents, records


def test_collusion_ring_agents_from_synthetic_data_score_above_every_legit_agent() -> None:
    dataset, ring_agents, records = generate_ring_dataset()
    by_agent: dict[str, list] = {}
    for record in records:
        by_agent.setdefault(record.agent_id, []).append(record)

    rows = [build_feature_row(agent_id, recs, records) for agent_id, recs in by_agent.items()]
    collusion = {row["agent_id"]: row["collusion_score"] for row in rows}

    legit_agents = dataset.labels[~dataset.labels["is_fraud"]]["agent_id"]
    assert len(ring_agents) == dataset.rings["size"].sum()
    # Ring agents mix in normal activity (v2 generator), so they no longer score ~1,
    # but the shared pool still lifts every ring agent above every legit agent.
    assert all(collusion[a] > 0.3 for a in ring_agents)
    assert all(collusion[a] < 0.1 for a in legit_agents)
    assert min(collusion[a] for a in ring_agents) > max(collusion[a] for a in legit_agents)
    # Not asserted: that FraudDetector flags every ring agent. On the v2 data it
    # does not (see ml/results/evaluation_summary.md); that is a model finding,
    # not a feature-engineering invariant.
