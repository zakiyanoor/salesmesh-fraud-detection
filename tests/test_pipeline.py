from datetime import datetime
from types import SimpleNamespace
from src.pipeline import (
    compute_submission_frequency,
    compute_time_of_day_entropy,
    compute_repetition_score,
    compute_sequential_score,
    compute_customer_similarity,
)


def make_record(hour: int) -> SimpleNamespace:
    return SimpleNamespace(timestamp=datetime(2026, 8, 1, hour, 0, 0))


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