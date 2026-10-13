"""duplicate_activation_rule: a reported Step 7 baseline from unlabelled activation records only."""

import inspect

import pandas as pd

import baselines
import data_generation as dg
import selection

COLUMNS = ["agent_id", "timestamp", "customer_id", "client_id", "activation_status"]


def records(rows):
    return pd.DataFrame(rows, columns=COLUMNS)


def test_duplicate_activation_rule_by_hand():
    acts = records([
        ("A1", "2026-08-01 10:00", "CUST1", "CL01", "completed"),
        ("A2", "2026-08-02 10:00", "CUST1", "CL01", "completed"),
        ("A3", "2026-08-01 10:00", "CUST2", "CL01", "completed"),
        ("A3", "2026-08-02 10:00", "CUST2", "CL01", "failed"),
        ("A4", "2026-08-01 10:00", "CUST3", "CL01", "failed"),
        ("A4", "2026-08-02 10:00", "CUST3", "CL01", "completed"),
        ("A4", "2026-08-03 10:00", "CUST3", "CL02", "completed"),
    ])
    counts = baselines.duplicate_activation_counts(acts)
    assert counts.to_dict() == {"A1": 1, "A2": 1, "A3": 1, "A4": 0}


def test_duplicate_activation_rule_uses_no_labels():
    data = dg.generate_dataset(2, n_agents=120, fraud_rate=0.15)
    counts = baselines.duplicate_activation_counts(data.activations)
    with_labels = data.activations.merge(data.labels, on="agent_id")
    shuffled = with_labels.assign(is_fraud=with_labels["is_fraud"].sample(frac=1, random_state=0).values,
                                  profile="legit", ring_id="")
    assert counts.equals(baselines.duplicate_activation_counts(shuffled))
    assert list(inspect.signature(baselines.duplicate_activation_counts).parameters) == ["activations"]
    source = inspect.getsource(baselines.duplicate_activation_counts)
    assert not any(word in source for word in ["is_fraud", "profile", "ring_id", "labels.csv", "load_labelled", "load_labels"])


def test_duplicate_rule_is_not_a_selection_candidate():
    assert all(c["model"] in {"isolation_forest", "lof"} for c in selection.candidates())


def test_q1_reference_is_the_best_single_feature_of_a_baselines_run(tmp_path):
    pd.DataFrame({"baseline": ["random scores", "single feature: a (+)", "single feature: b (-)",
                               "rule: duplicate_activation_rule (pairs > 0)"],
                  "pr_auc": [0.15, 0.40, 0.57, 0.90]}).to_csv(tmp_path / "baseline_metrics.csv", index=False)
    assert selection.best_single_feature_pr_auc(tmp_path)[0] == 0.57
