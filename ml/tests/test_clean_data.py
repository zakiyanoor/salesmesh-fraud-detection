import pandas as pd
import pytest

import clean_data as cd
import data_generation as dg


@pytest.fixture(scope="module")
def raw():
    data = dg.generate_dataset(5, n_agents=120, fraud_rate=0.15)
    return data.activations, data.agents, data.clients


def run(acts, agents, clients):
    return cd.clean_data(acts, agents, clients)


def test_generated_data_passes_every_check(raw):
    clean, findings, _, _ = run(*raw)
    assert findings["rows_removed"] == 0
    assert not any(findings["invalid"].values())
    assert list(clean.columns) == cd.EXPECTED_COLUMNS


def test_cleaning_does_not_need_labels(raw):
    acts, agents, clients = raw
    assert "is_fraud" not in acts.columns and "is_fraud" not in agents.columns
    run(acts, agents, clients)


def row_like(acts, **changes):
    row = acts.iloc[[0]].copy()
    for column, value in changes.items():
        row[column] = value
    return row


@pytest.mark.parametrize("changes, check", [
    ({"record_id": "X1"}, "malformed_record_id"),
    ({"agent_id": "A99"}, "malformed_agent_id"),
    ({"agent_id": "A00001"}, "unknown_agent_id"),
    ({"customer_id": "CUST12"}, "malformed_customer_id"),
    ({"client_id": "CL99"}, "unknown_client_id"),
    ({"client_id": "CL01", "category": "fashion"}, "category_not_client_category"),
    ({"activation_status": "done"}, "invalid_activation_status"),
    ({"timestamp": "not a date"}, "unparseable_timestamp"),
    ({"timestamp": "2026-09-15 10:00:00"}, "timestamp_outside_window"),
])
def test_each_invalid_row_is_caught_and_removed(raw, changes, check):
    acts, agents, clients = raw
    bad = row_like(acts, **{"record_id": "R999999999", **changes})
    _, findings, _, _ = run(pd.concat([acts, bad]), agents, clients)
    assert findings["invalid"][check] >= 1
    assert findings["removed_invalid"] == 1


def test_activation_before_registration_is_removed(raw):
    acts, agents, clients = raw
    agents = agents.copy()
    first = acts.iloc[0]
    agents.loc[agents["agent_id"] == first["agent_id"], "registration_timestamp"] = "2026-08-30 23:59:59"
    _, findings, _, _ = run(acts, agents, clients)
    assert findings["invalid"]["timestamp_before_registration"] >= 1


def test_missing_and_duplicate_rows_are_removed(raw):
    acts, agents, clients = raw
    missing = row_like(acts, record_id="R999999998", customer_id=None)
    _, findings, _, _ = run(pd.concat([acts, acts.iloc[[1]], acts.iloc[[2]].assign(customer_id="CUST11111111"), missing]),
                            agents, clients)
    assert findings["removed_missing_required"] == 1
    assert findings["removed_exact_duplicate_rows"] == 1
    assert findings["removed_duplicate_record_ids"] == 1


def small_frame(rows):
    return pd.DataFrame([{"record_id": f"R{i}", "agent_id": a, "client_id": c, "customer_id": cust,
                          "timestamp": pd.Timestamp(ts)} for i, (a, c, cust, ts) in enumerate(rows)])


def test_near_duplicates_by_hand():
    df = small_frame([
        ("A1", "CL01", "CUST10000000", "2026-08-01 10:00"),
        ("A1", "CL01", "CUST10000000", "2026-08-01 10:09"),  # same customer within 10 min
        ("A1", "CL01", "CUST10000001", "2026-08-01 10:05"),  # one digit away within 10 min
        ("A1", "CL01", "CUST10000000", "2026-08-01 10:30"),  # same customer, too late
        ("A1", "CL02", "CUST10000000", "2026-08-01 10:01"),  # other client
        ("A2", "CL01", "CUST10000000", "2026-08-01 10:02"),  # other agent
        ("A1", "CL01", "CUST20000099", "2026-08-01 10:03"),  # two digits away
    ])
    same, one_digit = cd.near_duplicates(df)
    assert same == {"R1"}
    assert one_digit == {"R2"}


def test_outliers_are_flagged_not_removed(raw):
    acts, agents, clients = raw
    clean, findings, _, agent_outliers = run(*raw)
    assert len(clean) == len(acts)
    assert set(agent_outliers["agent_id"]) == set(acts["agent_id"])
    assert findings["outliers_per_agent_total"]["iqr_outliers"] == int(agent_outliers["iqr_outlier"].sum())
