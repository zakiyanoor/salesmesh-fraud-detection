import pandas as pd
import pytest

import data_generation as dg
import split as sp


@pytest.fixture(scope="module")
def labels():
    return dg.generate_dataset(42).labels


@pytest.fixture(scope="module")
def assignment(labels):
    return sp.split_agents(labels)


def test_no_agent_is_in_two_splits(assignment, labels):
    assert not assignment["agent_id"].duplicated().any()
    assert set(assignment["agent_id"]) == set(labels["agent_id"])


def test_split_sizes_are_70_15_15(assignment):
    counts = assignment["split"].value_counts()
    assert counts.to_dict() == {"train": 700, "validation": 150, "test": 150}


def test_every_pattern_is_in_every_split(assignment, labels):
    merged = assignment.merge(labels, on="agent_id")
    stratum = sp.strata(merged)
    table = pd.crosstab(stratum, merged["split"])
    assert (table > 0).all().all()
    assert set(table.index) == {"legit", "ring", "weak_ring", "sequential", "duplicate", "weak"}


def test_eval_splits_have_enough_fraud_and_similar_share(assignment, labels):
    merged = assignment.merge(labels, on="agent_id")
    fraud = merged.groupby("split")["is_fraud"].agg(["sum", "mean"])
    assert (fraud.loc[["validation", "test"], "sum"] >= sp.MIN_FRAUD_PER_EVAL_SPLIT).all()
    assert fraud["mean"].max() - fraud["mean"].min() < 0.02


def test_split_is_deterministic(labels, assignment):
    assert sp.split_agents(labels).equals(assignment)


def test_too_few_fraud_agents_fails():
    small = dg.generate_dataset(1, n_agents=300, fraud_rate=0.13).labels
    with pytest.raises(ValueError, match="fraud agents"):
        sp.split_agents(small)


def test_duplicate_assignment_is_rejected(assignment, labels):
    broken = pd.concat([assignment, assignment.iloc[[0]].assign(split="test")])
    with pytest.raises(ValueError, match="more than one split"):
        sp.check_split(broken, labels)
