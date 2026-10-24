"""identifier_similarity on ids of any prefix and length (issue #26), and no change to the frozen features."""

from pathlib import Path

import pandas as pd
import pytest

import feature_engineering as fe

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"


def test_existing_cases_are_unchanged() -> None:
    assert fe.identifier_similarity(["CUST12345678", "CUST12345678"]) == 1.0
    assert fe.identifier_similarity(["CUST12345678", "CUST12345679"]) == 7 / 8
    assert fe.identifier_similarity(["CUST12345678", "CUST12345679", "CUST87654321"]) == 7 / 24
    assert fe.identifier_similarity(["CUST12345678"]) == 0.0


@pytest.mark.parametrize("ids, expected", [
    (["12345678", "12345679"], 7 / 8),  # no prefix: all 8 digits count (it used to cut the first 4: 0.75)
    (["C001", "C002"], 2 / 3),  # a 1-letter prefix (it used to divide by zero)
    (["ACC-00042", "ACC-00043"], 4 / 5),  # a prefix with punctuation
    (["CUST999", "CUST1000"], 0.0),  # right-aligned: 0999 vs 1000 share no position; padding never matches
    (["CUST1234", "CUST91234"], 4 / 5),  # right-aligned: the last 4 digits match, over the longest length 5
    (["CUST1234", "C1234", "1234"], 1.0),  # mixed prefixes in one set: all reduce to 1234
    (["AB-12x9", "AB-12y9"], 3 / 4),  # non-digit characters after the prefix are compared as characters
    (["ABC", "ABD"], 2 / 3),  # no digit at all: the id is kept whole
    (["ABC", "1"], 0.0),
])
def test_ids_of_any_prefix_and_length(ids, expected) -> None:
    assert fe.identifier_similarity(ids) == pytest.approx(expected)


def test_nothing_to_compare_gives_zero() -> None:
    assert fe.identifier_similarity([]) == 0.0
    assert fe.identifier_similarity(["CUST1"]) == 0.0
    assert fe.identifier_similarity(["CUST", "CUST"]) == 1.0  # no digit: compared whole


def test_frozen_customer_similarity_is_reproduced_exactly(tmp_path) -> None:
    """
    customer_similarity for all 1000 agents, recomputed with the current function, equals the frozen
    data/synthetic/feature_vectors.csv (hashed in results/FREEZE.md) with a difference of exactly 0.
    A freshly computed value and the same value read back from a CSV can differ in the last binary
    digit, so the test uses the same round trip as the pipeline (feature_engineering.main writes the
    file with to_csv(index=False), and every later step reads it with read_csv).
    """
    features = fe.compute_feature_vectors(pd.read_csv(DATA / "activation_records_clean.csv"),
                                          pd.read_csv(DATA / "agents.csv"))
    features.to_csv(tmp_path / "feature_vectors.csv", index=False)
    recomputed = pd.read_csv(tmp_path / "feature_vectors.csv")
    frozen = pd.read_csv(DATA / "feature_vectors.csv")
    assert len(frozen) == 1000 and recomputed["agent_id"].tolist() == frozen["agent_id"].tolist()
    difference = (recomputed["customer_similarity"] - frozen["customer_similarity"]).abs()
    assert difference.max() == 0.0
    assert (recomputed["customer_similarity"].values == frozen["customer_similarity"].values).all()
