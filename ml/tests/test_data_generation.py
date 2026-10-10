import re

import pandas as pd
import pytest

import data_generation as dg
from clean_data import CUSTOMER_ID_PATTERN
from data_checks import agent_table, chi_square_p
from feature_engineering import compute_repetition_score, compute_sequential_score


@pytest.fixture(scope="module")
def dataset():
    return dg.generate_dataset(42)


def frames_equal(a, b):
    return all(x.equals(y) for x, y in zip(a, b))


def test_same_seed_gives_identical_output(dataset):
    assert frames_equal(dataset, dg.generate_dataset(42))


def test_different_seed_gives_different_output(dataset):
    assert not dataset.activations.equals(dg.generate_dataset(7).activations)


def test_default_counts_follow_n_agents_and_fraud_rate(dataset):
    assert len(dataset.agents) == dg.DEFAULT_N_AGENTS == 1000
    assert int(dataset.labels["is_fraud"].sum()) == round(1000 * 0.13)


def test_parameters_change_the_counts():
    small = dg.generate_dataset(1, n_agents=200, fraud_rate=0.2)
    assert len(small.agents) == 200
    assert int(small.labels["is_fraud"].sum()) == 40


@pytest.mark.parametrize("n_agents, fraud_rate", [(0, 0.1), (100, 0.0), (100, 1.0)])
def test_invalid_parameters_raise(n_agents, fraud_rate):
    with pytest.raises(ValueError):
        dg.generate_dataset(1, n_agents=n_agents, fraud_rate=fraud_rate)


def test_agents_file_carries_no_labels(dataset):
    assert list(dataset.agents.columns) == ["agent_id", "registration_timestamp", "region"]
    assert set(dataset.labels.columns) == {"agent_id", "is_fraud", "profile", "ring_id"}


