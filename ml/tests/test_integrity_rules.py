"""Integrity rules R1-R6 (data change #5), on small hand-built fixtures and on generated data."""

import pandas as pd
import pytest

import data_generation as dg
import feature_engineering as fe
from data_checks import identity_checks, independence_table, referential_integrity, rule_checks

CONTEXT_COLUMNS = {"account_status", "quality_score", "commission_kes", "commission_per_activation_kes",
                   "certification_status", "certified_at", "full_name", "phone_number", "national_id_number"}
IDENTITY_COLUMNS = {"full_name", "phone_number", "national_id_number"}


def make_dataset(records, fraud=(), categories=None):
    """records: (agent_id, timestamp, customer_id, status, client_id)."""
    acts = pd.DataFrame(records, columns=["agent_id", "timestamp", "customer_id", "activation_status", "client_id"])
    acts.insert(0, "record_id", [f"R{i}" for i in range(len(acts))])
    acts["category"] = acts["client_id"].map(dg.CLIENT_CATEGORY)
    acts["quality_score"] = 80
    acts["commission_kes"] = 0
    agent_ids = sorted(set(acts["agent_id"]))
    agents = pd.DataFrame({"agent_id": agent_ids, "registration_timestamp": "2026-06-01 00:00:00",
                           "region": "Nairobi", "account_status": "active"})
    labels = pd.DataFrame({"agent_id": agent_ids, "is_fraud": [a in fraud for a in agent_ids],
                           "profile": ["duplicate" if a in fraud else "legit" for a in agent_ids], "ring_id": ""})
    if categories is None:
        categories = acts[["agent_id", "category"]].drop_duplicates().assign(
            certification_status="certified", certified_at="2026-07-01 00:00:00")
    identity = pd.DataFrame({"agent_id": agent_ids, "full_name": "", "phone_number": "", "national_id_number": ""})
    return dg.SyntheticDataset(agents, acts, labels, pd.DataFrame(), dg.clients_frame(), identity, categories)


def rules(records, **kwargs):
    return rule_checks(make_dataset(records, **kwargs))


def test_r1_a_pair_used_by_two_honest_agents_is_a_violation():
    shared = [("A1", "2026-08-05 10:00:00", "CUST1", "completed", "CL01"),
              ("A2", "2026-08-06 10:00:00", "CUST1", "completed", "CL01")]
    assert rules(shared)["R1_pairs_used_by_another_agent"] == {"honest": 1, "fraud": 0}
    other_client = shared[:1] + [("A2", "2026-08-06 10:00:00", "CUST1", "completed", "CL03")]
    assert rules(other_client)["R1_pairs_used_by_another_agent"] == {"honest": 0, "fraud": 0}


def test_r2_honest_repeat_only_after_failed_or_pending():
    retry = [("A1", "2026-08-05 10:00:00", "CUST1", "failed", "CL01"),
             ("A1", "2026-08-06 10:00:00", "CUST1", "completed", "CL01")]
    assert rules(retry)["R2_repeat_after_completed"]["honest"] == 0
    resubmit = [("A1", "2026-08-05 10:00:00", "CUST1", "completed", "CL01"),
                ("A1", "2026-08-06 10:00:00", "CUST1", "failed", "CL01"),
                ("A1", "2026-08-07 10:00:00", "CUST1", "completed", "CL01")]
    assert rules(resubmit)["R2_repeat_after_completed"]["honest"] == 1
    cross_sell = [("A1", "2026-08-05 10:00:00", "CUST1", "completed", "CL01"),
                  ("A1", "2026-08-06 10:00:00", "CUST1", "completed", "CL02")]
    assert rules(cross_sell)["R2_repeat_after_completed"]["honest"] == 0


def test_r3_honest_agents_share_customers_only_across_clients():
    records = [("A1", "2026-08-05 10:00:00", "CUST1", "completed", "CL01"),
               ("A2", "2026-08-06 10:00:00", "CUST1", "completed", "CL03")]
    checks = rules(records)
    assert checks["R3_honest_customers_shared_by_2plus_honest_agents"] == 1
    assert checks["R3_honest_pairs_shared_by_2plus_honest_agents"] == 0


