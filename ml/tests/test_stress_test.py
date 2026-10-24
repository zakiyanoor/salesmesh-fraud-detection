"""Unit tests for the stress test transforms (toy frames only; the stress run itself is not executed here)."""

import numpy as np
import pandas as pd
import pytest

import data_generation as dg
import stress_test as st
from baselines import duplicate_activation_counts


def frame(rows):
    acts = pd.DataFrame(rows, columns=["agent_id", "timestamp", "customer_id", "client_id", "activation_status"])
    acts["timestamp"] = pd.to_datetime(acts["timestamp"])
    return acts


def labels(profiles):
    return pd.DataFrame({"agent_id": list(profiles), "profile": list(profiles.values()),
                         "is_fraud": [not p.startswith("legit") for p in profiles.values()]})


def test_sequential_gaps_renumbers_only_the_run_with_gaps_1_to_3():
    rows = [("A1", f"2026-08-01 0{i % 5}:00", f"CUST{10000000 + i}", "CL01", "completed") for i in range(10)]
    rows.append(("A1", "2026-08-02 13:00", "CUST55555555", "CL01", "completed"))
    acts = frame(rows)
    out, counts = st.sequential_gaps(acts, labels({"A1": "sequential"}), np.random.default_rng(1))
    assert counts["records_identified"] == 10 and len(out) == len(acts)
    assert out.loc[10, "customer_id"] == "CUST55555555"
    run = out.iloc[:10].sort_values("timestamp", kind="mergesort")["customer_id"].str[4:].astype(int)
    assert run.iloc[0] == 10000000 and set(np.diff(run.values)) <= {1, 2, 3}
    assert out["customer_id"].str.fullmatch(r"CUST\d{8}").all() and out["customer_id"].is_unique


def test_duplicate_spread_moves_only_repeated_pairs_and_keeps_time_of_day():
    rows = [("A1", f"2026-08-0{d} 05:{d:02d}:07", "CUST10000001", "CL01", "completed") for d in range(1, 5)]
    rows.append(("A1", "2026-08-03 14:00:00", "CUST20000000", "CL01", "completed"))
    acts = frame(rows)
    out, counts = st.duplicate_spread(acts, labels({"A1": "duplicate"}), np.random.default_rng(1))
    assert counts["pairs_used_3_plus"] == 1 and counts["records_identified"] == 4
    assert out.loc[4, "timestamp"] == acts.loc[4, "timestamp"]
    moved = out.iloc[:4]["timestamp"]
    assert (moved.dt.time.values == acts.iloc[:4]["timestamp"].dt.time.values).all()
    assert (moved >= dg.ANALYSIS_START).all() and (moved < dg.ANALYSIS_START + pd.Timedelta(days=60)).all()


def test_evasion_a_leaves_the_rule_nothing_on_fraud_agents():
    acts = frame([
        ("H1", "2026-08-01 10:00", "CUST10000001", "CL01", "completed"),
        ("F1", "2026-08-02 10:00", "CUST10000001", "CL01", "completed"),  # shared with H1: dropped
        ("F1", "2026-08-03 10:00", "CUST10000002", "CL01", "completed"),
        ("F1", "2026-08-04 10:00", "CUST10000002", "CL01", "completed"),  # repeat after completed: dropped
        ("F1", "2026-08-05 10:00", "CUST10000003", "CL01", "failed"),
        ("F1", "2026-08-06 10:00", "CUST10000003", "CL01", "completed"),  # retry after a failure: kept
        ("H1", "2026-08-07 10:00", "CUST10000009", "CL01", "completed"),
        ("H1", "2026-08-08 10:00", "CUST10000009", "CL01", "completed"),  # honest: never changed
    ])
    out, counts = st.evasion_a(acts, labels({"H1": "legit", "F1": "duplicate"}))
    assert counts["records_dropped"] == 2 and sorted(set(acts.index) - set(out.index)) == [1, 3]
    pairs = duplicate_activation_counts(out)
    assert pairs.get("F1", 0) == 0 and pairs["H1"] == 1


def test_evasion_b_draws_hours_from_the_distribution_and_keeps_everything_else():
    acts = frame([(a, f"2026-08-{d:02d} 02:17:33", f"CUST1000000{d}", "CL01", "completed")
                  for a in ["R1", "H1"] for d in range(1, 9)])
    share = pd.Series(0.0, index=range(24))
    share[[9, 14]] = 0.5
    out, counts = st.evasion_b(acts, labels({"R1": "ring", "H1": "legit"}), share, np.random.default_rng(1))
    ring = out["agent_id"] == "R1"
    assert counts == {"agents": 1, "records_given_new_hour": 8, "records_hour_changed": 8}
    assert set(out.loc[ring, "timestamp"].dt.hour) <= {9, 14}
    assert (out.loc[ring, "timestamp"].dt.date.values == acts.loc[ring, "timestamp"].dt.date.values).all()
    assert (out.loc[ring, "timestamp"].dt.minute == 17).all() and (out.loc[ring, "timestamp"].dt.second == 33).all()
    assert out.loc[~ring].equals(acts.loc[~ring])
    assert out.drop(columns="timestamp").equals(acts.drop(columns="timestamp"))


def test_shifted_constants_are_restored():
    with st.shifted_constants():
        assert dg.RING_SIZE_RANGE == (7, 12) and dg.LEGIT_PATTERN_SHARES["legit_night"] == 0.16
    assert dg.RING_SIZE_RANGE == (2, 6) and dg.LEGIT_NIGHT_SHARE_RANGE == (0.10, 0.25)
    assert dg.LEGIT_PATTERN_SHARES["legit_night"] == 0.08


def test_verdict_rule():
    assert st.verdict(0.1, 0.02, 0.2).startswith("model")
    assert st.verdict(-0.1, -0.2, -0.01).startswith("rule")
    assert st.verdict(0.1, -0.01, 0.2) == "no clear difference"


def test_refuses_a_second_run(tmp_path):
    st.refuse_if_already_run(tmp_path)
    (tmp_path / "20261022-120000_stress_test_s201").mkdir()
    with pytest.raises(SystemExit):
        st.refuse_if_already_run(tmp_path)