def test_agent_ids_are_unique_and_not_ordered_by_label(dataset):
    ids = dataset.labels["agent_id"]
    assert ids.is_unique
    assert ids.str.fullmatch(r"A\d{5}").all()
    fraud_in_first_half = dataset.labels["is_fraud"].iloc[: len(ids) // 2].mean()
    assert 0.08 < fraud_in_first_half < 0.18


def test_allocate_rounds_to_the_total():
    counts = dg.allocate(78, dg.FRAUD_PATTERN_SHARES)
    assert sum(counts.values()) == 78
    assert counts == {"ring": 25, "weak_ring": 13, "sequential": 12, "duplicate": 12, "weak": 16}


def test_every_pattern_and_hard_legit_group_is_present(dataset):
    profiles = dataset.labels["profile"].value_counts()
    for profile in ["legit", "legit_night", "legit_repeat", "legit_busy", "ring", "weak_ring", "sequential", "duplicate", "weak"]:
        assert profiles.get(profile, 0) > 0
    assert (profiles[["legit_night", "legit_repeat", "legit_busy"]] == [70, 69, 52]).all()


def test_rings_vary_in_size_pool_and_hours(dataset):
    rings = dataset.rings
    assert len(rings) >= 3
    assert rings["size"].nunique() > 1 and rings["pool_size"].nunique() > 1 and rings["hour_start"].nunique() > 1
    ring_members = dataset.labels[dataset.labels["ring_id"] != ""].groupby("ring_id").size()
    assert ring_members.to_dict() == rings.set_index("ring_id")["size"].to_dict()
    assert (rings["size"] >= 2).all()
    assert set(rings["strength"]) == {"strong", "weak"}


def test_ring_pools_contain_no_consecutive_ids():
    numbers = sorted(int(c[4:]) for c in dg.non_consecutive_customer_ids(500))
    assert all(b - a > 1 for a, b in zip(numbers, numbers[1:]))


def test_only_sequential_agents_have_a_sequential_signal(dataset):
    scores = dataset.activations.groupby("agent_id")["customer_id"].apply(compute_sequential_score)
    by_profile = dataset.labels.set_index("agent_id").join(scores.rename("seq")).groupby("profile")["seq"].max()
    assert by_profile.drop("sequential").max() < 0.05
    assert by_profile["sequential"] > 0.5


def test_weak_fraud_repeats_less_than_duplicate_fraud(dataset):
    rep = dataset.activations.groupby("agent_id")["customer_id"].apply(compute_repetition_score)
    by_agent = dataset.labels.set_index("agent_id").join(rep.rename("rep"))
    assert by_agent.loc[by_agent["profile"] == "weak", "rep"].max() < by_agent.loc[by_agent["profile"] == "duplicate", "rep"].min()


def test_fraud_agents_keep_a_normal_looking_share(dataset):
    acts = dataset.activations.merge(dataset.labels, on="agent_id")
    seq = acts[acts["profile"] == "sequential"].copy()
    seq["num"] = seq["customer_id"].str[4:].astype(int)
    in_run = seq.groupby("agent_id")["num"].transform(lambda s: s.isin(s + 1) | s.isin(s - 1))
    assert 0.2 < 1 - in_run.mean() < 0.4


def test_records_pass_the_cleaning_formats(dataset):
    acts = dataset.activations
    assert acts["customer_id"].str.match(CUSTOMER_ID_PATTERN).all()
    assert acts["record_id"].is_unique
    ts = pd.to_datetime(acts["timestamp"])
    assert ts.min() >= dg.ANALYSIS_START and ts.max() < dg.ANALYSIS_END + pd.Timedelta(days=1)
    assert set(acts["agent_id"]) <= set(dataset.agents["agent_id"])


@pytest.fixture(scope="module")
def agents(dataset):
    return agent_table(dataset)


def collusion_scores(dataset):
    return agent_table(dataset)


def test_regions_are_kenyan_counties_independent_of_label(dataset):
    from scipy.stats import chi2_contingency

    assert len(dg.COUNTY_POPULATION_THOUSANDS) == 47
    assert set(dg.COUNTY_TO_FORMER_PROVINCE) == set(dg.COUNTY_POPULATION_THOUSANDS)
    assert set(dataset.agents["region"]) <= set(dg.COUNTY_POPULATION_THOUSANDS)
    merged = dataset.agents.merge(dataset.labels, on="agent_id")
    province = merged["region"].map(dg.COUNTY_TO_FORMER_PROVINCE)
    assert chi2_contingency(pd.crosstab(province, merged["is_fraud"]))[1] > 0.05


def test_large_counties_get_more_agents(dataset):
    counts = dataset.agents["region"].value_counts()
    assert counts.get("Nairobi", 0) > counts.get("Lamu", 0)
    assert counts.idxmax() == "Nairobi"


def test_some_legit_agents_share_customers_mostly_within_their_county(dataset):
    scores = collusion_scores(dataset)
    legit = scores[~scores["is_fraud"]]
    assert (legit["collusion"] > 0).mean() > 0.2

    acts = dataset.activations.merge(dataset.agents[["agent_id", "region"]], on="agent_id")
    acts = acts[acts["agent_id"].isin(legit.index)]
    shared = acts.groupby("customer_id")["agent_id"].nunique()
    counties = acts[acts["customer_id"].isin(shared[shared > 1].index)].groupby("customer_id")["region"].nunique()
    # The rest are chance collisions between random 8-digit ids (about 10% at seed 42).
    assert (counties == 1).mean() > 0.8


def test_weak_rings_share_less_than_strong_rings(dataset):
    scores = collusion_scores(dataset)
    weak = scores.loc[scores["profile"] == "weak_ring", "collusion"]
    strong = scores.loc[scores["profile"] == "ring", "collusion"]
    assert (weak > 0).all()
    assert weak.max() < strong.min()


def test_every_county_has_at_least_the_floor(agents):
    per_county = agents["region"].value_counts().reindex(dg.COUNTIES, fill_value=0)
    assert per_county.min() >= dg.COUNTY_MIN_AGENTS


def test_small_runs_relax_the_county_floor():
    small = dg.generate_dataset(3, n_agents=50, fraud_rate=0.2)
    assert len(small.agents) == 50


def test_fraud_is_independent_of_county_region_category_and_client(agents):
    for column in ["region", "former_region", "primary_category", "primary_client"]:
        assert chi_square_p(agents, column) > 0.05, column


def test_clients_reference_list(dataset):
    clients = dataset.clients
    assert len(clients) == 20 and clients["client_id"].is_unique
    assert clients["name"].str.fullmatch(r"Client \d{2}").all()
    assert set(clients["category"]) == set(dg.CATEGORIES) and len(dg.CATEGORIES) == 12


def test_record_category_comes_from_its_client(dataset):
    acts = dataset.activations
    assert set(acts["client_id"]) <= set(dg.CLIENTS)
    assert (acts["category"] == acts["client_id"].map(dg.CLIENT_CATEGORY)).all()


def test_agents_work_with_one_to_three_clients_mostly_in_one_or_two_categories(agents):
    assert agents["n_clients"].between(1, 3).all()
    assert (agents["n_categories"] <= 2).mean() > 0.9


def test_duplicate_fraud_resubmits_the_same_customer_for_the_same_client(dataset):
    acts = dataset.activations.merge(dataset.labels, on="agent_id")
    dup = acts[acts["profile"] == "duplicate"]
    per_pair = dup.groupby(["agent_id", "customer_id"])["client_id"].agg(["size", "nunique"])
    resubmitted = per_pair[per_pair["size"] > 1]
    assert len(resubmitted) > 0
    assert (resubmitted["nunique"] == 1).mean() > 0.9


def test_same_customer_for_different_clients_is_rare(dataset):
    per_pair = dataset.activations.groupby(["agent_id", "customer_id"])["client_id"].nunique()
    assert 0 < (per_pair > 1).mean() < 0.05


def test_timestamps_fall_in_the_observation_window(dataset):
    ts = pd.to_datetime(dataset.activations["timestamp"])
    assert ts.dt.tz is None and dg.TIMEZONE == "Africa/Nairobi"
    assert ts.min() >= dg.ANALYSIS_START and ts.max() < dg.ANALYSIS_END + pd.Timedelta(days=1)


ACCEPTED_ZERO_OVERLAP = {("collusion_score", "ring"), ("customer_similarity", "sequential"), ("night_share", "sequential")}


@pytest.fixture(scope="module")
def audit(dataset):
    from data_checks import overlap_audit

    return overlap_audit(dataset)


def test_legit_agents_also_work_off_hours(dataset):
    acts = dataset.activations.merge(dataset.labels, on="agent_id")
    legit_hours = pd.to_datetime(acts.loc[~acts["is_fraud"], "timestamp"]).dt.hour
    assert set(range(24)) <= set(legit_hours)
    plain = acts[acts["profile"] == "legit"]
    odd = pd.to_datetime(plain["timestamp"]).dt.hour.isin([5, 6, 20, 21, 22, 23])
    assert odd.groupby(plain["agent_id"]).any().mean() > 0.3


def test_daily_volume_has_no_class_specific_cap(audit):
    _, table = audit
    plain_max = table.loc[table["group"] == "legit", "max_per_day"]
    assert plain_max.max() > 20
    weak_max = table.loc[table["group"] == "weak", "max_per_day"]
    assert weak_max.nunique() > 3


def test_only_accepted_signatures_have_zero_overlap_with_legit(audit):
    rows, _ = audit
    zero = {(r.descriptor, r.group) for r in rows.itertuples() if r.zero_overlap}
    assert zero == ACCEPTED_ZERO_OVERLAP


def test_identifier_similarity_by_hand():
    from data_checks import identifier_similarity

    assert identifier_similarity(["CUST12345678", "CUST12345678"]) == 1.0
    assert identifier_similarity(["CUST12345678", "CUST12345679"]) == 7 / 8
    # pairs: (a,b) 7 matches, (a,c) 0, (b,c) 0 -> 7 / (8 * 3)
    assert identifier_similarity(["CUST12345678", "CUST12345679", "CUST87654321"]) == 7 / 24
    assert identifier_similarity(["CUST12345678"]) == 0.0
