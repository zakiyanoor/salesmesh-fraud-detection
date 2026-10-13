"""Unit tests for the reporting and analysis modules (by hand, on small frames; no real labels)."""

import numpy as np
import pandas as pd

import cross_validation
import detectors
import eda
import explainability
import feature_analysis
import freeze
import redraw_score_figure
import stability
import union_reference
from feature_engineering import ALL_FEATURES, BASE_FEATURES, CANDIDATE_FEATURE, MODEL_FEATURES


def agents(n=120, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({f: rng.normal(0, 1, n) for f in ALL_FEATURES})
    df.insert(0, "agent_id", [f"A{10000 + i}" for i in range(n)])
    df["is_fraud"] = np.arange(n) % 6 == 0
    df["profile"] = np.where(df["is_fraud"], np.array(["ring", "weak"] * n)[:n], "legit")
    df.loc[df["is_fraud"], "collusion_score"] += 4
    return df


def test_cv_pooled_recall_and_summary_by_hand():
    oof = pd.DataFrame({"method": "m", "agent_id": list("abcde"), "profile": ["ring", "ring", "weak", "legit", "legit"],
                        "is_fraud": [True, True, True, False, False], "flag": [True, False, False, True, False]})
    table = cross_validation.pooled_pattern_recall(oof).set_index("method")
    assert table.loc["m", "ring"] == 0.5 and table.loc["m", "weak"] == 0.0
    assert table.loc["m", "all_fraud"] == 1 / 3 and table.loc["m", "honest_flag_rate"] == 0.5
    folds = pd.DataFrame({"method": ["m", "m"], "pr_auc": [0.8, 0.6], "roc_auc": [0.9, 0.7], "precision": [1, 1],
                          "recall": [1, 1], "f1": [1, 1]})
    summary = cross_validation.summarise(folds).set_index("method")
    assert summary.loc["m", "pr_auc_mean"] == 0.7 and abs(summary.loc["m", "pr_auc_std"] - np.std([0.8, 0.6], ddof=1)) < 1e-12


def test_cv_folds_keep_test_agents_out_and_fit_inside_each_fold():
    data = agents()
    folds, oof = cross_validation.cross_validate(data, pd.Series(0, index=data["agent_id"]), folds=3)
    assert set(oof["agent_id"]) == set(data["agent_id"])
    assert oof.groupby("method")["agent_id"].nunique().eq(len(data)).all()
    assert (folds["train_agents"] + folds["test_agents"] == len(data)).all()


def test_union_reference_flag_summary_by_hand():
    val = pd.DataFrame({"is_fraud": [True, True, False, False], "profile": ["ring", "weak", "legit", "legit"]})
    row = union_reference.flag_summary("x", np.array([True, False, True, False]), val)
    assert row["flagged"] == 2 and row["true_positives"] == 1 and row["false_positives"] == 1
    assert row["recall_ring"] == 1.0 and row["recall_weak"] == 0.0 and row["precision"] == 0.5


def test_stability_metrics_by_hand():
    y = np.array([True, True, False, False])
    m = stability.scores_metrics(y, np.array([0.9, 0.2, 0.8, 0.1]), np.array([True, False, True, False]))
    assert m["precision"] == 0.5 and m["recall"] == 0.5 and m["flagged"] == 2 and m["roc_auc"] == 0.75
    assert stability.SEEDS == list(range(101, 111))


def test_redraw_reads_classes_from_saved_files_only(tmp_path):
    pd.DataFrame({"agent_id": ["A1", "A2", "A3", "A4"], "score": [3.0, 2.0, 1.0, 0.5],
                  "flag": [True, True, False, False]}).to_csv(tmp_path / "test_scores.csv", index=False)
    pd.DataFrame({"error": ["false alarm", "missed fraud"], "agent_id": ["A2", "A3"]}).to_csv(
        tmp_path / "error_analysis.csv", index=False)
    table = redraw_score_figure.classes_from_saved_files(tmp_path)
    assert table.set_index("agent_id")["fraud"].to_dict() == {"A1": True, "A2": False, "A3": True, "A4": False}


def test_permutation_importance_finds_the_informative_feature():
    data = agents()
    data["is_fraud"] = np.arange(len(data)) % 12 == 0
    data.loc[data["is_fraud"], "collusion_score"] += np.linspace(6, 12, int(data["is_fraud"].sum()))
    detector = detectors.fit_isolation_forest(data, MODEL_FEATURES)
    base, table = explainability.permutation_importance(detector, data)
    assert base > 0.5 and table.iloc[0]["feature"] == "collusion_score"


def test_feature_analysis_auc_table_and_decision():
    data = agents()
    table = feature_analysis.single_feature_auc(data)
    assert set(table["feature"]) == set(ALL_FEATURES)
    assert table.query("feature == 'collusion_score' and target == 'all_fraud'")["auc"].iloc[0] > 0.95
    correlations = data[ALL_FEATURES].corr(method="spearman")
    keep, auc, max_corr = feature_analysis.decide(table, correlations)
    assert keep == (auc > feature_analysis.KEEP_MIN_AUC and max_corr <= feature_analysis.KEEP_MAX_ABS_CORRELATION)
    assert CANDIDATE_FEATURE not in BASE_FEATURES


def test_eda_entropy_and_descriptors_by_hand():
    assert eda.hour_entropy(pd.Series([3, 3, 3])) == 0.0
    assert abs(eda.hour_entropy(pd.Series(range(24))) - 1.0) < 1e-12
    acts = pd.DataFrame({"record_id": ["R1", "R2", "R3"], "agent_id": ["A1", "A1", "A2"],
                         "timestamp": ["2026-08-01 02:00", "2026-08-01 14:00", "2026-08-02 10:00"],
                         "customer_id": ["C1", "C1", "C1"], "client_id": ["CL01", "CL01", "CL02"]})
    flags = pd.DataFrame({"record_id": ["R2"], "flag": ["near_duplicate_same_customer"]})
    table = eda.agent_descriptors(acts, flags)
    assert table.loc["A1", "records"] == 2 and table.loc["A1", "night_share"] == 0.5
    assert table.loc["A1", "repeat_same_client_share"] == 0.5 and table.loc["A1", "near_duplicates"] == 1
    assert table.loc["A2", "shared_customer_share"] == 1.0


def test_freeze_lists_the_rules_and_the_model():
    paths = [path for _, path in freeze.FILES]
    for needed in ["results/acceptance_criteria.md", "results/selection_rule.md", "results/selection_notes.md"]:
        assert needed in paths
    assert any(p.endswith("chosen_model.joblib") for p in paths) and any(p.endswith("scoring_bundle.joblib") for p in paths)
