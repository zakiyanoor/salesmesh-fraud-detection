import numpy as np
import pandas as pd
import pytest

import data_generation as dg
import feature_engineering as fe

T0 = pd.Timestamp("2026-08-01 00:00:00")


def times(*hours):
    return pd.Series([T0 + pd.Timedelta(hours=h) for h in hours])


def test_submission_frequency_by_hand():
    # window [t, t+24h): 0h, 0.5h, 23.9h fall in one window; 24h starts a new one
    assert fe.submission_frequency(times(0, 0.5, 23.9, 24, 60)) == 3
    assert fe.submission_frequency(times(0, 24)) == 1
    assert fe.submission_frequency(times(10, 20, 30, 33.9)) == 4
    assert fe.submission_frequency(times()) == 0


def test_time_of_day_entropy_by_hand():
    assert fe.time_of_day_entropy(times(9, 9, 9)) == 0.0
    assert fe.time_of_day_entropy(times(*range(24))) == pytest.approx(1.0)
    # two hours, equal counts: entropy 1 bit / log2(24)
    assert fe.time_of_day_entropy(times(9, 10)) == pytest.approx(1 / np.log2(24))


def test_identifier_similarity_by_hand():
    assert fe.identifier_similarity(["CUST12345678", "CUST12345678"]) == 1.0
    assert fe.identifier_similarity(["CUST12345678", "CUST12345679"]) == 7 / 8
    assert fe.identifier_similarity(["CUST12345678", "CUST12345679", "CUST87654321"]) == 7 / 24
    assert fe.identifier_similarity(["CUST12345678"]) == 0.0


def test_collusion_score_by_hand():
    records = pd.DataFrame({"agent_id": ["A1", "A1", "A1", "A2"], "customer_id": ["c1", "c1", "c2", "c1"]})
    scores = fe.collusion_scores(records)
    assert scores["A1"] == 0.5  # c1 shared, c2 not; repeating c1 does not count twice
    assert scores["A2"] == 1.0


def test_volume_vs_peers_by_hand():
    volume = pd.Series([10, 20, 30, 40, 50], index=list("abcde"))
    category = pd.Series(["x", "x", "x", "y", "y"], index=volume.index)
    region = pd.Series(["R", "R", "R", "R", "R"], index=volume.index)
    ratio, level = fe.volume_vs_peers(volume, category, region, min_group=3)
    # x/R has 3 agents: leave-one-out medians 25, 20, 15
    assert ratio[["a", "b", "c"]].tolist() == [10 / 25, 20 / 20, 30 / 15]
    assert set(level[["a", "b", "c"]]) == {"category+region"}
    # y has 2 agents in every grouping, so it falls back to all agents: d's peers 10,20,30,50 -> 25
    assert ratio["d"] == 40 / 25 and level["d"] == "all"


def test_period_filter_and_period_columns():
    agents = pd.DataFrame({"agent_id": ["A1"], "region": ["Nairobi"]})
    records = pd.DataFrame({
        "agent_id": ["A1"] * 3, "customer_id": ["CUST10000001", "CUST10000002", "CUST10000003"],
        "client_id": ["CL01"] * 3, "category": ["banking"] * 3,
        "timestamp": ["2026-08-01 10:00:00", "2026-08-02 10:00:00", "2026-08-05 10:00:00"],
    })
    out = fe.compute_feature_vectors(records, agents, "2026-08-01", "2026-08-03")
    assert out.loc[0, "volume"] == 2
    assert out.loc[0, "analysis_period_start"] == pd.Timestamp("2026-08-01")
    assert out.loc[0, "analysis_period_end"] == pd.Timestamp("2026-08-03")


@pytest.fixture(scope="module")
def small():
    data = dg.generate_dataset(3, n_agents=150, fraud_rate=0.15)
    return data, fe.compute_feature_vectors(data.activations, data.agents)


def test_no_label_or_id_information_enters_the_features(small):
    data, features = small
    assert not {"is_fraud", "profile", "ring_id"} & set(features.columns)
    # renaming every agent id must not change any agent's feature values
    rename = {a: f"A{90000 + i}" for i, a in enumerate(data.agents["agent_id"].sample(frac=1, random_state=0))}
    renamed = fe.compute_feature_vectors(data.activations.assign(agent_id=data.activations["agent_id"].map(rename)),
                                         data.agents.assign(agent_id=data.agents["agent_id"].map(rename)))
    original = features.set_index(features["agent_id"].map(rename))[fe.ALL_FEATURES].sort_index()
    pd.testing.assert_frame_equal(original, renamed.set_index("agent_id")[fe.ALL_FEATURES].sort_index(),
                                  check_names=False)


def test_features_do_not_depend_on_the_label_file(small):
    data, features = small
    assert "is_fraud" not in data.agents.columns and "is_fraud" not in data.activations.columns
    assert len(features) == len(data.agents)