def test_r4_fraud_violations_are_counted_on_the_fraud_side():
    records = [("F1", "2026-08-05 10:00:00", "CUST1", "completed", "CL01"),
               ("F1", "2026-08-06 10:00:00", "CUST1", "completed", "CL01"),
               ("F2", "2026-08-06 11:00:00", "CUST1", "completed", "CL01")]
    checks = rules(records, fraud={"F1", "F2"})
    assert checks["R1_pairs_used_by_another_agent"] == {"honest": 0, "fraud": 1}
    assert checks["R2_repeat_after_completed"] == {"honest": 0, "fraud": 1}


def test_r5_activation_needs_registration_and_a_certification_in_force():
    records = [("A1", "2026-08-05 10:00:00", "CUST1", "completed", "CL01"),
               ("A1", "2026-08-06 10:00:00", "CUST2", "completed", "CL03")]
    categories = pd.DataFrame([("A1", "banking", "certified", "2026-08-05 12:00:00"),
                               ("A1", "mobile money", "expired", "2026-07-01 00:00:00")],
                              columns=["agent_id", "category", "certification_status", "certified_at"])
    checks = rules(records, categories=categories)
    assert checks["R5_activation_without_certification_or_before_registration"]["honest"] == 2
    assert rules(records)["R5_activation_without_certification_or_before_registration"]["honest"] == 0


def test_r6_pending_only_in_the_last_72_hours():
    assert dg.pending_window_start() == pd.Timestamp("2026-08-28 00:00:00")
    old = [("A1", "2026-08-27 23:59:59", "CUST1", "pending", "CL01")]
    recent = [("A1", "2026-08-28 00:00:00", "CUST1", "pending", "CL01")]
    assert rules(old)["R6_pending_before_last_72h"]["honest"] == 1
    assert rules(recent)["R6_pending_before_last_72h"]["honest"] == 0


@pytest.fixture(scope="module")
def generated():
    return dg.generate_dataset(1, n_agents=300, fraud_rate=0.13)


def test_generated_data_keeps_every_rule(generated):
    checks = rule_checks(generated)
    for rule in ["R1_pairs_used_by_another_agent", "R2_repeat_after_completed",
                 "R5_activation_without_certification_or_before_registration", "R6_pending_before_last_72h"]:
        assert checks[rule]["honest"] == 0, rule
    assert checks["R1_pairs_used_by_another_agent"]["fraud"] > 0
    assert checks["R2_repeat_after_completed"]["fraud"] > 0
    assert checks["R3_honest_customers_shared_by_2plus_honest_agents"] > 0
    assert checks["R3_honest_pairs_shared_by_2plus_honest_agents"] == 0
    integrity = referential_integrity(generated)
    assert not any(integrity["unknown_agent_id"].values())
    assert all(v == 0 for k, v in integrity.items() if k != "unknown_agent_id")


def test_identity_is_unique_and_well_formed(generated):
    checks = identity_checks(generated.identity)
    assert checks["rows"] == 300
    assert all(v == 0 for k, v in checks.items() if k != "rows")
    assert len(dg.FIRST_NAMES) >= 60 and len(dg.LAST_NAMES) >= 60
    assert len(set(dg.FIRST_NAMES)) == len(dg.FIRST_NAMES) and len(set(dg.LAST_NAMES)) == len(dg.LAST_NAMES)


def test_model_input_list_is_exactly_the_four_features():
    assert fe.MODEL_FEATURES == ["submission_frequency", "time_of_day_entropy", "customer_similarity", "collusion_score"]
    for columns in [fe.MODEL_FEATURES, fe.FEATURE_COLUMNS, fe.ALL_FEATURES]:
        assert not CONTEXT_COLUMNS & set(columns)


def test_feature_vectors_carry_no_context_or_identity_column(generated):
    features = fe.compute_feature_vectors(generated.activations, generated.agents)
    assert not CONTEXT_COLUMNS & set(features.columns)


def test_identity_columns_are_not_in_labels_or_agents(generated):
    assert not IDENTITY_COLUMNS & set(generated.labels.columns)
    assert not IDENTITY_COLUMNS & set(generated.agents.columns)
    assert not IDENTITY_COLUMNS & set(generated.activations.columns)


def test_context_fields_are_independent_of_fraud():
    table = independence_table(dg.generate_dataset(42))
    for field in ["account_status_suspended", "n_categories", "registration_age_days", "mean_quality_score",
                  "completed_share", "commission_mean_per_record_kes"]:
        assert 0.35 <= table[field]["auc"] <= 0.65, field
